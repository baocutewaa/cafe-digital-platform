# BREW & BEAN — `cafe-digital-platform`

> **Định vị thương hiệu:** Hệ thống quán cà phê đặc sản tại **khu vực Tây Hồ, Hà Nội — nằm dọc vành đai Hồ Tây** (Nguyễn Đình Thi · Quảng An · Trích Sài), kết hợp **Brand Landing Page** và trợ lý **Bean AI Barista (Hybrid RAG)**.  
> **Chiến lược triển khai:** **Local-First (No-Docker), Deploy-Last** — Phát triển và kiểm thử hoàn tất trên Local (`localhost`) không cần Docker Desktop, sau đó triển khai lên Neon + Cloudflare Tunnel + Render + Vercel ở giai đoạn cuối (P7).

---

## Hệ thống Quán Cà phê Vành đai Hồ Tây (Tây Hồ, Hà Nội)

| Chi nhánh | Địa chỉ | Điểm nhấn không gian | Hotline |
|---|---|---|---|
| **Flagship Nguyễn Đình Thi** | `88 Nguyễn Đình Thi, P. Thụy Khuê, Q. Tây Hồ, Hà Nội` | Mặt hồ Nam Hồ Tây, quầy **Pour-over V60**, nhiều ổ cắm làm việc | `024 3728 8899` |
| **Quảng An Garden** | `24 Quảng An, P. Quảng An, Q. Tây Hồ, Hà Nội` | Sân vườn ven hồ bán đảo Quảng An, **pet-friendly**, chỗ đậu xe | `024 3718 2468` |
| **Heritage Trích Sài** | `135 Trích Sài, P. Bưởi, Q. Tây Hồ, Hà Nội` | Vành đai Trích Sài yên tĩnh (`quiet_zone`), bàn họp nhóm, chỗ đậu xe | `024 3753 1357` |

*(Thực đơn giữ nguyên 30 đồ uống & bánh thủ công chọn lọc từ hạt Arabica Cầu Đất 1.650m và Robusta Buôn Ma Thuột, minh bạch chỉ số Đắng/Ngọt/Caffeine và 4 nhóm dị ứng `DAIRY`, `NUTS`, `SOY`, `GLUTEN`.)*

---

## Cấu trúc Multi-App Platform

- `apps/landing-page`: **Ứng dụng 1** — Brand Landing Page + Bean AI RAG UI (React 18 + Vite 6 + TypeScript + Tailwind CSS Editorial Warm Alabaster, typography `Inter Variable` & `Lora Variable` + shadcn/ui + TanStack Query).
- `services/landing-api`: **Backend Ứng dụng 1** — FastAPI + SQLAlchemy Async + PostgreSQL 17 (`pgvector`, `pg_trgm`, `unaccent`, `pgcrypto`) + Hybrid RAG Orchestrator + Auto-Seed / Self-Healing `answer_cache`.
- `apps/online-ordering`: **Ứng dụng 2 (Tương lai)** — Website đặt hàng trực tuyến kết nối qua `VITE_ORDERING_APP_URL`.
- `apps/admin-dashboard`: **Ứng dụng 3 (Tương lai)** — Admin Dashboard & AI/ML BI.
- `data/`: Dữ liệu Seed JSON (`data/seed/`: `stores.json`, `categories.json`, `ingredients.json`, `products.json`, `promotions.json`, `answer_cache.json`) & Knowledge Base Markdown (`data/knowledge_base/`, 28 tài liệu).
- `scripts/`: Scripts CLI `seed_database.py`, `ingest_knowledge.py`, `prewarm_cache.py` và `sql/init_neon.sql`.
- `deploy/pc/`: Công cụ PowerShell/Python vận hành PostgreSQL 17 Native, Ollama Local & Cloudflare Tunnel trên PC.
- `docs/`: Tài liệu kỹ thuật chi tiết theo từng giai đoạn triển khai (`P0`–`P5` và các bản cập nhật sau P5).

---

## Stack AI & Bảo vệ Chất lượng Trả lời (Bean AI RAG)

- **LLM mặc định (`LLM_MODEL`):** `qwen2.5:3b` (`LLM_NUM_PREDICT=650`, `LLM_THINK_NUM_PREDICT=2048`), đồng thời hỗ trợ tự động nhận diện `/api/show` cho các model dual-mode / thinking (`qwen3:4b`, `qwen3:8b`, DeepSeek-R1...) trong `OllamaClient`.
- **Embedding Model (`EMBEDDING_MODEL`):** `bge-m3` (`1024` chiều).
- **Hybrid Retrieval + SQL Fast-path:**
  - `SQL Fast-path` trả lời tức thì (< 800 ms, không tốn LLM) cho giá món/size (`PRODUCT_LOOKUP`), thông tin quán Tây Hồ (`STORE_INFO`), khuyến mãi (`PROMOTION_LOOKUP`) và ngoài phạm vi (`OUT_OF_SCOPE`).
  - `Hybrid Search` (`pgvector` HNSW + PostgreSQL FTS/`pg_trgm` qua RRF `k=60`) kết hợp `SqlProductRetriever` (lọc giá, `max_sweetness`, `drinks_only`, `max_bitterness`, dị ứng bắt buộc).
  - Lớp bảo vệ `rag/generation/guards.py` + `CacheSeedService`: chặn lọt chuỗi `<think>` / độc thoại suy luận tiếng Anh, kiểm tra giá/dị ứng sau sinh câu trả lời, tự dọn bản ghi lỗi trong PostgreSQL `answer_cache` (`purge_corrupted_answer_cache`) và đồng bộ `data/seed/answer_cache.json` (44 câu hỏi chuẩn) khi khởi động (`AUTO_SEED_ANSWER_CACHE=true`).

---

## Khởi chạy & Đồng bộ Dữ liệu Local (Không dùng Docker)

1. **PostgreSQL 17 Native + `pgvector` (`127.0.0.1:5432`):**
   ```powershell
   .\deploy\pc\start-local-postgres.ps1
   ```
2. **Ollama Local (`127.0.0.1:11434`):**
   ```powershell
   .\deploy\pc\setup-ollama-env.ps1
   ollama pull bge-m3
   ollama pull qwen2.5:3b
   ```
3. **Migration, Seed, Ingestion & Answer Cache (tại thư mục gốc `cafe-digital-platform`):**
   ```powershell
   cd services\landing-api
   .\.venv\Scripts\Activate.ps1
   alembic upgrade head
   cd ..\..
   python scripts\seed_database.py
   python scripts\ingest_knowledge.py --path data\knowledge_base
   python scripts\prewarm_cache.py --import-seed --force
   ```
4. **Backend FastAPI (`http://localhost:8000`):**
   ```powershell
   cd services\landing-api
   .\.venv\Scripts\Activate.ps1
   uvicorn app.main:app --reload --port 8000
   ```
   Kiểm tra nhanh: `http://localhost:8000/health`, `http://localhost:8000/ready`, `http://localhost:8000/docs`.
5. **Frontend React (`http://localhost:5173`):**
   ```powershell
   cd apps\landing-page
   npm install
   npm run dev
   ```

---

## Kiểm thử Nhanh

- **Backend (`services/landing-api`):**
  ```powershell
  ruff check .
  pytest tests/unit -v
  pytest -v
  ```
- **Frontend (`apps/landing-page`):**
  ```powershell
  npm run lint
  npm run build
  ```

---

## Tài liệu Chi tiết

- Tổng hợp tiến độ & cấu hình hiện hành: [docs/README.md](./docs/README.md)
- Tổng hợp các cập nhật sau P5 (RAG Consultation, Chống lọt Thinking & Chuyển địa bàn Hồ Tây): [docs/post-p5-updates-and-tay-ho-rebrand.md](./docs/post-p5-updates-and-tay-ho-rebrand.md)
- Kế hoạch kiến trúc tổng thể: [Coffee_Landing_Page_Plan.md](./Coffee_Landing_Page_Plan.md)
