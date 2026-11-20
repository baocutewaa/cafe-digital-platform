# Giai đoạn P0 — Thiết lập Môi trường Local (No-Docker) & Walking Skeleton Local

> **Mục tiêu P0:** Dựng hoàn chỉnh cấu trúc Multi-App `cafe-digital-platform`, thiết lập PostgreSQL 17 Native (không dùng Docker), cấu hình bộ khung Backend FastAPI và Frontend React/Vite nối thông suốt qua `/health`, `/ready`, `/api/v1/storefront`.
> **Phạm vi thực tế:** Phần cài đặt thêm model và chạy benchmark Ollama (`deploy/pc/bench_ollama.py`) được bỏ qua theo yêu cầu để người dùng tự triển khai sau; cấu hình mặc định sử dụng `LLM_MODEL=qwen3:4b` và `EMBEDDING_MODEL=bge-m3`.

---

## 1. Cấu trúc Repository Multi-App đã khởi tạo

Theo Mục 7 của [Coffee_Landing_Page_Plan.md](../Coffee_Landing_Page_Plan.md), toàn bộ cây thư mục nền tảng được thiết lập tại gốc `cafe-digital-platform/`:

- **CI/CD & Blueprint triển khai (chuẩn bị sẵn cho P7):**
  - `.github/workflows/ci-landing.yml`: Tự động chạy `ruff check .` + `pytest tests/unit -v` cho backend và `npm ci` + `npm run lint` + `npm run build` cho frontend.
  - `render.yaml`: Render Web Service blueprint (Python `3.12.8`, region `singapore`, `rootDir: services/landing-api`).
  - `apps/landing-page/vercel.json`: Cấu hình SPA rewrite và security headers cho Vercel.
- **3 Ứng dụng theo định hướng hệ sinh thái:**
  - `apps/landing-page/`: Ứng dụng 1 (React 18 + Vite 6 + TypeScript + Tailwind CSS + shadcn/ui).
  - `apps/online-ordering/README.md`: Placeholder tài liệu cho Ứng dụng 2 (Đặt hàng trực tuyến theo `sku` & `product.slug`).
  - `apps/admin-dashboard/README.md`: Placeholder tài liệu cho Ứng dụng 3 (Admin & AI/ML BI).
- **Backend & RAG:**
  - `services/landing-api/`: Backend FastAPI + cấu trúc thư mục `app/`, `rag/`, `alembic/`, `tests/`.
  - `services/landing-api/requirements-api.txt`, `requirements-cli.txt`, `requirements-dev.txt`, `pyproject.toml`.
- **Dữ liệu, Scripts & Công cụ PC:**
  - `data/seed/` và `data/knowledge_base/{menu,coffee_guide,faq,policies,brand}/`.
  - `scripts/sql/init_neon.sql`.
  - `deploy/pc/`: Bộ script PowerShell & Python vận hành Local/PC (`start-local-postgres.ps1`, `stop-local-postgres.ps1`, `setup-ollama-env.ps1`, `start-ai-node.ps1`, `stop-ai-node.ps1`, `status-ai-node.ps1`, `backup_db.ps1`, `bench_ollama.py`, `cloudflared-config.yml.example`).

---

## 2. Hạ tầng Local Native (No-Docker)

### 2.1. PostgreSQL 17 Native + `pgvector` (`127.0.0.1:5432`)
- Cài đặt trong user space tại `C:\Users\Admin\.local\pgsql` với thư mục dữ liệu `C:\Users\Admin\.local\pgsql17-data` (không cần Docker Desktop hay WSL2).
- `scripts/sql/init_neon.sql` khởi tạo 4 extensions bắt buộc và role least-privilege dùng cho Production:
  - `vector` (`0.8.7`)
  - `pg_trgm` (`1.6`)
  - `unaccent` (`1.1`)
  - `pgcrypto` (`1.3`)
  - Role `landing_app_user` với `ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO landing_app_user`.
- `deploy/pc/start-local-postgres.ps1` kiểm tra tiến trình, tạo role `cafe_owner`, database `cafe_db`, chạy `init_neon.sql` và khởi động Postgres bằng `pg_ctl.exe`.
- `deploy/pc/stop-local-postgres.ps1` dừng PostgreSQL sạch qua `pg_ctl.exe stop -m fast`.

### 2.2. Ollama Local (`http://127.0.0.1:11434`)
- `deploy/pc/setup-ollama-env.ps1` thiết lập biến môi trường user (`OLLAMA_HOST=127.0.0.1:11434`, `OLLAMA_FLASH_ATTENTION=1`, `OLLAMA_KV_CACHE_TYPE=q8_0`, `OLLAMA_MAX_LOADED_MODELS=2`, `OLLAMA_KEEP_ALIVE=30m`).
- Máy local đã có sẵn dịch vụ Ollama `0.40.16` cùng `qwen3:4b` và `bge-m3:latest`.

---

## 3. Walking Skeleton Backend & Frontend

### 3.1. Backend FastAPI (`services/landing-api`)
- Python `.venv` (Python `3.11.9`) cài đặt đầy đủ `fastapi`, `uvicorn[standard]`, `pydantic`, `pydantic-settings`, `sqlalchemy[asyncio]`, `asyncpg`, `alembic`, `pgvector`, `httpx`, `pytest`, `pytest-asyncio`, `ruff`.
- Cấu hình tại `app/core/config.py` (`.env` và `.env.example` đã tạo sẵn với `CORS_ORIGINS=["http://localhost:5173","http://localhost:4173"]`, `LLM_MODEL=qwen3:4b`, `EMBEDDING_MODEL=bge-m3`).
- Kết nối DB tại `app/db/session.py` (`AsyncSessionLocal`, `check_db_connection()`).
- Client Ollama tích hợp Circuit Breaker (`_failure_threshold = 3`, `_cooldown_seconds = 15.0`) và hỗ trợ `CF-Access-Client-Id`/`Secret` tại `app/integrations/ollama_client.py`.
- Endpoints P0:
  - `GET /health` (`app/api/v1/endpoints/health.py`): Liveness check không chạm DB/Ollama.
  - `GET /ready`: Kiểm tra đồng thời PostgreSQL (kết nối + đủ 4 extensions) và Ollama (`/api/version` + `/api/tags`).
  - `GET /api/v1/storefront`: Trả thông tin tổng quan thương hiệu & `ai_mode`.

### 3.2. Frontend React + Vite (`apps/landing-page`)
- Cấu hình Tailwind CSS + bảng màu Espresso/Cream/Caramel (`src/index.css`, `tailwind.config.ts`) và shadcn/ui (`components.json`, `badge.tsx`, `button.tsx`, `card.tsx`).
- `src/lib/api-client.ts`, `src/lib/warmup.ts`, `src/lib/utils.ts`, `src/lib/sse-client.ts`.
- `HomePage.tsx` (P0 Walking Skeleton) gọi `warmupBackend()` và truy vấn `/ready` + `/api/v1/storefront` qua TanStack Query để hiển thị trạng thái kết nối FastAPI, PostgreSQL 17 extensions và Ollama Local.

---

## 4. Các lỗi phát hiện và đã khắc phục trong P0

| Vấn đề phát hiện khi rà soát | Nguyên nhân | Cách khắc phục |
|---|---|---|
| `/ready` luôn báo `postgresql.connected = false` | `app/db/session.py` chạy `SELECT current_database(), server_version` (sai cú pháp PostgreSQL: `column "server_version" does not exist`) | Sửa thành `SELECT current_database(), current_setting('server_version')` |
| `npm install` lỗi `ETARGET` | `apps/landing-page/package.json` khai báo `"globals": "^25.12.0"` không tồn tại trên npm | Sửa thành `"globals": "^15.12.0"` và sinh `package-lock.json` |
| `npm run build` (`tsc -b`) lỗi `ImportMeta.env`, `@/index.css`, `path`, `__dirname` | Thiếu type declarations cho Vite client và Node.js | Tạo `src/vite-env.d.ts` (`/// <reference types="vite/client" />`) và thêm `"@types/node": "^22.10.0"` vào `devDependencies` |
| `start-local-postgres.ps1` dễ giữ handle pipe khi gọi từ script tự động | Dùng `Start-Process postgres.exe -RedirectStandardOutput` | Chuyển sang `pg_ctl.exe -D $pgData -l $pgLog -o "-p 5432 -h 127.0.0.1,::1" start` (đồng bộ với `stop-local-postgres.ps1`) |

---

## 5. Kết quả nghiệm thu P0
- `ruff check .` (backend): Exit `0`.
- `pytest -v` (backend P0): Exit `0` (`3 passed`: `test_health_endpoint`, `test_ready_endpoint_reports_postgres_and_ollama_status`, `test_storefront_overview_endpoint`).
- `npm run lint` & `npm run build`: Exit `0`.
- Kiểm tra live `http://localhost:5173` ↔ `http://127.0.0.1:8000/ready`:
  - `/health`: `200 OK`
  - `/ready`: `200 OK`, `ready: true`, `docker_used: false`, `CORS: http://localhost:5173`, `postgresql.server_version: "17.12"` (đủ `pg_trgm`, `pgcrypto`, `unaccent`, `vector`), `ollama.connected: true` (`0.40.16`, `qwen3:4b`, `bge-m3`).
- *Lưu ý:* Thư mục gốc chưa chạy `git init` (sẵn sàng khởi tạo khi cần đẩy repository lên GitHub).
