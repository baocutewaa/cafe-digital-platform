# BREW & BEAN (`cafe-digital-platform`) — Tài liệu Chi tiết Theo Từng Giai đoạn

Thư mục `docs/` tổng hợp chi tiết toàn bộ kiến trúc, cấu hình, mã nguồn, quyết định kỹ thuật, các lỗi đã phát hiện/khắc phục và lịch sử cập nhật của hệ thống theo kế hoạch [Coffee_Landing_Page_Plan.md](../Coffee_Landing_Page_Plan.md).

## Tổng quan tiến độ triển khai

| Giai đoạn | Tên giai đoạn | Trạng thái | Tài liệu chi tiết |
|---|---|---|---|
| **P0** | Thiết lập Môi trường Local (No-Docker) & Walking Skeleton Local | Hoàn tất (đã nâng cấp cấu hình AI mặc định ở bản cập nhật sau P5) | [phase-p0-local-setup-walking-skeleton.md](./phase-p0-local-setup-walking-skeleton.md) |
| **P1** | Database Schema, Seed Data & Storefront API trên Local | Hoàn tất (đã đồng bộ địa bàn Tây Hồ, Hà Nội) | [phase-p1-database-seed-storefront-api.md](./phase-p1-database-seed-storefront-api.md) |
| **P2** | Giao diện React Brand Landing Page trên Local (6 trang) | Hoàn tất (đã nâng cấp Editorial UI & địa bàn Hồ Tây) | [phase-p2-react-landing-page-ui.md](./phase-p2-react-landing-page-ui.md) |
| **P3** | Biên soạn Knowledge Base (28 tài liệu) & Local CLI Ingestion Pipeline | Hoàn tất (đã cập nhật 5 tài liệu theo vành đai Hồ Tây) | [phase-p3-knowledge-base-cli-ingestion.md](./phase-p3-knowledge-base-cli-ingestion.md) |
| **P4** | Hybrid Retrieval, RRF (`k=60`) & SQL Fast-path trên Local | Hoàn tất (đã nâng cấp Query Parser, Tư vấn từng món & Tây Hồ hints) | [phase-p4-hybrid-retrieval-fast-path.md](./phase-p4-hybrid-retrieval-fast-path.md) |
| **P5** | Bean AI Generation, Answer Cache & Chat Widget UI trên Local | Hoàn tất (đã bổ sung Think Guard, Self-Healing Cache & `qwen2.5:3b`) | [phase-p5-bean-ai-generation-cache-chat-ui.md](./phase-p5-bean-ai-generation-cache-chat-ui.md) |
| **Post-P5** | Tối ưu Consultation RAG, Chống lọt Thinking, Editorial UI & Hệ thống Hồ Tây | Hoàn tất | [post-p5-updates-and-tay-ho-rebrand.md](./post-p5-updates-and-tay-ho-rebrand.md) |
| **P6** | Kiểm thử toàn diện, RAG Evaluation (80 câu) & Local Stability Gate | Chưa triển khai | — |
| **P7** | Hạ tầng Cloud (Neon, Cloudflare Tunnel, Render, Vercel) & Go-live | Chưa triển khai | — |

## Cấu hình hiện hành (Local-First, No-Docker)

- **Địa bàn vận hành thương hiệu:** Hệ thống 3 chi nhánh **BREW & BEAN** tại **Quận Tây Hồ, Hà Nội (vành đai Hồ Tây)**:
  - `brew-bean-nguyen-dinh-thi` (`88 Nguyễn Đình Thi, P. Thụy Khuê, Q. Tây Hồ`)
  - `brew-bean-quang-an` (`24 Quảng An, P. Quảng An, Q. Tây Hồ`)
  - `brew-bean-trich-sai` (`135 Trích Sài, P. Bưởi, Q. Tây Hồ`)
- **PostgreSQL 17 Native (Windows User Space):** `127.0.0.1:5432`, database `cafe_db`, role `cafe_owner`, các extensions: `vector` (`0.8.7`), `pg_trgm` (`1.6`), `unaccent` (`1.1`), `pgcrypto` (`1.3`).
- **Ollama Local Runtime:** `http://127.0.0.1:11434`, mặc định `LLM_MODEL=qwen2.5:3b` (`LLM_NUM_PREDICT=650`, `LLM_THINK_NUM_PREDICT=2048`) và `EMBEDDING_MODEL=bge-m3` (`1024` chiều); `OllamaClient` tự phát hiện chế độ thinking qua `/api/show` cho mọi biến thể Qwen2.5 / Qwen3.
- **Answer Cache tự phục hồi:** `AUTO_SEED_ANSWER_CACHE=true`, `ANSWER_CACHE_TTL_DAYS=7` — khi khởi động FastAPI tự dọn bản ghi lỗi/dính thinking và nạp đồng bộ 44 câu hỏi chuẩn từ `data/seed/answer_cache.json`.
- **Backend FastAPI:** `http://localhost:8000` (Python 3.11 `.venv`).
- **Frontend React + Vite:** `http://localhost:5173` (dev) / `http://localhost:4173` (preview), bộ giao diện Editorial (`Inter Variable`, `Lora Variable`, Warm Alabaster).
