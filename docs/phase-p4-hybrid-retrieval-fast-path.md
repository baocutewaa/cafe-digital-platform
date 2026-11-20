# Giai đoạn P4 — Hybrid Retrieval, RRF & SQL Fast-path trên Local

> **Mục tiêu P4:** Xây dựng bộ phân tích truy vấn tiếng Việt/Anh (`Query Parser`), phân loại 7 ý định (`Intent Router`), nhánh trả lời tức thì từ SQL (`SQL Fast-path` < 0.8s không cần LLM), các bộ truy xuất `Dense` (`pgvector`), `Lexical` (`FTS + pg_trgm`), `SQL Product/Store/Promotion`, hợp nhất **Reciprocal Rank Fusion (`k=60`)** đạt **Recall@5 ≥ 0.85**, và chế độ **Lexical + SQL Fallback** khi Ollama Local tắt.

---

## 1. Kiến trúc Retrieval & Routing đã triển khai

### 1.1. Query Parser (`services/landing-api/rag/retrieval/query_parser.py`)
Phân tích câu hỏi đầu vào (hỗ trợ cả tiếng Việt có dấu, không dấu và tiếng Anh) thành cấu trúc `ParsedQuery`:
- **Ngôn ngữ (`language`):** Tự động nhận diện `vi` hoặc `en`.
- **Ngân sách (`max_price`):** Tách các cụm như *"dưới 45k"*, *"tối đa 50.000đ"*, *"under 50k"*, *"45 nghìn"*.
- **Khẩu vị & Độ đắng (`taste_tags`, `max_bitterness`):** *ít đắng / không đắng / dễ uống* → `less_bitter` (`bitterness_level <= 2`), *ngọt dịu* → `sweet`, *béo* → `creamy`, *trái cây* → `fruity`, *thanh mát* → `refreshing`, *đậm vị* → `bold`.
- **Caffeine (`caffeine_level`):** *không caffeine / buổi tối / không mất ngủ* → `none`; *ít caffeine / buổi chiều* → `low`; *nhiều caffeine* → `high`.
- **Sữa bò & Dị ứng (`has_milk`, `excluded_allergens`):**
  - Nhận diện ngữ cảnh dị ứng/kiêng khem kết hợp regex theo từ khóa (`DAIRY`, `NUTS`, `SOY`, `GLUTEN`) để đảm bảo cả câu phức như *"Mình bị dị ứng các loại hạt (NUTS)"* vẫn bắt chính xác mã `NUTS`.
- **Danh mục (`category_slug`), Size (`requested_size`: `small`/`regular`/`large`), Chi nhánh (`store_hint`) và `search_terms`**.

### 1.2. Intent Router (`services/landing-api/rag/generation/intent_router.py`)
Phân loại chính xác vào **7 intent** theo Mục 6.2:
1. `OUT_OF_SCOPE` — Ngoài phạm vi cà phê/quán (lập trình, toán, thời tiết, chứng khoán...).
2. `ALLERGEN_INGREDIENT` — Câu hỏi dị ứng thực phẩm, thành phần nguyên liệu, thuần chay, lactose/gluten.
3. `PROMOTION_LOOKUP` — Mã giảm giá, combo, khuyến mãi.
4. `STORE_INFO` — Giờ mở/đóng cửa, địa chỉ chi nhánh, Wi-Fi, chỗ đậu xe, ổ cắm (tách biệt rõ với câu hỏi về văn bản *chính sách / quy định* của quán).
5. `PRODUCT_LOOKUP` — Hỏi giá theo món/size (`\bgia\b` với word-boundary để tránh khớp nhầm từ *"không gian"*), calo hoặc lọc danh sách món theo giá/danh mục.
6. `PRODUCT_RECOMMENDATION` — Tư vấn, gợi ý món theo khẩu vị, ngân sách, mức caffeine.
7. `COFFEE_KNOWLEDGE` — Kiến thức cà phê (Arabica vs Robusta, Cold Brew vs Espresso, rang vừa), chính sách quán và câu chuyện thương hiệu.

---

## 2. Bộ truy xuất & Hợp nhất RRF (`services/landing-api/rag/retrieval/`)

1. **`DenseRetriever` (`dense.py`):** Truy vấn độ tương đồng cosine qua `pgvector` HNSW trên `document_chunks` đang `is_active = true`, lấy top `RAG_TOP_K_DENSE = 20`.
2. **`LexicalRetriever` (`lexical.py`):** Kết hợp PostgreSQL Full-Text Search (`ts_rank_cd` trên `search_vector` dạng `OR` giữa các token có dấu + không dấu) và `pg_trgm` `word_similarity` trên `search_text`, lấy top `RAG_TOP_K_LEXICAL = 20`.
3. **`SqlProductRetriever` (`sql_retriever.py`):**
   - `find_products_by_name`: Tìm tên món gần đúng bằng `unaccent` + `word_similarity`, chấm điểm theo mức khớp từ khóa.
   - `search_products`: Lọc đa chiều theo giá, caffeine, sữa bò, độ đắng, `taste_tags`, và **loại trừ nghiêm ngặt các món có thành phần dị ứng** (`~Product.product_ingredients.any(...)` + `has_milk = false` khi loại `DAIRY`).
   - `search_stores` & `search_promotions`: Lấy trạng thái mở cửa thực tế (`UTC+7`) và khuyến mãi đang hiệu lực.
4. **`reciprocal_rank_fusion` (`rrf.py`):** Áp dụng công thức $\text{RRF}(d) = \sum \frac{1}{k + \text{rank}_r(d)}$ với $k = 60$, khử trùng lặp theo `chunk_id` và giữ lại top `RAG_FINAL_TOP_K` (`4` mặc định).
5. **`HybridRetriever` (`context_builder.py`):**
   - Điều phối Parse → Intent → SQL Retrieval → Hybrid Search (`Dense + Lexical -> RRF`).
   - Tự động chuyển sang **Lexical + SQL Fallback** (`degraded = True`, bỏ qua gọi Ollama `/api/embed`) khi `offline_fallback=True`, Circuit Breaker đang mở hoặc gặp `OllamaUnavailableError`.
   - Sinh `citations` (khử trùng lặp theo `source_key`, `section`) và `formatted_context` gắn nhãn `[SQL VERIFIED MENU DATA]` + `[KNOWLEDGE BASE CONTEXT]`.

---

## 3. SQL Fast-path & Offline Fallback (`rag/generation/fast_path.py`)

- `try_build_fast_path(retrieval)` trả lời tức thì bằng template song ngữ Việt/Anh (`0` LLM calls) cho:
  - `PRODUCT_LOOKUP`: Giá chính xác từng size `S/M/L` và calo từ `product_variants`.
  - `STORE_INFO`: Địa chỉ, trạng thái *Đang mở cửa / Đã đóng cửa*, giờ mở cửa hôm nay, SĐT và tiện ích.
  - `PROMOTION_LOOKUP`: Danh sách ưu đãi kèm mã code và điều kiện áp dụng.
  - `OUT_OF_SCOPE`: Từ chối lịch sự và điều hướng về chủ đề BREW & BEAN.
- `build_offline_fallback_answer(retrieval)` tổng hợp danh sách món an toàn dị ứng / món gợi ý từ SQL kèm trích đoạn tri thức Lexical Search khi Ollama Local tắt.

---

## 4. Kết quả kiểm thử & Đo lường P4

- **Unit Tests (`tests/unit/test_rag_retrieval.py`):** `3` test mới cho `parse_query`, `classify_intent` (7 intents) và `reciprocal_rank_fusion` (`k=60`).
- **Integration & Benchmark (`tests/integration/test_rag_p4.py`):**
  - `test_sql_fast_path_queries_accurate_and_under_800ms`: Xác minh giá `Caramel Latte size L = 55.000đ`, chi nhánh Quận 1, mã `MORNING20`/`COLDBREW10K` và `OUT_OF_SCOPE`. Độ trễ đo thực tế (offline Ollama): `PRODUCT_LOOKUP = 10.6 ms`, `STORE_INFO = 14.5 ms`, `PROMOTION_LOOKUP = 18.1 ms` (đạt chuẩn `< 800 ms`).
  - `test_allergen_and_multifilter_sql_safety`: Đảm bảo 100% không trả về món chứa `DAIRY` hoặc `NUTS` khi khách dị ứng.
  - `test_offline_lexical_fallback_works_without_ollama`: Xác minh truy xuất Lexical + Fallback hoạt động mượt mà khi tắt Ollama.
  - `test_hybrid_retrieval_recall_at_5_meets_slo`: Đạt **Recall@5 = 15/16 = 0.9375 (93.75%)**, vượt ngưỡng SLO `≥ 0.85`.
- **Tổng hợp sau chỉnh sửa cuối:**
  - `ruff check .`: Exit `0`.
  - `pytest tests/unit -v`: Exit `0` (`10 passed`).
  - `pytest -v`: Exit `0` (`23 passed`).
