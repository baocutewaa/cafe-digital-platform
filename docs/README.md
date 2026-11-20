# BREW & BEAN (`cafe-digital-platform`) — Tài liệu Chi tiết Theo Từng Giai đoạn

Thư mục `docs/` tổng hợp chi tiết toàn bộ kiến trúc, cấu hình, mã nguồn, quyết định kỹ thuật, các lỗi đã phát hiện/khắc phục và kết quả kiểm thử thực tế của từng giai đoạn triển khai theo kế hoạch [Coffee_Landing_Page_Plan.md](../Coffee_Landing_Page_Plan.md).

## Tổng quan tiến độ triển khai

| Giai đoạn | Tên giai đoạn | Trạng thái | Tài liệu chi tiết |
|---|---|---|---|
| **P0** | Thiết lập Môi trường Local (No-Docker) & Walking Skeleton Local | Hoàn tất (trừ phần tự benchmark Ollama theo yêu cầu) | [phase-p0-local-setup-walking-skeleton.md](./phase-p0-local-setup-walking-skeleton.md) |
| **P1** | Database Schema, Seed Data & Storefront API trên Local | Hoàn tất 100% | [phase-p1-database-seed-storefront-api.md](./phase-p1-database-seed-storefront-api.md) |
| **P2** | Giao diện React Brand Landing Page trên Local (6 trang) | Hoàn tất 100% | [phase-p2-react-landing-page-ui.md](./phase-p2-react-landing-page-ui.md) |
| **P3** | Biên soạn Knowledge Base (28 tài liệu) & Local CLI Ingestion Pipeline | Hoàn tất 100% | [phase-p3-knowledge-base-cli-ingestion.md](./phase-p3-knowledge-base-cli-ingestion.md) |
| **P4** | Hybrid Retrieval, RRF (`k=60`) & SQL Fast-path trên Local | Hoàn tất 100% | [phase-p4-hybrid-retrieval-fast-path.md](./phase-p4-hybrid-retrieval-fast-path.md) |
| **P5** | Bean AI Generation, Answer Cache & Chat Widget UI trên Local | Hoàn tất 100% | [phase-p5-bean-ai-generation-cache-chat-ui.md](./phase-p5-bean-ai-generation-cache-chat-ui.md) |
| **P6** | Kiểm thử toàn diện, RAG Evaluation (80 câu) & Local Stability Gate | Chưa triển khai | — |
| **P7** | Hạ tầng Cloud (Neon, Cloudflare Tunnel, Render, Vercel) & Go-live | Chưa triển khai | — |

## Cấu hình cốt lõi xuyên suốt P0–P5 (Local-First, No-Docker)
- **PostgreSQL 17 Native (Windows User Space):** `127.0.0.1:5432`, database `cafe_db`, role `cafe_owner`, các extensions: `vector` (`0.8.7`), `pg_trgm` (`1.6`), `unaccent` (`1.1`), `pgcrypto` (`1.3`).
- **Ollama Local Runtime:** `http://127.0.0.1:11434`, `LLM_MODEL=qwen3:4b`, `EMBEDDING_MODEL=bge-m3` (`1024` chiều).
- **Backend FastAPI:** `http://localhost:8000` (Python 3.11.9 `.venv`).
- **Frontend React + Vite:** `http://localhost:5173` (dev) / `http://localhost:4173` (preview).
