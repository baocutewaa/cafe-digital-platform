# BREW & BEAN — `cafe-digital-platform`

> **Chiến lược triển khai:** **Local-First (No-Docker), Deploy-Last**  
> Phát triển và kiểm thử hoàn tất trên Local (`localhost`) không cần chạy Docker Desktop, sau đó mới triển khai lên Neon + Cloudflare Tunnel + Render + Vercel ở giai đoạn cuối (P7).

## Cấu trúc Multi-App Platform

- `apps/landing-page`: **Ứng dụng 1** — Brand Landing Page + Bean AI RAG UI (React + Vite + TypeScript + Tailwind CSS + shadcn/ui).
- `services/landing-api`: **Backend Ứng dụng 1** — FastAPI + SQLAlchemy Async + Hybrid RAG Orchestrator.
- `apps/online-ordering`: **Ứng dụng 2 (Tương lai)** — Online Ordering Website.
- `apps/admin-dashboard`: **Ứng dụng 3 (Tương lai)** — Admin Dashboard & AI/ML BI.
- `data/`: Dữ liệu Seed JSON (`data/seed/`) & Knowledge Base Markdown (`data/knowledge_base/`).
- `scripts/`: Scripts CLI khởi tạo DB, seed dữ liệu, ingest vector & prewarm cache.
- `deploy/pc/`: Công cụ vận hành PostgreSQL 17 Native, Ollama Local & Cloudflare Tunnel trên PC.

## Khởi chạy Local (P0 Walking Skeleton — Không dùng Docker)

1. **PostgreSQL 17 Native + pgvector (`127.0.0.1:5432`):**
   ```powershell
   .\deploy\pc\start-local-postgres.ps1
   ```
2. **Ollama Local (`127.0.0.1:11434`):**
   ```powershell
   .\deploy\pc\setup-ollama-env.ps1
   python deploy\pc\bench_ollama.py
   ```
3. **Backend FastAPI (`http://localhost:8000`):**
   ```powershell
   cd services\landing-api
   .\.venv\Scripts\Activate.ps1
   uvicorn app.main:app --reload --port 8000
   ```
4. **Frontend React (`http://localhost:5173`):**
   ```powershell
   cd apps\landing-page
   npm run dev
   ```
