# Giai đoạn P1 — Database Schema, Seed Data & Storefront API trên Local

> **Mục tiêu P1:** Thiết kế đầy đủ toàn bộ 16 bảng PostgreSQL 17 bằng SQLAlchemy 2.0 + Alembic migrations, biên soạn bộ dữ liệu mẫu chuẩn cho thương hiệu **BREW & BEAN**, xây dựng script `seed_database.py` (idempotent upsert) và hoàn thiện hệ thống Storefront Read API đạt độ trễ p95 < 150 ms trên Local.

---

## 1. Database Schema (SQLAlchemy 2.0 + Alembic)

### 1.1. Danh sách 16 bảng đã định nghĩa trong `services/landing-api/app/models/`

1. **`app/models/store.py`:**
   - `stores`: Thông tin chi nhánh (`slug`, `name`, `address`, `district`, `city`, `phone`, `google_maps_url`, `latitude`, `longitude`, `amenities` JSONB, `image_url`, `is_active`).
   - `store_hours`: Giờ mở cửa theo ngày (`day_of_week` `0..6` với constraint `ck_store_hours_day_of_week`, `open_time`, `close_time`, `is_closed`, unique `(store_id, day_of_week)`).
2. **`app/models/menu.py`:**
   - `menu_categories`: Danh mục menu (`slug`, `name_vi`, `name_en`, `description_vi`, `description_en`, `display_order`, `is_active`).
   - `products`: Sản phẩm (`category_id`, `slug`, `name_vi`, `name_en`, `short_description_vi`, `short_description_en`, `story_vi`, `image_url`, `taste_tags` JSONB với GIN index `idx_products_taste_tags`, `caffeine_level` check `'none'|'low'|'medium'|'high'`, `bitterness_level` `1..5`, `sweetness_level` `1..5`, `has_milk`, `is_signature`, `is_featured`, `is_active`, `display_order`, index `idx_products_category_active`).
   - `product_variants`: Biến thể theo size (`sku` unique sẵn sàng cho App 2, `size` `'small'|'regular'|'large'`, `temperature` `'hot'|'iced'|'both'`, `price_vnd >= 0`, `calories_kcal`, `is_available`, unique `(product_id, size)`).
   - `ingredients`: Nguyên liệu (`code`, `name_vi`, `name_en`, `allergen_code`).
   - `product_ingredients`: Bảng nối sản phẩm – nguyên liệu (`is_optional`).
3. **`app/models/promotion.py`:**
   - `promotions`: Khuyến mãi (`slug`, `title_vi`, `title_en`, `summary_vi`, `conditions_vi`, `promo_code`, `discount_type` `'percentage'|'fixed_amount'|'bundle'`, `discount_value`, `banner_image_url`, `start_at`, `end_at`, `is_active`).
   - `promotion_products`: Bảng nối khuyến mãi – sản phẩm.
4. **`app/models/knowledge.py` (chuẩn bị cho P3–P4):**
   - `knowledge_sources`: Theo dõi nguồn tài liệu (`source_key`, `checksum`, `current_version`, `status`).
   - `knowledge_documents`: Phiên bản tài liệu (`doc_key`, `category`, `language`, `content`, `metadata_` map cột `"metadata"` JSONB, `version`, `content_hash`, `is_active`, unique `(doc_key, version)`).
   - `document_chunks`: Chunks phục vụ Hybrid Search (`content`, `search_text`, cột generated `search_vector TSVECTOR GENERATED ALWAYS AS (to_tsvector('simple', search_text)) STORED`, `embedding VECTOR(1024)`, `embedding_model`, `token_count`, `metadata_`) cùng 4 index:
     - `idx_chunks_embedding` (`hnsw` với `vector_cosine_ops`)
     - `idx_chunks_search_fts` (`gin` trên `search_vector`)
     - `idx_chunks_search_trgm` (`gin` với `gin_trgm_ops` trên `search_text`)
     - `idx_chunks_metadata` (`gin` trên `metadata`)
5. **`app/models/conversation.py` (chuẩn bị cho P5):**
   - `chat_sessions`: Phiên chat ẩn danh (`session_token_hash`, `store_id`, `language`, `preferences` JSONB, `expires_at`).
   - `chat_messages`: Tin nhắn hội thoại (`client_message_id`, `role`, `status`, `content`, `intent`, `model`, `ttft_ms`, `latency_ms`, `cached`, `degraded`, `retrieved_chunk_ids`, `recommended_product_slugs`, `citations`) kèm partial unique index `uq_chat_client_msg` (`WHERE client_message_id IS NOT NULL`) và `idx_chat_messages_session`.
   - `chat_feedback`: Đánh giá 👍/👎 (`rating IN (-1, 1)`).
   - `answer_cache`: Cache câu trả lời (`normalized_query`, `language`, `intent`, `query_embedding VECTOR(1024)`, `answer`, `product_slugs`, `citations`, `knowledge_version`, `hit_count`, `expires_at`, GIN `gin_trgm_ops` index `idx_answer_cache_trgm`).

### 1.2. Cấu hình Alembic & Migration
- Tạo `services/landing-api/alembic.ini`, `alembic/env.py` (dùng `async_engine_from_config` đọc `settings.MIGRATION_DATABASE_URL`), `alembic/script.py.mako` (import `pgvector.sqlalchemy`).
- Sinh migration đầu tiên `alembic/versions/4adbd42ae0c9_initial_schema.py` và chạy `alembic upgrade head` thành công trên `cafe_db`.
- Cập nhật `pyproject.toml` bỏ qua các rule line-length/import cho file autogenerate trong `alembic/versions/*.py`.

---

## 2. Bộ dữ liệu Seed (`data/seed/`) & CLI `scripts/seed_database.py`

### 2.1. Dữ liệu chuẩn BREW & BEAN
- `data/seed/stores.json` (**3 chi nhánh**):
  - `brew-bean-nguyen-hue` (Flagship Nguyễn Huệ — Quận 1)
  - `brew-bean-thao-dien` (Thảo Điền Garden — TP. Thủ Đức)
  - `brew-bean-vo-van-tan` (Heritage Võ Văn Tần — Quận 3)
  - Mỗi chi nhánh có đầy đủ 7 khung giờ mở cửa từ Thứ Hai (`0`) đến Chủ Nhật (`6`).
- `data/seed/categories.json` (**6 danh mục**):
  - `signature` (5 món), `espresso-coffee` (7 món), `cold-brew` (5 món), `matcha-tea` (5 món), `non-coffee` (4 món), `pastry` (4 món).
- `data/seed/ingredients.json` (**32 nguyên liệu**): Gắn rõ mã dị ứng `DAIRY`, `NUTS`, `SOY`, `GLUTEN` hoặc `null`.
- `data/seed/products.json` (**30 sản phẩm, 82 variants**):
  - Mỗi sản phẩm có `taste_tags`, `bitterness_level`, `sweetness_level`, `caffeine_level`, `has_milk`, `is_signature` (5 món), `is_featured`, các biến thể size `small`/`regular`/`large` kèm `sku`, `temperature`, `price_vnd`, `calories_kcal`.
  - Đảm bảo nhất quán: 13 đồ uống có `has_milk = false` không chứa nguyên liệu `DAIRY` bắt buộc.
- `data/seed/promotions.json` (**3 khuyến mãi đang hiệu lực**):
  - `MORNING20` (giảm 20% combo sáng), `COLDBREW10K` (giảm 10.000đ Cold Brew 18h), `CHILLDUO` (mua 2 đồ uống tặng 1 bánh ngọt).

### 2.2. Script `scripts/seed_database.py`
- Định nghĩa các Pydantic v2 schema (`StoreSeed`, `CategorySeed`, `IngredientSeed`, `ProductSeed`, `PromotionSeed`, `SeedBundle`) kiểm tra tính hợp lệ và tham chiếu chéo (category slug, ingredient code, SKU trùng lặp, product slug trong promotion) trước khi ghi DB.
- Thực hiện `UPSERT` idempotent (`ON CONFLICT ... DO UPDATE`) trong 1 transaction theo `MIGRATION_DATABASE_URL`, đồng bộ cả bảng con (`store_hours`, `product_variants`, `product_ingredients`, `promotion_products`).

---

## 3. Storefront Read API (`/api/v1`)

### 3.1. Kiến trúc phân lớp trong `services/landing-api/app/`
- **Schemas (`app/schemas/`):** `storefront.py`, `store.py`, `menu.py`, `promotion.py`.
- **Repositories (`app/repositories/`):**
  - `store_repo.py`: Truy vấn chi nhánh đang hoạt động kèm `selectinload(Store.hours)`.
  - `menu_repo.py`: Truy vấn danh mục kèm `product_count`, truy vấn sản phẩm với bộ lọc đa chiều (`category`, `max_price`, `caffeine_level`, `has_milk`, `taste_tag` qua JSONB `@>`, `signature`, `featured`, và tìm kiếm tiếng Việt không dấu `q` bằng `func.unaccent(...).ilike(...)`).
  - `promotion_repo.py`: Lọc các khuyến mãi đang `is_active` và trong khoảng `start_at <= now <= end_at`.
- **Services (`app/services/`):**
  - `storefront_service.py`: Tổng hợp overview, tính `is_open_now` & `today_hours` theo múi giờ Việt Nam `UTC+7` (`compute_store_open_status`), chuẩn hóa dữ liệu promotion.
  - `menu_service.py`: Tổng hợp `min_price_vnd`, `max_price_vnd` (từ variants `is_available = true`), danh sách `allergens` duy nhất đã sắp xếp, và chi tiết nguyên liệu (`build_product_summary`, `build_product_detail`).
- **Tối ưu hiệu năng `OllamaClient` (`app/integrations/ollama_client.py`):**
  - Bổ sung tham số `use_cache: bool = False` với TTL `10s` cho `check_health()`: `/ready` vẫn probe trực tiếp (`use_cache=False`), còn `/api/v1/storefront` dùng `use_cache=True` giúp độ trễ `/storefront` ổn định dưới ngưỡng SLO ngay cả khi Ollama chậm hoặc tắt.
- **Endpoints (`app/api/v1/endpoints/` & `router.py`):**
  - `GET /api/v1/storefront`
  - `GET /api/v1/stores`, `GET /api/v1/stores/{slug}`
  - `GET /api/v1/menu/categories`, `GET /api/v1/menu/products`, `GET /api/v1/menu/products/{slug}`
  - `GET /api/v1/promotions/active`
- **Exception Handler (`app/main.py`):** Ánh xạ `ResourceNotFoundError` sang HTTP `404`.

---

## 4. Kiểm thử & Kết quả nghiệm thu P1

- **Unit Tests (`tests/unit/test_storefront_helpers.py`):**
  - `test_compute_store_open_status_open_and_closed`
  - `test_build_product_summary_and_detail_allergens_and_prices`
  - `test_seed_json_bundle_passes_pydantic_validation` (kiểm tra cả tính nhất quán `has_milk=false` với `DAIRY`).
- **Integration Tests (`tests/integration/test_storefront_api.py` & `tests/conftest.py`):**
  - Sử dụng `httpx.AsyncClient` (`ASGITransport`) và `engine.dispose()` tránh xung đột event loop `asyncpg`.
  - Kiểm tra toàn bộ endpoints, 9 tổ hợp bộ lọc đa chiều (`category`, `max_price`, `caffeine_level`, `has_milk`, `taste_tag`, `signature`, tìm không dấu `q=ca phe muoi`, lọc kết hợp), cảnh báo dị ứng (`DAIRY`), `404` cho slug không tồn tại, và kiểm tra **p95 latency < 150 ms** trên toàn bộ các GET endpoints.

**Kết quả chạy thực tế sau chỉnh sửa cuối:**
- `alembic check`: Exit `0` (`No new upgrade operations detected.`).
- `python scripts/seed_database.py` (chạy 2 lần liên tiếp): Exit `0`, đều ghi nhận `stores: 3, categories: 6, ingredients: 32, products: 30, variants: 82, promotions: 3`.
- `ruff check .` & `ruff check scripts/seed_database.py`: Exit `0`.
- `pytest tests/unit -v`: `4 passed`.
- `pytest -v`: `13 passed in 1.61s` (bao gồm test p95 < 150 ms).
