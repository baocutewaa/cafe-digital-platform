# Giai đoạn P4 — Hybrid Retrieval, RRF & SQL Fast-path trên Local

> **Mục tiêu P4:** Xây dựng bộ phân tích truy vấn tiếng Việt/Anh (`Query Parser`), phân loại 7 ý định (`Intent Router`), nhánh trả lời tức thì từ SQL (`SQL Fast-path` < 0.8s không cần LLM), các bộ truy xuất `Dense` (`pgvector`), `Lexical` (`FTS + pg_trgm`), `SQL Product/Store/Promotion`, hợp nhất **Reciprocal Rank Fusion (`k=60`)** đạt **Recall@5 ≥ 0.85**, và chế độ **Lexical + SQL Fallback** khi Ollama Local tắt.

---

## 1. Kiến trúc Retrieval & Routing đã triển khai

### 1.1. Query Parser (`services/landing-api/rag/retrieval/query_parser.py`)
Phân tích câu hỏi đầu vào (hỗ trợ cả tiếng Việt có dấu, không dấu và tiếng Anh) thành cấu trúc `ParsedQuery`:
- **Ngôn ngữ (`language`):** Tự động nhận diện `vi` hoặc `en`.
- **Ngân sách (`max_price`):** Tách các cụm như *"dưới 45k"*, *"với 45k"*, *"tối đa 50.000đ"*, *"under 50k"*; đồng thời bỏ qua giá niêm yết nằm trong ngoặc ngữ cảnh sản phẩm đang xem (`_PAREN_VARIANT_PRICE_RE`, ví dụ `"(Vừa (M), 55.000đ)"`).
- **Khẩu vị, Độ đắng & Độ ngọt (`taste_tags`, `max_bitterness`, `max_sweetness`):** *ít đắng / không đắng / dễ uống* → `less_bitter` (`bitterness_level <= 2`), *ít ngọt / bớt ngọt* → `max_sweetness = 2`, *không ngọt* → `max_sweetness = 1`; tách biệt rõ câu hỏi tùy chỉnh (`is_customization_query`) để không gắn nhầm `sweet`.
- **Caffeine (`caffeine_level`):** *không caffeine / buổi tối / không mất ngủ* → `none`; *ít caffeine / buổi chiều* → `low`; *nhiều caffeine* → `high`.
- **Sữa bò & Dị ứng (`has_milk`, `excluded_allergens`):**
  - Phân biệt câu hỏi tránh dị ứng (*"Mình bị dị ứng..."*) với câu hỏi kiểm tra thành phần (`is_inspection_question`: *"Món X có chứa sữa bò không?"*) kết hợp regex cho `DAIRY`, `NUTS`, `SOY`, `GLUTEN`.
- **Danh mục (`category_slug`), Đồ uống thuần (`drinks_only`), Đại từ tham chiếu (`has_pronoun_reference`), Size (`requested_size`: hỗ trợ cả `Nhỏ (S)`/`Vừa (M)`/`Lớn (L)`), Chi nhánh Tây Hồ (`store_hint`: `nguyen dinh thi` / `quang an` / `trich sai`) và `search_terms`**.

### 1.2. Intent Router (`services/landing-api/rag/generation/intent_router.py`)
Phân loại chính xác vào **7 intent** theo Mục 6.2:
1. `OUT_OF_SCOPE` — Ngoài phạm vi cà phê/quán (lập trình, toán, thời tiết, chứng khoán...).
2. `ALLERGEN_INGREDIENT` — Câu hỏi dị ứng thực phẩm, thành phần nguyên liệu, thuần chay, lactose/gluten.
3. `PROMOTION_LOOKUP` — Mã giảm giá, combo, khuyến mãi.
4. `STORE_INFO` — Giờ mở/đóng cửa, địa chỉ chi nhánh Tây Hồ / vành đai Hồ Tây (Nguyễn Đình Thi, Quảng An, Trích Sài), Wi-Fi, chỗ đậu xe, ổ cắm (tách biệt rõ với văn bản *chính sách / quy định*).
5. `PRODUCT_LOOKUP` — Hỏi giá theo món/size (`\bgia\b` với word-boundary để tránh khớp nhầm *"không gian"*), calo hoặc lọc danh sách món theo giá/danh mục.
6. `PRODUCT_RECOMMENDATION` — Tư vấn, gợi ý món theo khẩu vị, ngân sách, mức caffeine.
7. `COFFEE_KNOWLEDGE` — Kiến thức cà phê, câu hỏi tùy chỉnh vị ngọt/đá (`is_customization_query`), chính sách quán và câu chuyện thương hiệu.

---

## 2. Bộ truy xuất & Hợp nhất RRF (`services/landing-api/rag/retrieval/`)

1. **`DenseRetriever` (`dense.py`):** Truy vấn độ tương đồng cosine qua `pgvector` HNSW trên `document_chunks` đang `is_active = true`, lấy top `RAG_TOP_K_DENSE = 20`.
2. **`LexicalRetriever` (`lexical.py`):** Kết hợp PostgreSQL Full-Text Search (`ts_rank_cd` trên `search_vector` dạng `OR` giữa các token có dấu + không dấu) và `pg_trgm` `word_similarity` trên `search_text`, lấy top `RAG_TOP_K_LEXICAL = 20`.
3. **`SqlProductRetriever` (`sql_retriever.py`):**
   - `find_products_by_name`: Tìm tên món bằng khớp cụm tên/slug chính xác kết hợp cắt subspan lồng nhau (có cờ `exact_only`), hoặc fallback `unaccent` + `word_similarity` theo tỷ lệ phủ từ khóa.
   - `search_products`: Lọc đa chiều theo giá, caffeine, sữa bò, độ đắng, `max_sweetness` (sắp xếp `sweetness_level ASC`), `drinks_only`, `taste_tags`, và **loại trừ nghiêm ngặt các món có thành phần dị ứng** (`~Product.product_ingredients.any(...)` + `has_milk = false` khi loại `DAIRY`).
   - `search_stores` & `search_promotions`: Lấy trạng thái mở cửa thực tế (`UTC+7`) cho hệ thống quán Tây Hồ và khuyến mãi đang hiệu lực.
4. **`reciprocal_rank_fusion` (`rrf.py`):** Áp dụng công thức $\text{RRF}(d) = \sum \frac{1}{k + \text{rank}_r(d)}$ với $k = 60$, khử trùng lặp theo `chunk_id` và giữ lại top `RAG_FINAL_TOP_K` (`4` mặc định).
5. **`HybridRetriever` (`context_builder.py`):**
   - Điều phối Parse → Intent → SQL Retrieval (hỗ trợ giải quyết đại từ từ lịch sử hội thoại và truy vấn phụ cho tùy chỉnh/từng món) → Hybrid Search (`Dense + Lexical -> RRF`).
   - Tự động chuyển sang **Lexical + SQL Fallback** (`degraded = True`, bỏ qua gọi Ollama `/api/embed`) khi `offline_fallback=True`, Circuit Breaker đang mở hoặc gặp `OllamaUnavailableError`.
   - Sinh `citations` (khử trùng lặp theo `source_key`, `section`) và `formatted_context` gắn nhãn `[SQL VERIFIED MENU DATA]` + `[KNOWLEDGE BASE CONTEXT]`.

---

## 3. SQL Fast-path & Offline Fallback (`rag/generation/fast_path.py`)

- `try_build_fast_path(retrieval)` trả lời tức thì bằng template song ngữ Việt/Anh (`0` LLM calls) cho:
  - `PRODUCT_LOOKUP`: Giá chính xác từng size `S/M/L` và calo từ `product_variants`.
  - `STORE_INFO`: Địa chỉ, trạng thái *Đang mở cửa / Đã đóng cửa*, giờ mở cửa hôm nay, SĐT và tiện ích.
  - `PROMOTION_LOOKUP`: Danh sách ưu đãi kèm mã code và điều kiện áp dụng.
  - `OUT_OF_SCOPE`: Từ chối lịch sự và điều hướng về chủ đề BREW & BEAN.
- `build_offline_fallback_answer(retrieval)` hỗ trợ tư vấn chuyên sâu 1 sản phẩm (`_build_single_product_consultation`), kiểm tra dị ứng 1 món (`_build_single_product_allergen_answer`), và làm sạch triệt để các thẻ `[Header]` / tên cột kỹ thuật qua `_clean_kb_chunk_text()` khi cắt đoạn trích.

---

## 4. Kết quả kiểm thử & Đo lường P4

- **Unit Tests (`tests/unit/test_rag_retrieval.py`, `test_product_consultation_rag.py`):** Kiểm tra `parse_query` (bao gồm chi nhánh Tây Hồ, tránh nhầm *"buổi"* với Phường Bưởi, `max_sweetness`, ngữ cảnh chi tiết món), `classify_intent` (7 intents) và `reciprocal_rank_fusion` (`k=60`).
- **Integration & Benchmark (`tests/integration/test_rag_p4.py`):**
  - `test_sql_fast_path_queries_accurate_and_under_800ms`: Xác minh giá `Caramel Latte size L = 55.000đ`, chi nhánh **Nguyễn Đình Thi (Tây Hồ)** (cập nhật từ case Quận 1 ban đầu sau chuyển địa bàn), mã `MORNING20`/`COLDBREW10K` và `OUT_OF_SCOPE`.
  - `test_allergen_and_multifilter_sql_safety`: Đảm bảo 100% không trả về món chứa `DAIRY` hoặc `NUTS` khi khách dị ứng.
  - `test_offline_lexical_fallback_works_without_ollama`: Xác minh truy xuất Lexical + Fallback hoạt động mượt mà khi tắt Ollama.
  - `test_hybrid_retrieval_recall_at_5_meets_slo`: Đạt **Recall@5 = 15/16 = 0.9375 (93.75%)** tại thời điểm nghiệm thu P4 ban đầu, vượt ngưỡng SLO `≥ 0.85`.
