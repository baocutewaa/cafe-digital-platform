# Giai đoạn P5 — Bean AI Generation, Answer Cache & Chat Widget UI trên Local

> **Mục tiêu P5:** Hoàn thiện tầng sinh câu trả lời streaming qua Ollama Local, cơ chế chặn lọt thinking & hậu kiểm giá/dị ứng, lưu trữ phiên chat & phản hồi (`chat_sessions`, `chat_messages`, `chat_feedback`), tầng tăng tốc `answer_cache` tự phục hồi kèm CLI `scripts/prewarm_cache.py` (44 câu hỏi), và giao diện **Bean AI Chat Widget** (SSE streaming, Product Cards, Citations, Feedback 👍/👎, chế độ *Tra cứu nhanh*) trên React.

---

## 1. Tầng Generation, An toàn & Hậu kiểm (`services/landing-api/`)

### 1.1. `OllamaClient` (`app/integrations/ollama_client.py`)
- Kết nối tới `OLLAMA_BASE_URL` (mặc định Local `http://127.0.0.1:11434`; hỗ trợ sẵn header `CF-Access-Client-Id` và `CF-Access-Client-Secret` cho P7).
- Hỗ trợ cả streaming NDJSON (`stream_chat`) và non-streaming (`chat`) tới `/api/chat`:
  - Model mặc định hiện hành: `LLM_MODEL=qwen2.5:3b` (cập nhật từ `qwen3:4b` sau P5), `EMBEDDING_MODEL=bge-m3` qua `/api/embed`.
  - Tham số mặc định: `num_ctx: 4096`, `num_predict: 650` (`LLM_NUM_PREDICT`), `LLM_THINK_NUM_PREDICT: 2048`, `temperature: 0.3`.
  - `_resolve_think_mode()` kiểm tra `/api/show` để áp dụng `"think"` phù hợp: `none` (không gửi cho model instruct thuần), `disable` (`think=false`), hoặc `separate` (`think=true` với `num_predict >= 2048` + tự động nâng cấp `promote_to_separate_thinking()` và fallback gỡ `think` nếu Ollama trả HTTP `400`).
- Kiểm soát tải & chịu lỗi:
  - `asyncio.Semaphore` giới hạn đồng thời (`LLM_MAX_CONCURRENCY=1`, `LLM_QUEUE_TIMEOUT_S=20.0`).
  - **Circuit Breaker:** Mở mạch sau `3` lỗi liên tiếp với thời gian hồi `15.0s`.
  - `check_health(use_cache=True)` với TTL `10.0s` để các endpoint storefront/session kiểm tra trạng thái Ollama mà không làm nghẽn request.

### 1.2. System Prompts & Conversation Memory (`rag/generation/prompts/system_prompts.py`)
- Hỗ trợ song ngữ Việt (`BASE_SYSTEM_PROMPT_VI`) và Anh (`BASE_SYSTEM_PROMPT_EN` định vị hệ thống BREW & BEAN tại khu vực Tây Hồ, vành đai Hồ Tây, Hà Nội), kèm `_TASK_GUIDANCE` riêng cho 3 intent cần LLM và `_SINGLE_PRODUCT_TASK_VI`/`EN` khi tư vấn sâu 1 món cụ thể (`single_product_focus`).
- Ràng buộc trả lời chỉ dựa trên `[SQL VERIFIED MENU DATA]` và `[KNOWLEDGE BASE CONTEXT]`, không tự bịa tên món, giá tiền (VND), mã khuyến mãi, giờ mở cửa hay thông tin dị ứng; không lặp lại tên nhãn kỹ thuật nội bộ; luôn nhắc nguy cơ nhiễm chéo tại quầy bar cho câu hỏi dị ứng.
- Nạp lịch sử hội thoại `RAG_HISTORY_TURNS=4` lượt gần nhất (`user`/`assistant`) từ `ChatRepository.get_recent_history` (tự động lọc bỏ tin nhắn lỗi cũ).

### 1.3. Guards, `AnswerGenerator` & Hậu kiểm (`rag/generation/guards.py`, `rag/generation/answer_generator.py`)
- **Abstention:** Nếu intent là `COFFEE_KNOWLEDGE` nhưng không có cả `chunks` lẫn `products` từ SQL, hệ thống trả về thông báo từ chối an toàn (`model="abstention"`) thay vì gọi LLM suy đoán.
- **Anti-Thinking Leak & Truncation Guard (`guards.py`, `_ThinkStreamFilter`):**
  - Đệm 64 ký tự đầu trước khi flush stream; kiểm tra sớm (`>= 16` ký tự) qua `looks_like_leaked_thinking()` để tự promote mode hoặc hủy stream suy luận tiếng Anh / thẻ `</think>` không có thẻ mở (`enter_untagged_think`).
  - `is_corrupted_cached_answer()` kiểm tra thẻ `<think>` sót, độc thoại reasoning tiếng Anh, dấu `**` lẻ cặp hoặc câu trả lời đứt đoạn ở cuối.
- **Post-generation Check (`post_check_answer`):**
  - `strip_think_tags`: Loại bỏ các khối `<think>...</think>` và `<thought>...</thought>`.
  - `extract_mentioned_prices_vnd`: Đối chiếu các mức giá (`xx.000đ`, `xxk`) trong câu trả lời với `product_variants` đang `is_available=True`; nếu phát hiện giá không khớp, tự động bổ sung dòng `*Lưu ý giá niêm yết chính xác từ hệ thống:*`.
  - Kiểm tra danh sách món không an toàn (`get_unsafe_product_names`) khi truy vấn có `excluded_allergens` (`DAIRY`, `NUTS`, `SOY`, `GLUTEN`) để gắn `*Cảnh báo kiểm tra dị ứng*`.
- **Graceful Degradation (Offline Fallback):**
  - Khi `retrieval.degraded=True`, Circuit Breaker đang mở, gặp `OllamaUnavailableError` hoặc output sau cùng vi phạm `is_corrupted_cached_answer`, tự động chuyển sang `build_offline_fallback_answer` (`model="lexical-sql-fallback"`, `degraded=True`).

---

## 2. Chat API, Bảo mật Phiên, Rate Limit & Answer Cache

### 2.1. API Endpoints (`app/api/v1/endpoints/chat.py`, `app/schemas/chat.py`)
1. `POST /api/v1/chat/sessions` (`201 Created`):
   - Tạo phiên ẩn danh (`session_id`, `session_token`, `expires_at` theo `SESSION_TTL_HOURS=24`, `ai_mode`: `"online"` hoặc `"fast_lookup_only"`).
   - Token gốc được sinh bằng `secrets.token_urlsafe(32)` và lưu bản băm SHA-256 kèm `SESSION_TOKEN_PEPPER` (`app/core/security.py`), xác thực qua `hmac.compare_digest`.
2. `POST /api/v1/chat/sessions/{session_id}/messages`:
   - Yêu cầu header `X-Session-Token`; giới hạn độ dài tin nhắn `1..1000` ký tự (`CHAT_MAX_MESSAGE_LENGTH=1000`).
   - Trả về `StreamingResponse` (`text/event-stream`) theo chuỗi sự kiện SSE:
     `meta` → `status` (`retrieving` / `generating`) → `products` (emit trước/song song stream text) → `token` → `sources` → `done`.
3. `POST /api/v1/chat/messages/{message_id}/feedback`:
   - Ghi nhận đánh giá `rating` (`1` hoặc `-1`) và `comment` (tùy chọn, tối đa 500 ký tự) vào bảng `chat_feedback` (upsert theo `message_id`).

### 2.2. `ChatService`, `ChatRepository` & Rate Limiting
- **Idempotency (`app/services/chat_service.py`, `app/models/conversation.py`):**
  - Nếu request gửi kèm `client_message_id` đã tồn tại trong cùng `session_id` (unique partial index `uq_chat_client_msg`), hệ thống phát lại (`replayed: true`) câu trả lời trước đó mà không tính thêm vào rate limit hay gọi lại LLM.
- **Lưu tùy chọn phiên (`chat_sessions.preferences`):** Tự động cập nhật `max_price`, `excluded_allergens` và `taste_tags` trích xuất từ câu hỏi vào JSONB của phiên.
- **Rate Limiting (`app/services/rate_limit.py`):**
  - `SlidingWindowRateLimiter` (in-memory, cửa sổ trượt 60s) giới hạn **`8` tin nhắn/phút/phiên** (`CHAT_RATE_LIMIT_PER_MIN=8`) và **`30` tin nhắn/phút/IP**; vượt ngưỡng trả HTTP `429`.

### 2.3. Answer Cache, Auto-Seed Tĩnh & Pre-warming CLI (`app/repositories/chat_repo.py`, `app/services/cache_seed_service.py`, `scripts/prewarm_cache.py`)
- Áp dụng cache cho 3 intent: `COFFEE_KNOWLEDGE`, `PRODUCT_RECOMMENDATION`, `ALLERGEN_INGREDIENT`.
- `lookup_answer_cache`: Tra cứu khớp chính xác `normalized_query` hoặc tương đồng `pg_trgm` qua bộ bảo vệ `_is_safe_fuzzy_cache_hit()` (chặn khớp nhầm giữa các món khác nhau, khác mức giá hoặc khác size `S/M/L`), kiểm tra `is_corrupted_cached_answer()` và **tự xóa ngay bản ghi bẩn nếu bắt gặp lúc đọc**, đồng thời tăng `hit_count`.
- `upsert_answer_cache` & `purge_corrupted_answer_cache`: Từ chối lưu câu trả lời `degraded`/`abstention`/vi phạm `guards.py`, đồng thời dọn các dòng trùng câu hỏi nhưng khác `intent` cũ.
- **Auto-seed tĩnh & Tự làm sạch khi khởi động app (`AUTO_SEED_ANSWER_CACHE=true`):**
  - `cache_seed_service.py` (`startup_seed_answer_cache` gọi trong `lifespan` của `app/main.py`): Tự động gọi `purge_corrupted_answer_cache()` và nạp đồng bộ đè (`force=True`) 44 câu hỏi chuẩn từ [data/seed/answer_cache.json](../data/seed/answer_cache.json) vào `answer_cache` theo `knowledge_version` hiện hành mà **không cần gọi Ollama**.
- **CLI `scripts/prewarm_cache.py`:**
  - Tổng hợp **44 câu hỏi** (`PREWARM_QUESTIONS`), tự động quét dọn cache lỗi trước khi chạy, hỗ trợ `--limit`, `--force`, `--dry-run`, `--delay`, `--export-seed` và `--import-seed`.

---

## 3. Giao diện Bean AI Chat Widget (`apps/landing-page/src/features/chat/`)

### 3.1. Quản lý Phiên, SSE Stream & Ngữ cảnh toàn trang
- `hooks/useChatSession.ts`: Lưu phiên chat vào `sessionStorage` (`brew_bean_chat_session_v1`), kiểm tra hết hạn `expires_at`, tự tạo phiên mới nếu thiếu/hết hạn hoặc gặp `401` (`RETRY_SESSION`), cập nhật trạng thái `ai_mode` (`"online"` / `"fast_lookup_only"`).
- `hooks/useChatStream.ts`: Sử dụng `@microsoft/fetch-event-source` kết nối SSE (`POST /api/v1/chat/sessions/{id}/messages`), hỗ trợ dừng stream tức thời qua `AbortController`, cập nhật realtime `stage` (`retrieving` → `generating`), danh sách `products`, từng `delta` token, `citations`, thông số `done`, gửi feedback 👍/👎 và hiển thị thông báo an toàn khi mất kết nối.
- `components/ChatWidgetProvider.tsx` & `context/ChatWidgetContext.tsx`: Kết nối tất cả nút *"Hỏi Bean AI"* trên `Navbar`, `HomePage` (bao gồm Interactive Taste Finder), `MenuPage`, `ProductDetailPage`, `AboutPage`, `PromotionPage` và `VisitPage` qua `openChat()` và `openChatWithPrompt(prompt)`.
- *(Lưu ý: `src/lib/sse-client.ts` hiện giữ interface `SseEventPayload`, trong khi luồng SSE thực tế được triển khai trực tiếp qua `fetchEventSource` trong `useChatStream.ts`.)*

### 3.2. Thành phần giao diện Chat
| Component | Vai trò đã triển khai |
|---|---|
| `ChatWidget.tsx` & `ChatWindow.tsx` | Nút nổi *"Hỏi Bean AI Barista"* ở góc dưới phải; cửa sổ chat responsive (toàn màn hình trên mobile, `420×620px` trên desktop). |
| `ChatHeader.tsx` | Hiển thị badge trạng thái **Trực tuyến** (`online`) hoặc **Tra cứu nhanh** (`fast_lookup_only`), nút làm mới cuộc trò chuyện và nút đóng. |
| `ChatMessageList.tsx` & `SuggestedQuestions.tsx` | Tự cuộn xuống cuối khi có token mới; hiển thị gợi ý câu hỏi nhanh thay đổi động theo route (`/`, `/menu`, `/menu/:slug`, `/promotions`, `/visit` với câu hỏi chi nhánh Hồ Tây, `/about`). |
| `ChatMessage.tsx` | Render Markdown an toàn (`SafeMarkdown` lọc thẻ `[Section]` thừa và token `**` / `` ` `` chưa đóng via `sanitizeIncompleteInlineTokens`), suy đoán `preferredSize` (`S/M/L`) theo câu hỏi, badge **Trả lời nhanh** / **Tra cứu nhanh**, nút 👍/👎 (`submitFeedback`). |
| `ProductRecommendationCard.tsx` | Thẻ món gợi ý (tối đa 4 thẻ/lượt) kèm ảnh `.webp`, giá theo `preferredSize` hoặc giá thấp nhất, badge *Không sữa bò* / `Đắng` / `Ngọt`, link `/menu/:slug` và nút **Đặt món** mở `OrderQuickModal` (hoặc URL `VITE_ORDERING_APP_URL`). |
| `SourceCitationBadge.tsx` & `TypingAndStageIndicator.tsx` | Chip nguồn tài liệu cho phép bấm mở rộng xem `section` + `snippet`; chỉ báo trạng thái theo từng giai đoạn xử lý. |
| `ChatInput.tsx` | Ô nhập tối đa `1000` ký tự kèm bộ đếm ký tự, hỗ trợ `Enter` gửi / `Shift+Enter` xuống dòng và nút **Dừng** khi đang stream. |

---

## 4. Kiểm thử & Trạng thái Xác minh P5

### 4.1. Bộ test P5 & Bản cập nhật sau P5
- **Unit Tests P5 (`services/landing-api/tests/unit/test_rag_generation.py`):** Bao gồm kiểm tra `strip_think_tags`, `extract_mentioned_prices_vnd`, `OllamaClient._build_chat_payload` theo `think_mode`, `post_check_answer`, `build_rag_messages`, `SlidingWindowRateLimiter`, và xác thực `44` bản ghi trong `data/seed/answer_cache.json`.
- **Unit Tests Consultation & Guards (`services/landing-api/tests/unit/test_product_consultation_rag.py`):** Kiểm tra parser chi tiết món đang xem, `45k ít ngọt`, `looks_like_leaked_thinking`, auto-promote chế độ thinking khi stream, bỏ qua suy luận không thẻ mở trước `</think>`, và `is_corrupted_cached_answer`.
- **Integration Tests (`services/landing-api/tests/integration/test_chat_api.py`):** Tạo phiên, fast-path SSE, idempotent replay (`client_message_id`), feedback 👍/👎, RAG streaming + cache hit + circuit breaker fallback, và rate limit `429`.

### 4.2. Ghi chú kiểm chứng
- Các bài kiểm thử tự động cần được chạy trực tiếp trong môi trường có Python `.venv` / PostgreSQL 17 Local (`ruff check .`, `pytest tests/unit -v`, `pytest -v`, `npm run lint`, `npm run build`) mỗi khi cập nhật dữ liệu chi nhánh hoặc bộ seed `answer_cache.json`.
