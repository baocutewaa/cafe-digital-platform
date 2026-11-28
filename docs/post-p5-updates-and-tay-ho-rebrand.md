# Cập nhật Sau P5 — Tối ưu Bean AI RAG, Giao diện Editorial & Hệ thống Quán Vành đai Hồ Tây

Tài liệu này tổng hợp toàn bộ các nâng cấp đã được triển khai vào codebase sau cột mốc P5 ban đầu (tương ứng các hạng mục cập nhật ở tầng Backend RAG, Cache, Frontend Editorial UI và chuyển đổi hệ thống chi nhánh về Tây Hồ, Hà Nội).

---

## 1. Nâng cấp Tầng LLM Runtime & Chống Lọt Thinking (`services/landing-api/`)

### 1.1. Chuyển model mặc định sang `qwen2.5:3b` & Runtime Think-Mode Detection
- **Cấu hình (`app/core/config.py`, `.env`, `.env.example`):**
  - Đổi mặc định `LLM_MODEL` từ `qwen3:4b` sang `qwen2.5:3b` để ổn định tốc độ phản hồi tiếng Việt và tránh hiện tượng model nhỏ suy luận dài bằng tiếng Anh.
  - Tăng `LLM_NUM_PREDICT` từ `350` lên `650` (hạn chế đứt đoạn giữa câu) và bổ sung `LLM_THINK_NUM_PREDICT=2048`.
- **Xử lý linh hoạt theo model (`app/integrations/ollama_client.py`):**
  - Thêm `_resolve_think_mode()` truy vấn `/api/show` và phân loại model theo 3 chế độ:
    - `none`: Model instruct thuần (như `qwen2.5:3b`) → không gửi tham số `think`.
    - `disable`: Model dual-mode (`qwen3:*`) → gửi `"think": false`.
    - `separate`: Model thinking chuyên biệt (`*-thinking`, `deepseek-r1`, `qwq`) hoặc bị nâng cấp tại runtime → gửi `"think": true` với `num_predict >= LLM_THINK_NUM_PREDICT`.
  - Hỗ trợ `can_promote_think_mode()` / `promote_to_separate_thinking()` và cơ chế retry gỡ `"think"` khi gặp HTTP `400`.

### 1.2. Lớp Kiểm định Guards & Stream Filter (`rag/generation/guards.py`, `answer_generator.py`)
- **`rag/generation/guards.py`:**
  - `strip_think_tags()`: Xử lý cả khối `<think>...</think>`, thẻ `<thought>`, thẻ đóng mồ côi `</think>` ở đầu câu, và khối `<think>` chưa kịp đóng.
  - `looks_like_leaked_thinking()`: Nhận diện độc thoại nội tâm tiếng Anh (`Okay, let's tackle...`, `The user wants...`, `First, I need...`) và các nhãn prompt nội bộ (`SQL VERIFIED MENU DATA`, `KNOWLEDGE BASE CONTEXT`, `which translates to...`).
  - `is_corrupted_cached_answer()`: Kiểm tra thẻ thinking sót, độc thoại reasoning, dấu `**` bị lẻ cặp, hoặc câu trả lời bị cắt cụt giữa câu (kết thúc bằng dấu `(`, `:`, `,` hoặc từ nối tiếng Anh lửng).
- **`AnswerGenerator` (`rag/generation/answer_generator.py`):**
  - `_ThinkStreamFilter` bổ sung `enter_untagged_think()` khi phát hiện chuỗi reasoning không có thẻ mở `<think>`.
  - Đệm phần mở đầu (`preamble_buf` tối đa 64 ký tự) trước khi stream ra UI: kiểm tra sớm từ ký tự thứ `16`, nếu phát hiện lọt thinking sẽ tự promote sang `separate` hoặc chuyển sang `build_offline_fallback_answer`.

---

## 2. Nâng cấp Consultation RAG & Tư vấn Đúng Trọng tâm

- **Query Parser (`rag/retrieval/query_parser.py`):**
  - Tách ngữ cảnh sản phẩm đang xem khỏi điều kiện lọc ngân sách via `_PAREN_VARIANT_PRICE_RE` (ví dụ `"(Vừa (M), 55.000đ)"` không làm đặt nhầm `max_price = 55000`).
  - Phân biệt câu hỏi *ít ngọt* (`max_sweetness = 2` / `1`) với câu hỏi *chỉnh đường/ngọt* (`_SWEET_NON_PREFERENCE_RE`, `is_customization_query = True`), tránh gắn nhầm tag `sweet` (`Ngọt 4/5`).
  - Thêm `drinks_only` (khi khách hỏi `"uống gì"` / `"đồ uống"` mà không nhắc bánh ngọt), `has_pronoun_reference` (`"món này"`, `"ly này"`), và nhận diện size `Nhỏ (S)` / `Vừa (M)` / `Lớn (L)`.
- **SQL Retrieval & Context (`rag/retrieval/sql_retriever.py`, `context_builder.py`, `fast_path.py`):**
  - `find_products_by_name(..., exact_only=...)`: Khớp cụm tên đầy đủ và loại bỏ các subspan con trùng lặp (như `"Sữa Hạnh Nhân"` nằm trong `"Matcha Sữa Hạnh Nhân"`).
  - `search_products`: Sắp xếp ưu tiên `sweetness_level ASC` khi `max_sweetness` được bật và nới ngưỡng bao gồm món ngọt dịu `<= 3/5` nếu cần.
  - Tự động nhận diện hỏi về **1 món cụ thể** (`single_product_focus`) để dùng `_SINGLE_PRODUCT_TASK_VI`/`EN` trong `system_prompts.py` và `_build_single_product_consultation()` khi offline, đồng thời lọc bỏ các thẻ `[Header]` và tên field kỹ thuật (`less_bitter`, `has_milk = false`) ở `_clean_kb_chunk_text()`.

---

## 3. Nâng cấp Answer Cache Tự Phục hồi & An toàn Kết quả

- **Chống khớp nhầm Fuzzy Cache (`app/repositories/chat_repo.py`):**
  - `_is_safe_fuzzy_cache_hit()` ngăn `pg_trgm` khớp nhầm câu hỏi dùng chung khung mẫu (`"Mình đang xem <Món A>..."` vs `<Món B>`), khác số tiền (`45k` vs `50k`) hoặc khác size (`S` vs `M`/`L`).
- **Self-Healing Cache (`chat_repo.py`, `app/services/cache_seed_service.py`, `scripts/prewarm_cache.py`):**
  - `purge_corrupted_answer_cache()` xóa toàn bộ dòng `answer_cache` lỗi/dính thinking trong PostgreSQL.
  - `lookup_answer_cache()` kiểm tra từng kết quả; nếu gặp bản ghi lỗi sẽ tự xóa khỏi DB ngay lập tức.
  - `upsert_answer_cache()` chặn lưu câu trả lời lỗi và dọn các bản ghi cũ trùng `(normalized_query, language, knowledge_version)` nhưng lệch `intent`.
  - `get_recent_history()` lọc bỏ các tin nhắn `assistant` lỗi trong phiên chat cũ khỏi ngữ cảnh gửi LLM.
  - `startup_seed_answer_cache()` gọi `seed_answer_cache_from_file(session, force=True)` khi FastAPI khởi động để dọn cache bẩn và nạp đè 44 câu hỏi chuẩn từ `data/seed/answer_cache.json`.
- **Unit tests bổ sung (`tests/unit/test_product_consultation_rag.py`):** Bao phủ parser câu hỏi chi tiết sản phẩm, `45k ít ngọt`, chống lọt thinking, auto-promote, untagged `</think>`, và kiểm định toàn bộ seed `answer_cache.json`.

---

## 4. Làm mới Giao diện Editorial & Chuyển Địa bàn về Vành đai Hồ Tây (Tây Hồ, Hà Nội)

- **Editorial Design System (`apps/landing-page/`):**
  - Bổ sung typography `@fontsource-variable/inter` và `@fontsource-variable/lora`, bảng màu Warm Alabaster (`--background: 38 24% 96%`, `--foreground: 24 12% 16%`, `--primary: 24 12% 17%`, `--accent: 28 42% 42%`), bo góc tinh gọn `rounded-sm` (`--radius: 0.25rem`).
  - Nâng cấp ảnh hero editorial (`brand-hero-editorial.jpg`, `cau-dat-craft.jpg`, `roasting-craft-editorial.jpg`), logo `BrandLeafMark` trên `Navbar.tsx`.
  - `ProductRecommendationCard.tsx` & `ChatMessage.tsx`: Hiển thị đúng size khách chọn (`preferredSize`), badge `Ngọt X/5`, làm sạch token Markdown dở (`sanitizeIncompleteInlineTokens`) và ẩn thẻ section thừa.
- **Hệ thống 3 không gian quanh vành đai Hồ Tây (Tây Hồ, Hà Nội):**
  - Cập nhật `data/seed/stores.json`, ảnh `public/images/stores/{nguyen-dinh-thi,quang-an,trich-sai}.svg`, `scripts/seed_database.py` (tự đánh dấu `is_active = false` cho các slug cũ), `Store.city` default `"Hà Nội"`, `StorefrontService`, toàn bộ trang Frontend (`HomePage`, `VisitPage`, `AboutPage`, `Navbar`, `Footer`, `OrderQuickModal`, `SuggestedQuestions`, `index.html`), 5 tài liệu Markdown trong `data/knowledge_base/`, 3 bản ghi trong `data/seed/answer_cache.json`, `query_parser.py` (`store_hint`), `intent_router.py` (`_STORE_SIGNALS`), `system_prompts.py` và các bài test liên quan.
