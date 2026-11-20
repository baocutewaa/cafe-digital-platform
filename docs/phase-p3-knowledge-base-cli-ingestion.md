# Giai đoạn P3 — Biên soạn Knowledge Base & Local CLI Ingestion Pipeline

> **Mục tiêu P3:** Xây dựng bộ tri thức Markdown chất lượng cao (≥ 25 tài liệu) cho thương hiệu **BREW & BEAN**, triển khai module chuẩn hóa tiếng Việt (`rag/text/normalize.py`), pipeline chunking & embedding (`bge-m3` 1024 chiều qua Ollama Local) và CLI `scripts/ingest_knowledge.py` nạp nguyên tử vào PostgreSQL 17 (có chống trùng lặp theo `SHA-256 content_hash`).

---

## 1. Bộ Knowledge Base (`data/knowledge_base/` — 28 tài liệu)

Tất cả tài liệu sử dụng YAML frontmatter chuẩn (`title`, `category`, `language`, `tags`, và `product_slugs` khi liên quan sản phẩm) và được rà soát khớp 100% với thành phần, mã dị ứng, mức caffeine trong `data/seed/*.json`:

| Thư mục & Category | Số lượng | Danh sách tài liệu |
|---|---|---|
| `menu/` (`MENU`) | **8** | `01_signature_drinks_guide.md`, `02_espresso_and_phin_lineup.md`, `03_cold_brew_18h_collection.md`, `04_matcha_and_fruit_tea_guide.md`, `05_non_coffee_and_plant_milk.md`, `06_artisan_pastry_pairings.md`, `07_low_bitter_and_beginner_drinks.md`, `08_dairy_free_and_vegan_options.md` |
| `coffee_guide/` (`COFFEE_GUIDE`) | **7** | `01_arabica_cau_dat_vs_robusta_bmt.md`, `02_cold_brew_vs_iced_espresso.md`, `03_roasting_profiles_and_flavor.md`, `04_caffeine_guide_by_time_of_day.md`, `05_pouring_methods_espresso_v60_coldbrew.md`, `06_milk_and_plant_milk_pairings.md`, `07_sweetness_ice_adjustment_guide.md` |
| `faq/` (`FAQ`, định dạng `### Q:` / `A:`) | **6** | `01_menu_taste_and_customization_faq.md`, `02_allergens_and_dietary_faq.md`, `03_caffeine_and_health_faq.md`, `04_store_spaces_and_amenities_faq.md`, `05_promotions_and_vouchers_faq.md`, `06_bean_ai_and_ordering_faq.md` |
| `policies/` (`POLICY`) | **4** | `01_allergen_safety_and_cross_contact.md`, `02_quality_guarantee_and_remake.md`, `03_wifi_workspace_and_pet_policy.md`, `04_sustainability_and_packaging.md` |
| `brand/` (`BRAND`) | **3** | `01_brew_and_bean_story.md`, `02_flagship_spaces_overview.md`, `03_direct_trade_highland_farms.md` |
| **Tổng cộng** | **28** | Vượt ngưỡng yêu cầu ≥ 25 tài liệu của Giai đoạn P3 |

---

## 2. Pipeline Chuẩn hóa, Chunking, Embedding & Indexer

### 2.1. Chuẩn hóa văn bản tiếng Việt (`services/landing-api/rag/text/normalize.py`)
- `normalize_nfc(text)`: Chuẩn hóa Unicode NFC và gom khoảng trắng thừa.
- `strip_vietnamese_accents(text)`: Chuyển `đ`/`Đ` → `d`/`D` và loại bỏ dấu thanh tiếng Việt qua phân rã NFD.
- `build_search_text(text)`: Tạo văn bản song song gồm 2 dòng (bản NFC chữ thường + bản không dấu chữ thường) lưu vào `document_chunks.search_text`, giúp cột generated `search_vector` (`to_tsvector('simple', search_text)`) và `pg_trgm` tìm chính xác cả khi người dùng gõ có dấu hoặc không dấu.
- `normalize_query(text)`: Chuẩn hóa truy vấn người dùng cho tra cứu cache và lexical search.
- `estimate_tokens(text)`: Ước lượng số token (~1.45 tokens/từ) phục vụ ngân sách chunking.

### 2.2. Modules Ingestion (`services/landing-api/rag/ingestion/`)
1. `loaders.py` (`load_markdown_file`, `load_knowledge_directory`):
   - Quét đệ quy file `.md`, parse YAML frontmatter, suy luận `category` theo thư mục nếu thiếu, trích `title`, tính `SHA-256` checksum trên raw bytes và nhận diện tài liệu FAQ (`is_faq`).
2. `cleaner.py` (`clean_markdown_body`):
   - Gỡ YAML frontmatter, gỡ HTML comments, chuẩn hóa NFC và ngắt dòng `\n`.
3. `chunker.py` (`chunk_document`):
   - **Tài liệu FAQ:** Tách theo từng block `### Q:` và giữ nguyên vẹn cặp Hỏi – Đáp (`Q` + `A`) trong cùng 1 chunk (đính kèm tiêu đề tài liệu), chỉ tách theo đoạn nếu một cặp Q–A vượt quá `max_tokens = 400`.
   - **Tài liệu Markdown thường:** Tách theo heading (`#`, `##`), gộp các mục ngắn và tách các mục dài theo ranh giới đoạn văn bản trong ngưỡng `target_tokens = 320`, `max_tokens = 400`, `overlap_tokens = 45`.
   - Gắn đầy đủ metadata (`source_key`, `category`, `language`, `title`, `section`, `chunk_index`, `tags`, `product_slugs`).
4. `embedder.py` (`OllamaEmbedder`):
   - Gọi batch `POST http://127.0.0.1:11434/api/embed` với model `bge-m3` (hỗ trợ sẵn `CF-Access-Client-Id`/`Secret` cho P7).
   - Xác thực chặt chẽ số lượng vector trả về và số chiều vector phải bằng `1024`.
5. `indexer.py` (`ingest_knowledge_path`):
   - Đối chiếu `content_hash` với `knowledge_sources` và `knowledge_documents` đang `is_active = true`; bỏ qua hoàn toàn các file không thay đổi.
   - Thực hiện embed toàn bộ chunk mới bên ngoài lock DB, sau đó mở **1 transaction PostgreSQL duy nhất** để:
     1. Upsert `knowledge_sources` (tăng `current_version`).
     2. Đánh dấu `is_active = false` cho các phiên bản `knowledge_documents` cũ của cùng `doc_key`.
     3. Ghi `knowledge_documents` phiên bản mới (`is_active = true`) và toàn bộ `document_chunks` kèm vector 1024 chiều.
     4. Xóa các bản ghi `answer_cache` cũ để tránh trả lời từ dữ liệu lỗi thời.

### 2.3. CLI vận hành (`scripts/ingest_knowledge.py`)
- Hỗ trợ các tham số:
  - `--path` (mặc định `data/knowledge_base`)
  - `--force` (buộc embed & ghi lại toàn bộ bất kể hash)
  - `--dry-run` (chỉ parse & chunk để kiểm tra, không gọi Ollama hay ghi DB)
  - `--batch-size` (mặc định `16`)

---

## 3. Kiểm thử & Kết quả nghiệm thu P3

- **Unit Tests mới (`services/landing-api/tests/unit/test_rag_ingestion.py`):**
  - `test_vietnamese_normalization_and_search_text`
  - `test_knowledge_base_has_at_least_25_valid_markdown_docs` (xác nhận ≥ 25 tài liệu đủ 5 nhóm `MENU`, `COFFEE_GUIDE`, `FAQ`, `POLICY`, `BRAND`)
  - `test_chunker_preserves_faq_qa_pairs_and_respects_token_limit` (xác nhận Q–A giữ nguyên vẹn và token mỗi chunk nằm trong ngưỡng giới hạn).

**Kết quả chạy thực tế:**
1. `python scripts/ingest_knowledge.py --path data/knowledge_base --dry-run`:
   - Exit `0`: `28` tài liệu, `51` chunks trong `0.06s`.
2. `python scripts/ingest_knowledge.py --path data/knowledge_base` **(Lần 1)**:
   - Exit `0`: `28 changed, 0 skipped`, đã embed và ghi `51` chunks trong `13.2s`.
3. `python scripts/ingest_knowledge.py --path data/knowledge_base` **(Lần 2 — kiểm tra idempotency)**:
   - Exit `0`: `0 changed (skipped 28)`, `0` chunks ghi thêm trong `0.18s`.
4. **Kiểm tra trực tiếp trong PostgreSQL (`cafe_db`):**
   - `knowledge_sources`: `28`
   - `knowledge_documents` (`is_active = true`): `28`
   - `document_chunks`: `51` (`min_dim = 1024`, `max_dim = 1024`)
5. **Lint & Tests:**
   - `ruff check .` & `ruff check scripts/ingest_knowledge.py`: Exit `0`.
   - `pytest tests/unit -v`: Exit `0` (`7 passed`).
   - `pytest -v`: Exit `0` (`16 passed` — toàn bộ unit & integration tests P0–P3).
