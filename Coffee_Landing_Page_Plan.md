# BREW & BEAN — Kế hoạch triển khai chi tiết: Brand Landing Page & Bean AI RAG

> **Hệ sinh thái dự án:** `cafe-digital-platform` (Kiến trúc 3 ứng dụng độc lập)
> **Phạm vi tài liệu này:** Lập kế hoạch triển khai chi tiết cho **Ứng dụng 1 — Brand Landing Page tích hợp Bean AI RAG tư vấn khách hàng**
> **Chiến lược triển khai:** **Local-First (No-Docker), Deploy-Last** — Xây dựng, tích hợp và kiểm thử hoàn tất 100% tính năng ổn định trên môi trường Local (`localhost`) **mà không cần chạy Docker** (tiết kiệm 2–4 GB RAM để ưu tiên cho Ollama AI), sau đó mới bắt đầu thiết lập hạ tầng Cloud (Neon, Cloudflare Tunnel, Render, Vercel) để deploy ở giai đoạn cuối.
> **Tài liệu tham chiếu:** [`Coffee_Landing_Page_Plan_Draft.md`](./Coffee_Landing_Page_Plan_Draft.md) (chỉ kế thừa thiết kế Storefront, Database & Hybrid RAG; tách hoàn toàn khỏi project `cafe-revenue-regression` cũ và tách riêng phần Admin Portal)
>
> | Thành phần (Ứng dụng 1) | Môi trường Phát triển & Nghiệm thu (Giai đoạn P0–P6: Local 100%, Không dùng Docker) | Môi trường Production (Giai đoạn cuối P7: Sau khi Local ổn định) |
> |---|---|---|
> | **Frontend (Brand Landing Page + Bean AI Chat UI)** | **Vite Dev / Preview Server** (`http://localhost:5173`) | **Vercel** (React + Vite + TypeScript) |
> | **Backend (Storefront API + RAG Orchestrator)** | **FastAPI Uvicorn Local** (`http://localhost:8000`, Python `.venv` native) | **Render** (FastAPI Web Service — Singapore) |
> | **Database (PostgreSQL 17 + pgvector)** | **PostgreSQL 17 Native trên Windows** (`localhost:5432`) *hoặc* **Neon Dev Branch** (Không cần Docker Desktop) | **Neon Free Production** (Managed PostgreSQL 17 — Singapore, dùng chung cho hệ sinh thái) |
> | **AI Runtime (Ollama: Qwen3 + BGE-M3) & CLI Ingestion** | **Ollama Local trực tiếp** (`http://127.0.0.1:11434`) | **Máy tính cá nhân (Personal PC) + Cloudflare Tunnel (`cloudflared`)** |
>
> **Phiên bản:** 3.2 (Local-First, No-Docker, Deploy-Last) — 19/11/2026

---

## Mục lục

1. [Tổng quan hệ sinh thái `cafe-digital-platform` & Chiến lược Local-First](#1-tổng-quan-hệ-sinh-thái-cafe-digital-platform--chiến-lược-local-first)
2. [Quyết định kiến trúc & Chiến lược triển khai (ADR)](#2-quyết-định-kiến-trúc--chiến-lược-triển-khai-adr)
3. [Kiến trúc hệ thống Landing Page & Bean AI (Local → Production)](#3-kiến-trúc-hệ-thống-landing-page--bean-ai-local--production)
4. [Thiết kế Database & Quản trị dữ liệu không cần Admin UI](#4-thiết-kế-database--quản-trị-dữ-liệu-không-cần-admin-ui)
5. [Thiết kế chi tiết Frontend Landing Page & UX Bean AI](#5-thiết-kế-chi-tiết-frontend-landing-page--ux-bean-ai)
6. [Thiết kế Backend API & Hybrid RAG Pipeline](#6-thiết-kế-backend-api--hybrid-rag-pipeline)
7. [Cấu trúc Repository (`cafe-digital-platform`)](#7-cấu-trúc-repository-cafe-digital-platform)
8. [Hướng dẫn Thiết lập & Vận hành trên môi trường Local — Không dùng Docker (Giai đoạn Phát triển)](#8-hướng-dẫn-thiết-lập--vận-hành-trên-môi-trường-local--không-dùng-docker-giai-đoạn-phát-triển)
9. [Kiểm thử, RAG Evaluation & Nghiệm thu ổn định trên Local (Quality Gate trước khi Deploy)](#9-kiểm-thử-rag-evaluation--nghiệm-thu-ổn-định-trên-local-quality-gate-trước-khi-deploy)
10. [Roadmap triển khai 8 tuần (Hoàn thiện Local No-Docker P0–P6 → Setup & Deploy Cloud ở P7)](#10-roadmap-triển-khai-8-tuần-hoàn-thiện-local-no-docker-p0p6--setup--deploy-cloud-ở-p7)
11. [Bảo mật, Vận hành, Giám sát & Quản lý rủi ro](#11-bảo-mật-vận-hành-giám-sát--quản-lý-rủi-ro)
12. [Hướng dẫn Thiết lập Hạ tầng Cloud & Deploy từng bước (Thực hiện ở giai đoạn cuối)](#12-hướng-dẫn-thiết-lập-hạ-tầng-cloud--deploy-từng-bước-thực-hiện-ở-giai-đoạn-cuối)
13. [Checklist Nghiệm thu Local & Go-live Production (Definition of Done)](#13-checklist-nghiệm-thu-local--go-live-production-definition-of-done)
14. [Phụ lục: File cấu hình (Local vs Production) & Lệnh vận hành](#14-phụ-lục-file-cấu-hình-local-vs-production--lệnh-vận-hành)

---

## 1. Tổng quan hệ sinh thái `cafe-digital-platform` & Chiến lược Local-First

### 1.1. Định vị trong hệ sinh thái 3 ứng dụng độc lập

Dự án **`cafe-digital-platform`** được xây dựng từ đầu (greenfield), tách biệt hoàn toàn khỏi repo `cafe-revenue-regression` cũ, bao gồm **3 ứng dụng độc lập**:

```mermaid
flowchart TB
    subgraph PLATFORM["Hệ sinh thái cafe-digital-platform"]
        direction LR
        APP1["Ứng dụng 1 (TRỌNG TÂM PLAN NÀY)\nBrand Landing Page + Bean AI RAG\nKhám phá thương hiệu, menu & tư vấn AI"]
        APP2["Ứng dụng 2 (Giai đoạn tiếp theo)\nOnline Ordering Website\nGiỏ hàng, đặt món, thanh toán & giao hàng"]
        APP3["Ứng dụng 3 (Giai đoạn tiếp theo)\nAdmin Dashboard & AI/ML BI\nQuản trị kinh doanh, phân tích & dự báo doanh thu"]
    end

    DB[("Shared Source of Truth\nPostgreSQL 17 + pgvector\n(Local Native -> Neon Cloud)")]
    APP1 <--> DB
    APP2 -.-> DB
    APP3 -.-> DB
    APP1 -.->|"Deep-link CTA 'Đặt món ngay'\n(/order?product=<slug>)"| APP2
```

| Ứng dụng | Mục tiêu cốt lõi | Trạng thái trong kế hoạch này |
|---|---|---|
| **1. Brand Landing Page + Bean AI RAG** | Giới thiệu thương hiệu **BREW & BEAN**, trưng bày menu, câu chuyện hạt cafe, khuyến mãi, chi nhánh và tư vấn khách hàng trực tiếp bằng trợ lý **Bean AI (Hybrid RAG)** | **Triển khai 100% (Hoàn tất trên Local không cần Docker → Deploy ở giai đoạn cuối)** |
| **2. Online Ordering Website** | Đặt đồ uống trực tuyến, tùy chọn topping/đá/đường, giỏ hàng, thanh toán, theo dõi đơn | **Ngoài phạm vi** (Landing Page chỉ chuẩn bị sẵn nút CTA / deep-link theo `product.slug`) |
| **3. Admin Dashboard & AI/ML BI** | Quản lý menu/đơn hàng/khuyến mãi/tri thức, phân tích dữ liệu & dự báo doanh thu bằng AI/ML | **Ngoài phạm vi** (Trong giai đoạn này, dữ liệu Menu và Knowledge Base được nạp qua **Seed & Ingestion CLI** trên máy local) |

### 1.2. Nguyên tắc triển khai "Local-First (No-Docker), Deploy-Last"

Thay vì cấu hình Cloudflare Tunnel, Render, Vercel hay bật Docker Desktop ngay từ đầu gây tốn RAM và phân tán thời gian khi code còn đang thay đổi liên tục, kế hoạch này áp dụng quy trình **2 pha rõ rệt (100% không cần Docker trong suốt quá trình phát triển)**:

```mermaid
flowchart LR
    subgraph PHASE_LOCAL["PHA 1 (Giai đoạn P0 -> P6): Phát triển & Nghiệm thu 100% trên Local (Không dùng Docker)"]
        direction LR
        L1["1. Dựng Local Stack (No Docker)\nPostgres Native + Ollama\nFastAPI (.venv) + Vite React"] --> L2["2. Xây dựng DB, Seed,\nStorefront API & 6 trang UI"]
        L2 --> L3["3. Xây dựng Knowledge Base,\nHybrid RAG & Chat Widget"]
        L3 --> L4["4. Kiểm thử toàn diện trên Local\nUnit/Integration + 80 câu RAG Eval\n+ Offline Fallback Test"]
    end

    GATE{"LOCAL STABILITY GATE\nMọi tính năng & bài test\nổn định 100% trên Local?"}

    subgraph PHASE_DEPLOY["PHA 2 (Giai đoạn cuối P7): Thiết lập Hạ tầng & Deploy Production"]
        direction LR
        D1["1. Tạo Neon Production DB\nMigrate + Seed + Ingest\ntừ Local lên Cloud"] --> D2["2. Setup Cloudflare Tunnel\nZero Trust + WAF cho Ollama"]
        D2 --> D3["3. Deploy FastAPI\nlên Render"]
        D3 --> D4["4. Deploy React lên Vercel\n& Bật CI/CD + Go-live"]
    end

    PHASE_LOCAL --> GATE
    GATE -->|"Đạt 100%"| PHASE_DEPLOY
```

**Lợi ích của việc hoàn tất trên Local (Không dùng Docker) trước khi Setup Deploy:**
1. **Tiết kiệm 2–4 GB RAM cho máy tính cá nhân:** Không phải chạy máy ảo WSL2 / Docker Desktop trên Windows; toàn bộ RAM và VRAM của máy được dành tối đa cho **Ollama (`qwen3` + `bge-m3`)**, giúp tốc độ sinh token và embed nhanh hơn rõ rệt.
2. **Tốc độ phát triển & Debug nhanh gấp nhiều lần:** Mọi kết nối giữa React (`localhost:5173`), FastAPI (`localhost:8000`), PostgreSQL (`localhost:5432`) và Ollama (`127.0.0.1:11434`) đều chạy native với độ trễ ~0 ms, không phụ thuộc thời gian build image hay chờ deploy trên Render/Vercel.
3. **Chốt chắc chắn Schema, Seed Data và Vector Embeddings trước khi lên Cloud:** Chỉ khi bộ dữ liệu và 80 câu test RAG đã đạt chuẩn trên Local mới đẩy một lần sạch sẽ lên Neon Production.
4. **Không lộ hoặc phải quản lý sớm các khóa bảo mật Cloud:** Chỉ mở Cloudflare Tunnel và cấu hình Service Token / WAF ở tuần cuối cùng khi toàn bộ cơ chế rate limit, phân quyền DB và hậu kiểm của Backend đã được kiểm chứng.

### 1.3. Lợi ích của việc tách riêng Landing Page & loại bỏ phần phụ thuộc cũ

1. **Codebase sạch 100%:** Không còn gánh nặng tương thích ngược với `src/`, `artifacts/`, `streamlit_app.py` hay thư viện ML nặng (`scikit-learn`, `pandas`) của repo cũ. Backend cực nhẹ (< 180 MB RAM).
2. **Bề mặt tấn công nhỏ & tập trung UX:** Không phải xây dựng hệ thống đăng nhập Admin, phân quyền RBAC hay các API `POST/PATCH/DELETE` quản trị trên Backend của Landing Page. Mọi API kết nối với database từ phía web đều là **Read-only đối với danh mục sản phẩm/tri thức** và **Append-only đối với phiên chat**.
3. **Đơn giản hóa việc nạp tri thức (Ingestion):** Quản lý dữ liệu menu (`data/seed/*.json`) và tài liệu tri thức (`data/knowledge_base/**/*.md`) ngay trong Git và chạy lệnh CLI `python scripts/ingest_knowledge.py` trực tiếp trên máy tính cá nhân.

---

## 2. Quyết định kiến trúc & Chiến lược triển khai (ADR)

| ID | Quyết định | Lựa chọn | Lý do chính |
|---|---|---|---|
| **ADR-01** | Chiến lược phát triển & triển khai | **Local-First (No-Docker), Deploy-Last**: Hoàn thiện và kiểm thử ổn định 100% trên Local (`Postgres Native` + `Ollama` + `FastAPI .venv` + `Vite`) ở P0–P6, hoàn toàn không dùng Docker; sau đó mới setup hạ tầng deploy ở P7 | Tiết kiệm 2–4 GB RAM trên Windows (không cần chạy Docker Desktop/WSL2); tránh tốn thời gian cấu hình cloud sớm khi schema, prompt và UI còn thay đổi |
| **ADR-02** | Phạm vi repo & ứng dụng | Tạo dự án mới `cafe-digital-platform`; xây dựng trước `apps/landing-page` và `services/landing-api` | Tách biệt rõ 3 ứng dụng độc lập; dễ mở rộng thêm `apps/online-ordering` và `apps/admin-dashboard` sau này |
| **ADR-03** | Database (Local No-Docker → Cloud) | **Local Dev (P0–P6):** PostgreSQL 17 cài trực tiếp trên Windows (`localhost:5432`, kèm binary `pgvector`) *hoặc* trỏ tới 1 branch `dev` trên Neon Free. **Production (P7):** **Neon Free Production** (PostgreSQL 17 + `pgvector` + `pg_trgm` + `unaccent`, region **Singapore**) | Không cần bật Docker mà vẫn tương thích 100% SQL/extensions giữa môi trường Local và Production; cùng bộ Alembic migrations và scripts seed/ingest chạy được cho cả hai |
| **ADR-04** | AI Runtime & Kết nối (Local → Cloud) | **Local Dev:** Gọi trực tiếp `http://127.0.0.1:11434`. **Production (P7):** Kết nối từ Render về PC qua **Cloudflare Named Tunnel (`cloudflared`)** + **Cloudflare Access Service Token** + **WAF Path Allowlist** | Khi code trên máy chỉ cần bật Ollama local; khi deploy lên Render chỉ cần bật thêm `cloudflared` và điền biến môi trường `OLLAMA_BASE_URL=https://ai.<domain>` |
| **ADR-05** | Model AI | Generation: **`qwen3:8b`** (nếu PC có GPU rời ≥ 6 GB VRAM) hoặc **`qwen3:4b`** (nếu PC chỉ dùng CPU), luôn bật `"think": false`. Embedding: **`bge-m3`** (1024 chiều) | Đảm bảo chất lượng tiếng Việt tự nhiên và thời gian phản hồi nhanh (TTFT < 2.5s trên GPU) |
| **ADR-06** | Quản lý Menu & Knowledge Base (khi chưa có App 3 Admin) | **Git-driven Declarative Data + Local CLI**: sửa file `data/seed/*.json` & `data/knowledge_base/**/*.md` → chạy `scripts/seed_database.py` & `scripts/ingest_knowledge.py` | Không cần xây Admin Portal trong phạm vi Landing Page; có lịch sử thay đổi (Git version control), idempotent theo `content_hash` |
| **ADR-07** | Chế độ vận hành khi tắt Ollama / tắt PC (Offline Resilience) | **3 lớp bảo vệ**: (1) SQL Fast-path cho câu hỏi giá/menu/cửa hàng/khuyến mãi, (2) Pre-warmed `answer_cache` cho 40+ câu hỏi phổ biến, (3) Lexical Search (`FTS` + `pg_trgm`) + SQL Product Cards khi Circuit Breaker mở | Kiểm thử được ngay trên Local bằng cách tắt tiến trình Ollama; khi lên Production khách truy cập lúc bạn tắt PC vẫn xem được web và hỏi đáp được 70–80% nhu cầu |
| **ADR-08** | Hosting Production ở giai đoạn cuối (P7) | **Frontend:** **Vercel** (React 18+ / Vite / TS / Tailwind / shadcn/ui). **Backend:** **Render** Web Service (Python native, region **Singapore** — cũng không cần Docker) | Thiết lập ở bước cuối cùng sau khi bản build local (`npm run build` & `pytest`) và bộ đánh giá RAG đã hoàn toàn ổn định |
| **ADR-09** | Liên kết với App 2 (Đặt hàng trực tuyến) | Cấu hình biến `VITE_ORDERING_APP_URL`. Khi App 2 chưa ra mắt, nút *"Đặt món"* mở modal thông tin chi nhánh / gọi món nhanh hoặc dẫn tới trang `/visit` | Sẵn sàng tích hợp ngay khi App 2 hoàn thành mà không cần sửa cấu trúc component |

---

## 3. Kiến trúc hệ thống Landing Page & Bean AI (Local → Production)

### 3.1. Kiến trúc môi trường Local Development — Không dùng Docker (Giai đoạn P0 – P6)

Trong suốt quá trình phát triển và kiểm thử (P0–P6), toàn bộ hệ thống chạy trực tiếp (Native) trên máy tính cá nhân của bạn mà **không cần bật Docker Desktop**:

```mermaid
flowchart LR
    subgraph LOCAL_PC["Máy tính cá nhân (Môi trường Local Native — Không dùng Docker — Giai đoạn P0 đến P6)"]
        BROWSER["Trình duyệt (Browser)\nhttp://localhost:5173"]
        VITE["Vite Dev / Preview Server\napps/landing-page (Node.js)"]
        FASTAPI["FastAPI Local Server (.venv)\nservices/landing-api\nhttp://localhost:8000"]
        LOCAL_PG[("PostgreSQL 17 Local (No Docker)\n+ pgvector + pg_trgm + unaccent\nNative Windows (localhost:5432)\nhoặc Neon Dev DB")]
        OLLAMA_LOCAL["Ollama Server Local\nhttp://127.0.0.1:11434\n(Qwen3 + BGE-M3)"]
        CLI_LOCAL["Scripts CLI & Evaluation\n- seed_database.py\n- ingest_knowledge.py\n- prewarm_cache.py\n- run_evaluation.py"]

        BROWSER <-->|HTTP| VITE
        BROWSER <-->|"REST + SSE\nlocalhost:8000/api/v1"| FASTAPI
        FASTAPI <-->|"asyncpg"| LOCAL_PG
        FASTAPI <-->|"HTTP\n127.0.0.1:11434"| OLLAMA_LOCAL
        CLI_LOCAL -->|"127.0.0.1:11434"| OLLAMA_LOCAL
        CLI_LOCAL -->|"asyncpg"| LOCAL_PG
    end
```

### 3.2. Kiến trúc môi trường Production sau khi Deploy (Giai đoạn cuối P7)

Sau khi toàn bộ tính năng trên Local đã vượt qua bước nghiệm thu ổn định (P6), kiến trúc được mở rộng lên Cloud ở Giai đoạn P7 mà **không cần sửa bất kỳ dòng logic code nào** (chỉ thay đổi cấu hình biến môi trường):

```mermaid
flowchart TB
    subgraph PUBLIC["Internet"]
        USER["Khách truy cập Website"]
    end

    subgraph VERCEL["Vercel Cloud (24/7)"]
        SPA["Landing Page SPA\n(Home, Menu, Product, About, Promotions, Visit)"]
    end

    subgraph RENDER["Render Cloud - Singapore (24/7)"]
        API["FastAPI Landing Backend\n- Storefront Read API\n- Hybrid RAG Orchestrator\n- Answer Cache & SQL Fast-path"]
    end

    subgraph NEON["Neon Cloud - Singapore (24/7)"]
        PG[("PostgreSQL 17\n- Catalog (Stores, Menu, Promotions)\n- Vector KB (pgvector + FTS + trgm)\n- Chat Sessions & Answer Cache")]
    end

    subgraph CF["Cloudflare Edge (Zero Trust)"]
        ZT["Cloudflare Access\n(Kiểm tra CF-Access-Client-Id/Secret)"]
        WAF["WAF Rule\n(Chỉ mở /api/chat, /api/embed, /api/version, /api/ps)"]
    end

    subgraph PC["Máy tính cá nhân (Windows / Linux)"]
        TUNNEL["cloudflared daemon\n(Outbound QUIC/HTTP2)"]
        OLLAMA["Ollama Server\n(127.0.0.1:11434)"]
        CLI["Scripts CLI (Đồng bộ dữ liệu lên Neon)\n- seed_database.py\n- ingest_knowledge.py\n- prewarm_cache.py"]
    end

    USER -->|HTTPS| SPA
    USER -->|"HTTPS REST + SSE"| API
    API -->|"TLS (landing_app_user)"| PG
    API -->|"HTTPS + Service Token"| ZT
    ZT --> WAF
    WAF <-->|"Outbound Tunnel"| TUNNEL
    TUNNEL -->|"Host: 127.0.0.1:11434"| OLLAMA
    CLI -->|"http://127.0.0.1:11434"| OLLAMA
    CLI -->|"TLS (cafe_owner)"| PG
```

### 3.3. Luồng xử lý hội thoại Bean AI (Online & Offline-Resilient)

Luồng xử lý này hoạt động **giống hệt nhau trên cả môi trường Local lẫn Production**:

```mermaid
sequenceDiagram
    autonumber
    participant U as Khách hàng (Browser)
    participant R as FastAPI Backend (Local / Render)
    participant D as PostgreSQL (Local Native / Neon)
    participant T as Ollama (Local 127.0.0.1 / Cloudflare Tunnel)

    U->>R: POST /api/v1/chat/sessions/{id}/messages
    R->>D: Xác thực session token hash, kiểm tra rate limit, lưu user message
    R-->>U: event: meta + status(retrieving)
    R->>R: Chuẩn hóa tiếng Việt + Phân loại Intent + Trích xuất bộ lọc (giá, danh mục, vị)

    alt 1. SQL Fast-path (Hỏi giá, danh sách món theo giá, giờ mở cửa, khuyến mãi)
        R->>D: Truy vấn SQL chuẩn xác
        R-->>U: event: products + token (Template song ngữ) + done (< 1s)
    else 2. Khớp Answer Cache trên Postgres (Câu hỏi FAQ / Kiến thức phổ biến)
        R->>D: Tra bảng answer_cache (exact hoặc pg_trgm similarity >= 0.78)
        R-->>U: event: products + token + sources + done (< 1s, cached=true)
    else 3. Câu hỏi tư vấn / Kiến thức mới
        R->>D: SQL Retrieval (lấy các món phù hợp điều kiện giá/danh mục)
        R-->>U: event: products (Hiển thị thẻ sản phẩm ngay lập tức)
        alt Ollama AI Node đang Bật (Circuit Closed)
            R->>T: POST /api/embed (bge-m3)
            R->>D: Dense Search (pgvector) + Lexical Search (FTS/trgm) -> RRF Fusion
            R-->>U: event: status(generating)
            R->>T: POST /api/chat (qwen3, stream=true, think=false)
            loop Stream từng token
                T-->>R: NDJSON chunk
                R-->>U: event: token
            end
            R-->>U: event: sources + done
            R->>D: Lưu câu trả lời + ghi vào answer_cache
        else Ollama AI Node đang Tắt (Circuit Open hoặc lỗi kết nối / HTTP 530/502)
            R->>D: Lexical Search (FTS + pg_trgm) trên document_chunks
            R-->>U: event: token (Tóm tắt thông tin từ tài liệu tìm được + gợi ý từ menu)
            R-->>U: event: sources + done (degraded=true)
        end
    end
```

---

## 4. Thiết kế Database & Quản trị dữ liệu không cần Admin UI

Database PostgreSQL 17 (`pgvector`, `pg_trgm`, `unaccent`, `pgcrypto`) đóng vai trò **Shared Source of Truth** cho toàn bộ `cafe-digital-platform`.
- **Trong giai đoạn phát triển (P0–P6 — Không dùng Docker):** Toàn bộ bảng được khởi tạo và kiểm thử trên **PostgreSQL 17 Native trên Windows (`localhost:5432`)** (hoặc một database `dev` trên Neon nếu bạn không muốn cài Postgres vào máy).
- **Trong giai đoạn deploy (P7):** Chạy đúng bộ Alembic migrations đó lên **Neon PostgreSQL Production** để đồng bộ schema 100%.

### 4.1. Sơ đồ ERD cho Ứng dụng 1 (Landing Page & Bean AI)

```mermaid
erDiagram
    STORES ||--o{ STORE_HOURS : has
    STORES ||--o{ CHAT_SESSIONS : receives
    MENU_CATEGORIES ||--o{ PRODUCTS : contains
    PRODUCTS ||--o{ PRODUCT_VARIANTS : has
    PRODUCTS ||--o{ PRODUCT_INGREDIENTS : uses
    INGREDIENTS ||--o{ PRODUCT_INGREDIENTS : included_in
    PROMOTIONS ||--o{ PROMOTION_PRODUCTS : applies_to
    PRODUCTS ||--o{ PROMOTION_PRODUCTS : promoted_by

    KNOWLEDGE_SOURCES ||--o{ KNOWLEDGE_DOCUMENTS : contains
    KNOWLEDGE_DOCUMENTS ||--o{ DOCUMENT_CHUNKS : split_into

    CHAT_SESSIONS ||--o{ CHAT_MESSAGES : contains
    CHAT_MESSAGES ||--o{ CHAT_FEEDBACK : receives
```

### 4.2. Chi tiết Schema (SQLAlchemy / Alembic DDL)

#### A. Nhóm bảng Storefront Catalog (Nguồn dữ liệu chuẩn cho UI & SQL Retrieval)

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE stores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(150) NOT NULL,
    address TEXT NOT NULL,
    district VARCHAR(100),
    city VARCHAR(100) DEFAULT 'TP. Hồ Chí Minh',
    phone VARCHAR(30),
    google_maps_url TEXT,
    latitude NUMERIC(9,6),
    longitude NUMERIC(9,6),
    amenities JSONB DEFAULT '[]'::jsonb,       -- ["wifi", "parking", "ac", "work_friendly"]
    image_url TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE store_hours (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
    day_of_week SMALLINT NOT NULL CHECK (day_of_week BETWEEN 0 AND 6), -- 0=Monday..6=Sunday
    open_time TIME NOT NULL,
    close_time TIME NOT NULL,
    is_closed BOOLEAN DEFAULT FALSE,
    UNIQUE (store_id, day_of_week)
);

CREATE TABLE menu_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug VARCHAR(100) UNIQUE NOT NULL,
    name_vi VARCHAR(120) NOT NULL,
    name_en VARCHAR(120) NOT NULL,
    description_vi TEXT,
    description_en TEXT,
    display_order SMALLINT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category_id UUID NOT NULL REFERENCES menu_categories(id),
    slug VARCHAR(120) UNIQUE NOT NULL,
    name_vi VARCHAR(150) NOT NULL,
    name_en VARCHAR(150) NOT NULL,
    short_description_vi TEXT NOT NULL,
    short_description_en TEXT,
    story_vi TEXT,                              -- Mô tả sâu cho trang Product Detail
    image_url TEXT NOT NULL,
    -- Thuộc tính có cấu trúc phục vụ bộ lọc UI và SQL Recommendation của Bean AI
    taste_tags JSONB DEFAULT '[]'::jsonb,       -- ["sweet", "creamy", "less_bitter", "fruity"]
    caffeine_level VARCHAR(20) DEFAULT 'medium' CHECK (caffeine_level IN ('none', 'low', 'medium', 'high')),
    bitterness_level SMALLINT DEFAULT 3 CHECK (bitterness_level BETWEEN 1 AND 5),
    sweetness_level SMALLINT DEFAULT 3 CHECK (sweetness_level BETWEEN 1 AND 5),
    has_milk BOOLEAN DEFAULT FALSE,
    is_signature BOOLEAN DEFAULT FALSE,
    is_featured BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    display_order SMALLINT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE product_variants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    sku VARCHAR(60) UNIQUE NOT NULL,            -- Sẵn sàng kết nối với App 2 (Online Ordering)
    size VARCHAR(20) NOT NULL CHECK (size IN ('small', 'regular', 'large')),
    temperature VARCHAR(20) DEFAULT 'both' CHECK (temperature IN ('hot', 'iced', 'both')),
    price_vnd INTEGER NOT NULL CHECK (price_vnd >= 0),
    calories_kcal SMALLINT,
    is_available BOOLEAN DEFAULT TRUE,
    UNIQUE (product_id, size)
);

CREATE TABLE ingredients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(60) UNIQUE NOT NULL,
    name_vi VARCHAR(120) NOT NULL,
    name_en VARCHAR(120) NOT NULL,
    allergen_code VARCHAR(50)                   -- 'DAIRY', 'NUTS', 'SOY', 'GLUTEN', NULL
);

CREATE TABLE product_ingredients (
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    ingredient_id UUID NOT NULL REFERENCES ingredients(id) ON DELETE CASCADE,
    is_optional BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (product_id, ingredient_id)
);

CREATE TABLE promotions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug VARCHAR(120) UNIQUE NOT NULL,
    title_vi VARCHAR(200) NOT NULL,
    title_en VARCHAR(200),
    summary_vi TEXT NOT NULL,
    conditions_vi TEXT NOT NULL,
    promo_code VARCHAR(50),                     -- Mã ưu đãi để khách dùng ở quầy hoặc trên App 2
    discount_type VARCHAR(20) NOT NULL CHECK (discount_type IN ('percentage', 'fixed_amount', 'bundle')),
    discount_value INTEGER NOT NULL,
    banner_image_url TEXT,
    start_at TIMESTAMPTZ NOT NULL,
    end_at TIMESTAMPTZ NOT NULL,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE promotion_products (
    promotion_id UUID NOT NULL REFERENCES promotions(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    PRIMARY KEY (promotion_id, product_id)
);
```

#### B. Nhóm bảng Knowledge Base & Hybrid RAG

```sql
CREATE TABLE knowledge_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_key VARCHAR(150) UNIQUE NOT NULL,    -- VD: 'coffee_guide/cold_brew.md'
    source_type VARCHAR(30) NOT NULL DEFAULT 'markdown',
    title VARCHAR(255) NOT NULL,
    checksum VARCHAR(64) NOT NULL,
    current_version INTEGER DEFAULT 1,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE knowledge_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL REFERENCES knowledge_sources(id) ON DELETE CASCADE,
    doc_key VARCHAR(150) NOT NULL,
    title VARCHAR(255) NOT NULL,
    category VARCHAR(50) NOT NULL,              -- MENU | COFFEE_GUIDE | FAQ | POLICY | BRAND | STORE
    language VARCHAR(10) DEFAULT 'vi',
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    version INTEGER NOT NULL DEFAULT 1,
    content_hash VARCHAR(64) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (doc_key, version)
);

CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES knowledge_documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    search_text TEXT NOT NULL,                  -- Chuẩn hóa NFC + bản không dấu
    search_vector TSVECTOR GENERATED ALWAYS AS (to_tsvector('simple', search_text)) STORED,
    embedding VECTOR(1024) NOT NULL,
    embedding_model VARCHAR(100) NOT NULL,
    token_count INTEGER,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (document_id, chunk_index)
);

CREATE INDEX idx_chunks_embedding ON document_chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX idx_chunks_search_fts ON document_chunks USING gin (search_vector);
CREATE INDEX idx_chunks_search_trgm ON document_chunks USING gin (search_text gin_trgm_ops);
CREATE INDEX idx_chunks_metadata ON document_chunks USING gin (metadata);
```

#### C. Nhóm bảng Hội thoại & Answer Cache

```sql
CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_token_hash VARCHAR(128) NOT NULL,
    store_id UUID REFERENCES stores(id),
    language VARCHAR(10) DEFAULT 'vi',
    preferences JSONB DEFAULT '{}'::jsonb,      -- Lưu khẩu vị/ngân sách trích xuất trong phiên
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    client_message_id VARCHAR(64),
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    status VARCHAR(20) DEFAULT 'completed',     -- streaming | completed | failed | cancelled
    content TEXT NOT NULL,
    intent VARCHAR(50),
    model VARCHAR(100),
    ttft_ms INTEGER,
    latency_ms INTEGER,
    cached BOOLEAN DEFAULT FALSE,
    degraded BOOLEAN DEFAULT FALSE,
    retrieved_chunk_ids JSONB DEFAULT '[]'::jsonb,
    recommended_product_slugs JSONB DEFAULT '[]'::jsonb,
    citations JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_chat_messages_session ON chat_messages (session_id, created_at);
CREATE UNIQUE INDEX uq_chat_client_msg ON chat_messages (session_id, client_message_id)
    WHERE client_message_id IS NOT NULL;

CREATE TABLE chat_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID UNIQUE NOT NULL REFERENCES chat_messages(id) ON DELETE CASCADE,
    rating SMALLINT NOT NULL CHECK (rating IN (-1, 1)),
    comment TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE answer_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    normalized_query TEXT NOT NULL,
    language VARCHAR(10) NOT NULL DEFAULT 'vi',
    intent VARCHAR(50) NOT NULL,
    query_embedding VECTOR(1024),
    answer TEXT NOT NULL,
    product_slugs JSONB DEFAULT '[]'::jsonb,
    citations JSONB DEFAULT '[]'::jsonb,
    knowledge_version INTEGER NOT NULL DEFAULT 1,
    hit_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    UNIQUE (normalized_query, language, intent, knowledge_version)
);
CREATE INDEX idx_answer_cache_trgm ON answer_cache USING gin (normalized_query gin_trgm_ops);
```

### 4.3. Quy trình quản trị dữ liệu bằng CLI (Khi chưa xây Ứng dụng 3 — Admin Dashboard)

Vì Ứng dụng 3 (Admin Dashboard) là một dự án độc lập phát triển sau, toàn bộ dữ liệu của Landing Page được quản lý theo mô hình **Data-as-Code** (chạy với Docker Postgres Local trong giai đoạn P1–P6, và chạy với Neon Postgres trong giai đoạn P7):

1. **Cập nhật Menu, Giá, Cửa hàng, Khuyến mãi:**
   - Sửa các file JSON có cấu trúc trong `data/seed/` (`stores.json`, `categories.json`, `ingredients.json`, `products.json`, `promotions.json`).
   - Chạy `python scripts/seed_database.py` → script validate bằng Pydantic và thực hiện `UPSERT` (`ON CONFLICT (slug) DO UPDATE`) vào PostgreSQL theo `MIGRATION_DATABASE_URL`.
2. **Cập nhật Tri thức cho Bean AI:**
   - Thêm/sửa các file Markdown trong `data/knowledge_base/` (`menu/`, `coffee_guide/`, `faq/`, `policies/`, `brand/`).
   - Chạy `python scripts/ingest_knowledge.py`:
     - Script tính `SHA-256` checksum từng file; chỉ những file có thay đổi mới được chunk lại và gửi tới `http://127.0.0.1:11434/api/embed` (`bge-m3`) ngay trên PC.
     - Trong 1 transaction vào PostgreSQL: ghi chunks phiên bản mới, đánh dấu `is_active = false` cho phiên bản cũ, và vô hiệu các bản ghi `answer_cache` cũ.
   - Chạy `python scripts/prewarm_cache.py` để sinh trước câu trả lời chuẩn cho 40+ câu hỏi thường gặp lưu vào bảng `answer_cache`.

---

## 5. Thiết kế chi tiết Frontend Landing Page & UX Bean AI

### 5.1. Danh sách các trang (Routes) của Landing Page

Ứng dụng Frontend chỉ bao gồm **6 route public** (không có `/admin/*`):

| Route | Trang | Nội dung & Khu vực chức năng chính |
|---|---|---|
| `/` | **HomePage** | • **Hero Section:** Định vị thương hiệu BREW & BEAN, nút CTA *"Khám phá Menu"* và nút *"Hỏi Bean AI Barista"* (mở khung tư vấn kèm gợi ý theo thời điểm sáng/chiều/tối).<br>• **Signature Drinks Carousel:** 4–6 món đặc trưng lấy từ `/api/v1/menu/products?signature=true`.<br>• **Interactive Taste Finder (Điểm nhấn AI):** Thanh chọn nhanh khẩu vị (*Ít đắng / Ngọt dịu / Không caffeine / Dưới 45k*) → bấm *"Nhờ Bean AI chọn món"* sẽ mở thẳng Chat Widget với câu hỏi được tạo sẵn.<br>• **Brand Craft Section:** Câu chuyện hạt Arabica Cầu Đất & Robusta Buôn Ma Thuột.<br>• **Active Promotions Banner** & **Store Locator Preview**. |
| `/menu` | **MenuPage** | • Bộ lọc đa chiều: Danh mục (`Coffee`, `Cold Brew`, `Matcha & Tea`, `Signature`, `Pastry`), mức giá (`≤ 40k`, `≤ 50k`), mức caffeine, có sữa/không sữa, từ khóa tìm kiếm.<br>• Lưới Product Card hiển thị ảnh `.webp`, tên song ngữ, tag hương vị, giá theo size và nút *"Hỏi AI về món này"*. |
| `/menu/:slug` | **ProductDetailPage** | • Ảnh sản phẩm độ phân giải cao, câu chuyện đồ uống (`story_vi`).<br>• **Thanh chỉ số hương vị trực quan (Flavor Meter):** Độ đắng (1–5), Độ ngọt (1–5), Mức Caffeine.<br>• Bảng chọn Size (`S/M/L`) & Nhiệt độ (`Nóng/Đá`) kèm giá VND và lượng Calo.<br>• Danh sách thành phần & **Cảnh báo dị ứng rõ ràng** (`DAIRY`, `NUTS`...).<br>• **2 nút CTA:** (1) *"Hỏi Bean AI cách thưởng thức / điều chỉnh vị"*, (2) *"Đặt món ngay"* (liên kết sang Ứng dụng 2 `VITE_ORDERING_APP_URL/order?sku=...` hoặc modal đặt nhanh). |
| `/about` | **AboutPage** | • Câu chuyện thương hiệu BREW & BEAN, nguồn gốc vùng trồng, quy trình rang xay & các phương pháp pha chế (Espresso, Cold Brew 18 giờ, Pour-over). |
| `/promotions` | **PromotionPage** | • Danh sách chương trình ưu đãi đang áp dụng từ `/api/v1/promotions/active`, mã promo code (nút Copy), điều kiện áp dụng và danh sách món được giảm giá. |
| `/visit` | **VisitPage** | • Danh sách chi nhánh, giờ mở cửa theo từng ngày trong tuần (hiển thị badge *"Đang mở cửa"* / *"Đã đóng cửa"* theo giờ thực tế), tiện ích (Wi-Fi, chỗ đậu xe, không gian làm việc) và link Google Maps. |

### 5.2. Kiến trúc Component của Bean AI Chat Widget

Bean AI không chỉ nằm ở góc dưới màn hình mà được **tích hợp ngữ cảnh (contextual trigger)** vào từng trang của Landing Page:

```text
apps/landing-page/src/features/chat/
├── components/
│   ├── ChatWidget.tsx                 # Floating button + điều phối đóng/mở dialog
│   ├── ChatWindow.tsx                 # Khung chat chính (Desktop: panel 420px; Mobile: full-screen drawer)
│   ├── ChatHeader.tsx                 # Tên "Bean AI Barista", badge trạng thái (Trực tuyến / Tra cứu nhanh), nút Làm mới
│   ├── ChatMessageList.tsx            # Danh sách tin nhắn tự động cuộn mượt khi stream
│   ├── ChatMessage.tsx                # Render Markdown an toàn + danh sách Product Cards + Citations
│   ├── ProductRecommendationCard.tsx  # Card sản phẩm lấy từ SQL (ảnh, tên, size, giá, link chi tiết, nút Đặt món)
│   ├── SourceCitationBadge.tsx        # Popover hiển thị nguồn tri thức (VD: "Cẩm nang Cold Brew")
│   ├── SuggestedQuestions.tsx         # Chips câu hỏi gợi ý thay đổi theo trang khách đang xem
│   ├── TypingAndStageIndicator.tsx    # Hiển thị "Đang tìm trong menu..." -> "Bean AI đang pha câu trả lời..."
│   └── ChatInput.tsx                  # Ô nhập (tối đa 1.000 ký tự), phím tắt Enter, nút Dừng (Stop generation)
├── context/
│   └── ChatWidgetContext.tsx          # Cho phép bất kỳ nút nào trên trang gọi openChatWithPrompt("...")
├── hooks/
│   ├── useChatSession.ts              # Khởi tạo & lưu session token vào sessionStorage
│   └── useChatStream.ts               # Xử lý SSE qua @microsoft/fetch-event-source
└── types.ts
```

---

## 6. Thiết kế Backend API & Hybrid RAG Pipeline

### 6.1. Toàn bộ API Contract của Ứng dụng 1 (`/api/v1`)

Backend của Landing Page chỉ cung cấp **12 endpoint gọn nhẹ, rõ ràng**:

| Nhóm | Method | Endpoint | Mô tả |
|---|---|---|---|
| **Health** | `GET` | `/health` | Liveness check & warm-up từ Frontend (không chạm DB/Ollama) |
| **Health** | `GET` | `/ready` | Kiểm tra kết nối PostgreSQL & trạng thái Ollama AI Node (`online` / `fast_lookup_only`) |
| **Storefront** | `GET` | `/api/v1/storefront` | Thông tin tổng quan thương hiệu, số liệu nổi bật & `ai_mode` (`online` / `fast_lookup_only`) |
| **Storefront** | `GET` | `/api/v1/stores` | Danh sách chi nhánh kèm giờ mở cửa & trạng thái đang mở/đóng |
| **Storefront** | `GET` | `/api/v1/stores/{slug}` | Chi tiết một chi nhánh |
| **Menu** | `GET` | `/api/v1/menu/categories` | Danh sách danh mục đồ uống |
| **Menu** | `GET` | `/api/v1/menu/products` | Lọc sản phẩm theo `category`, `max_price`, `caffeine_level`, `has_milk`, `taste_tag`, `signature`, `q` |
| **Menu** | `GET` | `/api/v1/menu/products/{slug}` | Chi tiết sản phẩm, variants (size/giá/calo), nguyên liệu & mã dị ứng |
| **Promotions** | `GET` | `/api/v1/promotions/active` | Các chương trình khuyến mãi đang trong thời hạn hiệu lực |
| **Bean AI** | `POST` | `/api/v1/chat/sessions` | Tạo phiên chat ẩn danh, trả về `session_id` và `session_token` |
| **Bean AI** | `POST` | `/api/v1/chat/sessions/{id}/messages` | Gửi tin nhắn & nhận phản hồi **SSE Streaming** |
| **Bean AI** | `POST` | `/api/v1/chat/messages/{id}/feedback` | Gửi đánh giá 👍 (`1`) / 👎 (`-1`) và góp ý cho câu trả lời |

### 6.2. Định tuyến Intent & Kết hợp SQL + Hybrid RAG

Với sự bổ sung các cột thuộc tính có cấu trúc (`bitterness_level`, `sweetness_level`, `caffeine_level`, `has_milk`, `taste_tags`) trong bảng `products`, khả năng tư vấn bằng SQL của hệ thống mạnh và chính xác hơn hẳn:

| Intent | Ví dụ câu hỏi của khách | Nguồn dữ liệu xử lý | Hoạt động khi tắt Ollama / tắt PC? |
|---|---|---|---|
| `PRODUCT_LOOKUP` | *"Caramel Latte size L giá bao nhiêu?"* | **SQL Fast-path** (trả lời bằng template + Product Card) | **Có (100%)** |
| `STORE_INFO` | *"Quán ở Quận 1 mấy giờ đóng cửa, có chỗ đậu ô tô không?"* | **SQL Fast-path** (`stores` + `store_hours`) | **Có (100%)** |
| `PROMOTION_LOOKUP` | *"Hôm nay quán có mã giảm giá nào không?"* | **SQL Fast-path** (`promotions`) | **Có (100%)** |
| `PRODUCT_RECOMMENDATION` | *"Mình muốn đồ uống ít đắng, béo nhẹ, dưới 50k uống buổi chiều"* | **SQL Filter** (`price <= 50000`, `bitterness <= 2`, `has_milk = true`) + **Hybrid RAG** (mô tả hương vị) → **Qwen3 tổng hợp** | **Có một phần** (Vẫn lọc đúng Product Cards bằng SQL + Lexical Search khi tắt Ollama) |
| `COFFEE_KNOWLEDGE` | *"Cold Brew khác gì Espresso pha đá?"* | **Answer Cache** → nếu chưa có: **Hybrid RAG** (`pgvector` + `FTS`/`pg_trgm`, RRF `k=60`) → **Qwen3** | **Có** với các câu đã pre-warm trong Cache; hoặc trích đoạn Lexical Search |
| `ALLERGEN_INGREDIENT` | *"Mình bị dị ứng sữa bò thì uống món nào được?"* | **SQL Ingredient Check** (`allergen_code != 'DAIRY'`) + quy tắc an toàn dị ứng nghiêm ngặt | **Có (100%)** |
| `OUT_OF_SCOPE` | *"Viết giúp mình đoạn code Python"* | Từ chối lịch sự bằng template (không tốn tài nguyên gọi LLM) | **Có (100%)** |

---

## 7. Cấu trúc Repository (`cafe-digital-platform`)

Cấu trúc thư mục được tổ chức theo hướng **Multi-App Platform**, trong đó giai đoạn này triển khai đầy đủ `apps/landing-page` và `services/landing-api`, đồng thời để sẵn vị trí rõ ràng cho 2 ứng dụng độc lập tiếp theo:

```text
cafe-digital-platform/
├── .github/
│   └── workflows/
│       ├── ci-landing.yml              # Lint + test cho landing-page & landing-api
│       ├── db-backup.yml               # pg_dump Neon hằng ngày (Kích hoạt ở Giai đoạn P7)
│       └── smoke-landing.yml           # Smoke test production (Kích hoạt ở Giai đoạn P7)
│
├── apps/
│   ├── landing-page/                   # [ỨNG DỤNG 1 - TRỌNG TÂM] React + Vite + TS
│   │   ├── public/
│   │   │   ├── images/
│   │   │   └── fonts/
│   │   ├── src/
│   │   │   ├── app/                    # router.tsx, providers.tsx
│   │   │   ├── pages/                  # HomePage, MenuPage, ProductDetailPage, AboutPage, PromotionPage, VisitPage
│   │   │   ├── features/
│   │   │   │   ├── menu/               # Filter, FlavorMeter, ProductGrid, ProductCard
│   │   │   │   ├── store/              # StoreCard, OpeningStatusBadge
│   │   │   │   ├── promotion/          # PromotionBanner, PromoCodeCopy
│   │   │   │   └── chat/               # Bean AI ChatWidget, SSE hook, ProductRecommendationCard
│   │   │   ├── components/             # ui/ (shadcn), layout/ (Navbar, Footer), shared/
│   │   │   └── lib/                    # api-client.ts, sse-client.ts, warmup.ts
│   │   ├── vercel.json                 # Dùng khi deploy lên Vercel ở giai đoạn cuối P7
│   │   ├── package.json
│   │   └── vite.config.ts
│   │
│   ├── online-ordering/                # [ỨNG DỤNG 2 - TƯƠNG LAI] Website đặt hàng trực tuyến (Độc lập)
│   │   └── README.md
│   │
│   └── admin-dashboard/                # [ỨNG DỤNG 3 - TƯƠNG LAI] Admin & AI/ML Forecasting (Độc lập)
│       └── README.md
│
├── services/
│   └── landing-api/                    # [BACKEND ỨNG DỤNG 1] FastAPI + Hybrid RAG
│       ├── app/
│       │   ├── main.py                 # FastAPI entrypoint
│       │   ├── api/v1/endpoints/       # storefront.py, menu.py, stores.py, promotions.py, chat.py, health.py
│       │   ├── core/                   # config.py, security.py, logging.py, exceptions.py
│       │   ├── db/                     # base.py, session.py
│       │   ├── models/                 # store.py, menu.py, promotion.py, knowledge.py, conversation.py
│       │   ├── schemas/                # menu.py, store.py, promotion.py, chat.py
│       │   ├── repositories/           # menu_repo.py, store_repo.py, promotion_repo.py, knowledge_repo.py, chat_repo.py
│       │   ├── services/               # storefront_service.py, menu_service.py, chat_service.py
│       │   └── integrations/           # ollama_client.py (Local HTTP + Cloudflare Access + Circuit Breaker)
│       ├── rag/
│       │   ├── text/normalize.py       # Chuẩn hóa tiếng Việt dùng chung
│       │   ├── ingestion/              # loaders, cleaner, chunker, embedder, indexer
│       │   ├── retrieval/              # query_parser, dense, lexical, sql_retriever, rrf, context_builder
│       │   ├── generation/             # prompts/, intent_router, fast_path, answer_generator
│       │   └── evaluation/             # dataset.jsonl, retrieval_metrics.py, generation_metrics.py, run_evaluation.py
│       ├── alembic/
│       ├── tests/                      # unit/, integration/, rag/
│       ├── requirements-api.txt        # Cài cho FastAPI runtime
│       ├── requirements-cli.txt        # Cài trên PC (thêm công cụ ingest & evaluation)
│       └── requirements-dev.txt
│
├── data/
│   ├── seed/                           # Dữ liệu chuẩn quản lý qua Git
│   │   ├── stores.json
│   │   ├── categories.json
│   │   ├── ingredients.json
│   │   ├── products.json
│   │   └── promotions.json
│   └── knowledge_base/                 # Tài liệu Markdown cho Bean AI RAG
│       ├── menu/
│       ├── coffee_guide/
│       ├── faq/
│       ├── policies/
│       └── brand/
│
├── scripts/                            # Chạy trực tiếp trên PC (với Local DB ở P1-P6, với Neon ở P7)
│   ├── sql/init_neon.sql               # Script khởi tạo extensions & phân quyền DB
│   ├── seed_database.py                # Upsert data/seed/*.json vào PostgreSQL
│   ├── ingest_knowledge.py             # Chunk + gọi Ollama local (127.0.0.1) + lưu vector vào PostgreSQL
│   └── prewarm_cache.py                # Sinh trước câu trả lời cho 40+ câu hỏi phổ biến vào answer_cache
│
├── deploy/
│   └── pc/                             # Bộ công cụ vận hành Ollama & Cloudflare Tunnel trên PC
│       ├── cloudflared-config.yml.example
│       ├── setup-ollama-env.ps1
│       ├── start-ai-node.ps1
│       ├── stop-ai-node.ps1
│       ├── status-ai-node.ps1
│       ├── backup_db.ps1
│       └── bench_ollama.py
│
├── docker-compose.yml                  # [TÙY CHỌN] Không dùng trong P0-P6 (chỉ dùng nếu cần đóng gói container khi deploy)
├── render.yaml                         # Render Blueprint (Chỉ dùng khi bắt đầu Deploy ở giai đoạn P7)
└── README.md
```

---

## 8. Hướng dẫn Thiết lập & Vận hành trên môi trường Local — Không dùng Docker (Giai đoạn Phát triển)

Toàn bộ quá trình phát triển từ **Giai đoạn P0 đến P6** chạy trực tiếp (Native) trên Windows theo 5 bước dưới đây — **hoàn toàn không sử dụng Docker Desktop** (giúp tiết kiệm 2–4 GB RAM cho Ollama), và cũng chưa cần đụng tới Cloudflare Tunnel, Render hay Vercel:

### 8.1. Bước 1: Cài đặt & tối ưu Ollama Local trên PC
```powershell
winget install Ollama.Ollama

# Thiết lập biến môi trường an toàn (chỉ nghe trên 127.0.0.1:11434)
.\deploy\pc\setup-ollama-env.ps1

# Tải model phục vụ embedding và sinh câu trả lời
ollama pull bge-m3
ollama pull qwen3:8b    # Dùng nếu PC có GPU rời >= 6GB VRAM
ollama pull qwen3:4b    # Dùng nếu PC chỉ chạy CPU hoặc để benchmark so sánh

# Chạy benchmark để đo TTFT và tokens/sec thực tế trên máy
python deploy/pc/bench_ollama.py
```

### 8.2. Bước 2: Thiết lập PostgreSQL 17 + `pgvector` cho Local (Không dùng Docker)

Bạn có thể chọn **1 trong 2 cách không cần Docker** dưới đây:

- **Cách A — Chạy PostgreSQL 17 Native trực tiếp trên Windows (`localhost:5432`, 100% Offline, tốn < 50 MB RAM):**
  1. Cài đặt PostgreSQL 17 cho Windows (`winget install PostgreSQL.PostgreSQL.17`) và giải nén bản binary [`pgvector` cho Windows](https://github.com/pgvector/pgvector/releases) vào thư mục cài đặt PostgreSQL (`C:\Program Files\PostgreSQL\17\`).
  2. Tạo user `cafe_owner`, database `cafe_db` và bật các extension:
     ```powershell
     psql -U postgres -c "CREATE ROLE cafe_owner WITH LOGIN PASSWORD 'password' SUPERUSER;"
     psql -U postgres -c "CREATE DATABASE cafe_db OWNER cafe_owner;"
     psql -U cafe_owner -d cafe_db -f scripts/sql/init_neon.sql
     ```
- **Cách B — Không cần cài cả Docker lẫn PostgreSQL vào máy (Zero-Install DB):**
  - Tạo nhanh một database `dev` miễn phí trên **Neon** (đã cài sẵn `vector`, `pg_trgm`, `unaccent`, `pgcrypto`) và dán `DATABASE_URL` vào `services/landing-api/.env`. Toàn bộ FastAPI (`localhost:8000`), React (`localhost:5173`), CLI scripts và Ollama (`127.0.0.1:11434`) vẫn chạy 100% trên Local mà máy bạn không phải gánh bất kỳ tiến trình Database hay Docker nào.

### 8.3. Bước 3: Chạy Migration & Khởi động Backend FastAPI trên Local (Python `.venv` Native)
```powershell
cd services/landing-api
copy .env.example .env
# Kiểm tra DATABASE_URL / MIGRATION_DATABASE_URL và OLLAMA_BASE_URL=http://127.0.0.1:11434 trong .env

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt

# Chạy Alembic migration
alembic upgrade head

# Khởi động FastAPI server ở chế độ hot-reload
uvicorn app.main:app --reload --port 8000
```
Kiểm tra tại:
- `http://localhost:8000/health` → `{"status": "ok"}`
- `http://localhost:8000/ready` → kiểm tra kết nối tới PostgreSQL & Ollama Local (`127.0.0.1:11434`).
- `http://localhost:8000/docs` → giao diện Swagger UI để test toàn bộ 12 API.

### 8.4. Bước 4: Nạp dữ liệu Seed, Ingest Knowledge Base & Prewarm Cache trên Local
```powershell
# Tại thư mục gốc cafe-digital-platform (với virtualenv đã kích hoạt)
python scripts/seed_database.py
python scripts/ingest_knowledge.py --path data/knowledge_base
python scripts/prewarm_cache.py
```

### 8.5. Bước 5: Khởi động Frontend React Landing Page trên Local (Node.js Native)
```powershell
cd apps/landing-page
copy .env.example .env
# Mặc định VITE_API_BASE_URL=http://localhost:8000/api/v1

npm install
npm run dev
```
Truy cập `http://localhost:5173` để phát triển, trải nghiệm toàn bộ 6 trang của Landing Page và trò chuyện trực tiếp với Bean AI ngay trên máy local.

---

## 9. Kiểm thử, RAG Evaluation & Nghiệm thu ổn định trên Local (Quality Gate trước khi Deploy)

> **Nguyên tắc bắt buộc (Local Stability Gate):** Chúng ta **chỉ bắt đầu bước sang Giai đoạn P7 (Setup Hạ tầng & Deploy Cloud)** sau khi toàn bộ hệ thống chạy trên Local vượt qua đầy đủ các bài kiểm thử tự động, bộ đánh giá RAG 80 câu và đạt tất cả chỉ tiêu SLO dưới đây.

### 9.1. Bộ kiểm thử tự động trên Local (Unit, Integration & Build Test)

1. **Backend Test Suite (`services/landing-api`):**
   ```powershell
   cd services/landing-api
   ruff check .
   pytest -v
   ```
   - Kiểm tra toàn bộ 12 endpoint (`/health`, `/ready`, `/storefront`, `/stores`, `/menu/*`, `/promotions/active`, `/chat/*`).
   - Kiểm tra bộ lọc đa chiều (`category`, `max_price`, `caffeine_level`, `has_milk`, `taste_tag`, `signature`, `q`).
   - Kiểm tra chuẩn hóa tiếng Việt (`normalize.py`), Query Parser, Intent Router, RRF Fusion (`k=60`) và hậu kiểm giá/dị ứng.
2. **Frontend Test & Production Build Verification (`apps/landing-page`):**
   ```powershell
   cd apps/landing-page
   npm run lint
   npm run build
   npm run preview
   ```
   - Đảm bảo TypeScript compile không lỗi (`tsc -b`), bundle size tối ưu, và bản build chạy mượt trên `vite preview` kết nối với FastAPI local.

### 9.2. Ba bài kiểm thử nghiệp vụ bắt buộc trên Local + Bộ 80 câu RAG Evaluation

```powershell
# Chạy bộ đánh giá chất lượng RAG 80 câu hỏi ngay trên Local
python -m services.landing_api.rag.evaluation.run_evaluation
```

1. **Exact Price & Variant Test (Độ chính xác 100%):** Hỏi giá 15 món ở các size khác nhau trên Local → giá trong câu trả lời và trên Product Card phải khớp tuyệt đối với `product_variants.price_vnd` trong PostgreSQL.
2. **Allergen & Grounding Safety Test (≥ 90% Abstention & 100% Allergen Safety):** Hỏi về món cho người dị ứng sữa/hạt hoặc thông tin không có trong tài liệu → Bean AI chỉ gợi ý món đã được xác minh trong bảng `product_ingredients` và từ chối suy đoán khi thiếu dữ liệu.
3. **Offline Ollama Resilience Test (Giả lập tắt AI Node ngay trên Local):** Tắt tiến trình Ollama trên máy (`Stop-Process -Name "ollama*"`) trong khi vẫn giữ FastAPI + React + PostgreSQL chạy → thực hiện 10 thao tác duyệt Landing Page và gửi 10 câu hỏi chat (giá, khuyến mãi, gợi ý món dưới 50k, FAQ đã cache) → 100% nhận được phản hồi hợp lệ và Product Cards trong < 2s mà không văng lỗi UI.

### 9.3. Chỉ tiêu chất lượng & hiệu năng (SLO) cần đạt trước khi Deploy

| Chỉ số | Mục tiêu khi Ollama Bật (Full AI Mode) | Mục tiêu khi Ollama Tắt (Fast Lookup Mode) |
|---|---|---|
| Storefront API (`GET /menu/*`, `/stores`) p95 | < 150 ms (Local) / < 300 ms (Cloud) | < 150 ms (Local) / < 300 ms (Cloud) |
| Landing Page LCP (Mobile 4G Lighthouse) | < 2.5 s (Performance ≥ 85, SEO ≥ 90) | < 2.5 s |
| Chat: SQL Fast-path & Answer Cache Hit | < 0.8 s (Local) / < 1.2 s (Cloud) | < 0.8 s (Local) / < 1.2 s (Cloud) |
| Chat: Thời gian hiện Product Cards | < 1.2 s (Local) / < 1.8 s (Cloud) | < 1.2 s (Local) / < 1.8 s (Cloud) |
| Chat: TTFT của LLM (`think=false`) | **≤ 2.5 s (PC có GPU)** / **≤ 9 s (PC CPU)** | Chuyển sang Lexical + SQL fallback ≤ 4 s (lần đầu), < 1 s (các lần sau) |
| RAG Recall@5 (trên 80 câu hỏi chuẩn) | ≥ 0.85 | ≥ 0.65 (Lexical FTS + `pg_trgm`) |
| Exact Price Accuracy | **100%** | **100%** |

---

## 10. Roadmap triển khai 8 tuần (Hoàn thiện Local No-Docker P0–P6 → Setup & Deploy Cloud ở P7)

Roadmap được tổ chức lại để **tập trung 100% nguồn lực hoàn thiện và nghiệm thu sản phẩm trên Local (không dùng Docker) từ Giai đoạn P0 đến P6**, sau khi mọi thứ hoàn toàn ổn định mới thực hiện **Setup Hạ tầng Cloud & Deploy ở Giai đoạn cuối P7**:

```mermaid
flowchart LR
    subgraph LOCAL_DEV["PHA 1: PHÁT TRIỂN & CHẠY ỔN ĐỊNH 100% TRÊN LOCAL — KHÔNG DÙNG DOCKER (Tuần 1 -> Đầu Tuần 8)"]
        P0["P0: Local Native Stack, Ollama\n& Walking Skeleton Local (T1)"] --> P1["P1: DB Schema, Seed Data\n& Storefront API Local (T2)"]
        P1 --> P2["P2: React Landing Page\n6 trang UI/UX Local (T3-4)"]
        P1 --> P3["P3: Knowledge Base\n& Local CLI Ingestion (T4-5)"]
        P3 --> P4["P4: Hybrid Retrieval, RRF\n& SQL Fast-path Local (T5-6)"]
        P2 --> P5["P5: Bean AI Generation, Cache\n& Chat Widget UI Local (T6-7)"]
        P4 --> P5
        P5 --> P6["P6: Kiểm thử toàn diện, RAG Eval 80 câu\n& Chốt ổn định trên Local (Đầu T8)"]
    end

    subgraph CLOUD_DEPLOY["PHA 2: SETUP HẠ TẦNG & DEPLOY (Cuối Tuần 8)"]
        P7["P7: Setup Neon Prod + Cloudflare Tunnel\n+ Deploy Render & Vercel + Go-live"]
    end

    P6 ==>|"Đã ổn định 100% trên Local"| P7
```

### Giai đoạn P0 — Thiết lập Môi trường Local (No-Docker), Ollama Benchmark & Walking Skeleton Local (Tuần 1)
- [ ] Cài đặt Ollama trên PC (`127.0.0.1:11434`), tải `bge-m3`, `qwen3:8b`, `qwen3:4b`.
- [ ] Chạy `deploy/pc/bench_ollama.py` (với `think=false`) để đo tốc độ thực tế trên PC và chốt model.
- [ ] Khởi tạo repo `cafe-digital-platform` theo cấu trúc Multi-App ở Mục 7.
- [ ] Thiết lập PostgreSQL 17 + `pgvector` cho Local mà **không dùng Docker** (cài PostgreSQL 17 Native trên Windows hoặc kết nối database `dev`), bật `vector`, `pg_trgm`, `unaccent`, `pgcrypto`.
- [ ] Dựng khung FastAPI (`services/landing-api`) bằng Python `.venv` native tại `http://localhost:8000` với `/health` và `/ready`.
- [ ] Dựng khung React + Vite + TypeScript + Tailwind + shadcn/ui (`apps/landing-page`) chạy tại `http://localhost:5173`.
- **Nghiệm thu Local P0:** Giao diện `http://localhost:5173` gọi thông suốt tới `http://localhost:8000/ready`, báo kết nối thành công tới cả PostgreSQL lẫn Ollama Local (`127.0.0.1:11434`) mà không cần chạy Docker.

### Giai đoạn P1 — Database Schema, Seed Data & Storefront API trên Local (Tuần 2)
- [ ] Viết SQLAlchemy models & Alembic migrations cho toàn bộ bảng ở Mục 4.2 và chạy `alembic upgrade head`.
- [ ] Biên soạn bộ dữ liệu mẫu chuẩn cho thương hiệu **BREW & BEAN** trong `data/seed/`: 3 cửa hàng, 6 danh mục, 28–32 sản phẩm (có đầy đủ `taste_tags`, `bitterness_level`, `sweetness_level`, `caffeine_level`, `has_milk`, nguyên liệu & mã dị ứng), 3 chương trình khuyến mãi.
- [ ] Viết và chạy `scripts/seed_database.py` (idempotent upsert).
- [ ] Xây dựng toàn bộ Storefront Read API (`/storefront`, `/stores`, `/menu/categories`, `/menu/products`, `/promotions/active`) và viết unit/integration tests trên Local.
- **Nghiệm thu Local P1:** p95 latency các endpoint GET trên Local < 150 ms; bộ lọc `max_price`, `caffeine_level`, `has_milk`, `taste_tag` trả kết quả đúng 100%.

### Giai đoạn P2 — Xây dựng Giao diện React Brand Landing Page trên Local (Tuần 3–4)
- [ ] Thiết kế Design System cho BREW & BEAN (bảng màu Espresso/Cream/Caramel, typography sang trọng).
- [ ] Xây dựng hoàn chỉnh 6 trang trên `localhost:5173`: `HomePage` (có Interactive Taste Finder), `MenuPage` (bộ lọc đa chiều kết nối API local), `ProductDetailPage` (có Flavor Meter, cảnh báo dị ứng, nút *"Hỏi Bean AI"* & nút *"Đặt món"* sẵn sàng cho App 2), `AboutPage`, `PromotionPage`, `VisitPage` (tự tính trạng thái Đang mở/Đã đóng cửa).
- [ ] Tích hợp `warmup.ts`, skeleton loading, tối ưu ảnh `.webp`, SEO metadata.
- **Nghiệm thu Local P2:** Duyệt mượt toàn bộ 6 trang trên `localhost:5173` (Desktop & Mobile responsive); Lighthouse mobile Performance ≥ 85, Accessibility ≥ 90, SEO ≥ 90; website hoạt động bình thường kể cả khi tắt Ollama local.

### Giai đoạn P3 — Biên soạn Knowledge Base & Local CLI Ingestion Pipeline (Tuần 4–5)
- [ ] Biên soạn ≥ 25 tài liệu Markdown chất lượng cao trong `data/knowledge_base/` (hương vị từng dòng đồ uống, kiến thức hạt Arabica/Robusta, Cold Brew vs Espresso, FAQ, chính sách quán, câu chuyện thương hiệu).
- [ ] Xây dựng `rag/text/normalize.py` (chuẩn hóa NFC + không dấu), Markdown/FAQ loaders, semantic chunker (250–400 tokens, giữ nguyên cặp Q–A).
- [ ] Xây dựng và chạy `scripts/ingest_knowledge.py` trên Local: kiểm tra `content_hash`, gọi `http://127.0.0.1:11434/api/embed` (`bge-m3`), lưu chunks & vectors vào PostgreSQL trong 1 transaction.
- **Nghiệm thu Local P3:** Ingest 25+ tài liệu hoàn tất nhanh chóng; chạy lại lần 2 báo `0 changed (skipped)`.

### Giai đoạn P4 — Hybrid Retrieval, RRF & SQL Fast-path trên Local (Tuần 5–6)
- [ ] Xây dựng Query Parser (tách điều kiện giá *"dưới 45k"*, vị *"ít đắng"*, *"không sữa"*, *"ít caffeine"*).
- [ ] Xây dựng Intent Router & **SQL Fast-path** (trả lời ngay bằng template song ngữ cho câu hỏi giá, danh sách món theo giá, giờ mở cửa, khuyến mãi mà không cần gọi LLM).
- [ ] Xây dựng Dense Retriever (`pgvector` HNSW), Lexical Retriever (`FTS` + `pg_trgm`), SQL Product Retriever và bộ hợp nhất **RRF (`k=60`)**.
- [ ] Xây dựng chế độ **Lexical + SQL Fallback** khi Ollama Local tắt (không cần gọi `/api/embed`).
- **Nghiệm thu Local P4:** Recall@5 ≥ 0.85 trên tập test retrieval local; câu hỏi SQL Fast-path phản hồi < 0.8s kể cả khi tắt Ollama.

### Giai đoạn P5 — Bean AI Generation, Answer Cache & Chat Widget UI trên Local (Tuần 6–7)
- [ ] Xây dựng `OllamaClient` hỗ trợ streaming NDJSON, `"think": false`, Circuit Breaker nhận diện lỗi kết nối nhanh (và hỗ trợ sẵn header Cloudflare Access Service Token để dùng khi deploy ở P7).
- [ ] Xây dựng System Prompt & Task Prompts, Conversation Memory (4 lượt gần nhất) và bước **Hậu kiểm giá tiền/dị ứng**.
- [ ] Xây dựng bảng `answer_cache` và chạy `scripts/prewarm_cache.py` trên Local nạp sẵn câu trả lời cho 40+ câu hỏi phổ biến & toàn bộ Suggested Questions trên Landing Page.
- [ ] Xây dựng trọn bộ **Bean AI Chat Widget** trên React (`localhost:5173`): streaming SSE từ `localhost:8000`, hiển thị `ProductRecommendationCard` ngay trước khi stream text, `SourceCitationBadge`, nút 👍/👎 feedback, và kết nối với các nút *"Hỏi Bean AI về món này"* trên toàn trang.
- **Nghiệm thu Local P5:** Trải nghiệm chat mượt mà cả trên Desktop lẫn Mobile tại `localhost:5173`; khi tắt thử Ollama giữa chừng, Chat tự động chuyển sang chế độ *"Tra cứu nhanh"* không gây lỗi giao diện.

### Giai đoạn P6 — Kiểm thử toàn diện, RAG Evaluation (80 câu) & Nghiệm thu ổn định trên Local (Đầu Tuần 8)
- [ ] Xây dựng bộ `rag/evaluation/dataset.jsonl` (80 câu hỏi phủ đủ 6 nhóm) và chạy `run_evaluation.py` trên Local.
- [ ] Chạy và vượt qua 3 bài test bắt buộc ở Mục 9.2 trên Local: **Exact Price Test (100%)**, **Allergen & Grounding Safety Test (≥ 90%)**, **Offline Ollama Resilience Test (100%)**.
- [ ] Kiểm thử bản build production của Frontend (`npm run build && npm run preview`) kết nối với FastAPI local; rà soát và đóng toàn bộ bug UI/UX, memory leak, rate limit và hiệu năng.
- **Nghiệm thu Local P6 (LOCAL STABILITY GATE):** 100% test tự động và 80 câu đánh giá RAG đều xanh trên Local; hệ thống hoạt động ổn định, sẵn sàng đóng gói để đưa lên Cloud.

### Giai đoạn P7 (Cuối cùng) — Thiết lập Hạ tầng Cloud, Cloudflare Tunnel & Deploy Production (Cuối Tuần 8)
*Chỉ bắt đầu sau khi Giai đoạn P6 đã nghiệm thu hoàn tất trên Local:*
- [ ] **Bước 7.1 (Cloud Database — Neon Production):** Chuẩn bị database Neon Postgres Production (Singapore), chạy `scripts/sql/init_neon.sql` để tạo role `landing_app_user` (Read-only trên catalog/knowledge), chạy `alembic upgrade head`, `seed_database.py`, `ingest_knowledge.py`, `prewarm_cache.py` từ PC để đồng bộ toàn bộ dữ liệu đã kiểm chứng lên Neon Production.
- [ ] **Bước 7.2 (Cloudflare Tunnel & Zero Trust):** Thiết lập `cloudflared` Named Tunnel (`ai.<domain>`) trên PC với `httpHostHeader: "127.0.0.1:11434"`; bật Cloudflare Zero Trust Service Token + WAF Custom Rule khóa chặt các path ngoài `/api/chat`, `/api/embed`, `/api/version`, `/api/ps`; hoàn thiện `start-ai-node.ps1`, `stop-ai-node.ps1`, `status-ai-node.ps1`.
- [ ] **Bước 7.3 (Deploy Backend — Render):** Kết nối repo lên Render qua `render.yaml`, điền biến môi trường (`DATABASE_URL` của Neon, `OLLAMA_BASE_URL=https://ai.<domain>`, `CF_ACCESS_CLIENT_ID/SECRET`), kiểm tra `/health` và `/ready` trên Render.
- [ ] **Bước 7.4 (Deploy Frontend — Vercel):** Kết nối `apps/landing-page` lên Vercel với `VITE_API_BASE_URL` trỏ về Render, kiểm tra toàn bộ 6 trang và Bean AI Chat SSE trên domain thật.
- [ ] **Bước 7.5 (CI/CD, Backup & Go-live):** Kích hoạt `.github/workflows/ci-landing.yml`, `db-backup.yml`, `smoke-landing.yml`, `deploy/pc/backup_db.ps1` và nghiệm thu Go-live Production.

---

## 11. Bảo mật, Vận hành, Giám sát & Quản lý rủi ro

### 11.1. Nguyên tắc bảo mật (Áp dụng từ Local tới Production)

- [ ] **Không mở bất kỳ port Inbound nào trên router gia đình**; Ollama trên PC luôn chỉ bind `127.0.0.1:11434` (cả khi dev local lẫn khi chạy tunnel).
- [ ] **Rate Limiting & Chống lạm dụng LLM (Kiểm thử ngay từ Local P5–P6):** Giới hạn 8 tin nhắn/phút/session và 30 tin nhắn/phút/IP; giới hạn độ dài câu hỏi ≤ 1.000 ký tự.
- [ ] **Quyền Database tối thiểu khi Deploy lên Render (P7):** Vì Landing Page không có chức năng Admin CRUD, user Postgres dùng trên Render (`landing_app_user`) chỉ có quyền **`SELECT` (Read-only)** trên các bảng `stores`, `menu_*`, `products`, `product_variants`, `promotions`, `knowledge_*`, `document_chunks`, và chỉ có quyền `SELECT/INSERT/UPDATE` trên bảng `chat_*` và `answer_cache`. Ngay cả khi backend bị khai thác lỗ hổng, kẻ tấn công cũng không thể sửa giá đồ uống hay xóa dữ liệu menu!
- [ ] **Chặn truy cập trái phép tại Cloudflare Edge khi mở Tunnel (P7):** Bắt buộc xác thực bằng `CF-Access-Client-Id` & `CF-Access-Client-Secret` (Cloudflare Access Service Token) kết hợp WAF Rule chỉ cho phép `/api/chat`, `/api/embed`, `/api/version`, `/api/ps` (chặn tuyệt đối `/api/pull`, `/api/delete`, `/api/create`, `/api/push`).

### 11.2. Vận hành hằng ngày trên Máy tính cá nhân (Sau khi Go-live ở P7)

Bộ 3 script PowerShell trong `deploy/pc/` giúp bạn chủ động bật/tắt vai trò AI Server của máy tính cá nhân bất cứ lúc nào:

- **Khi muốn bật AI Barista phục vụ khách / demo:**
  Chạy `.\deploy\pc\start-ai-node.ps1` → Tự động chống Sleep khi cắm sạc, bật Ollama (`127.0.0.1:11434`), nạp ấm `bge-m3` & `qwen3`, kết nối Cloudflare Tunnel.
- **Khi cần kiểm tra trạng thái:**
  Chạy `.\deploy\pc\status-ai-node.ps1` → Kiểm tra tiến trình Ollama, kết nối Tunnel `https://ai.<domain>/api/version` và mức VRAM đang dùng.
- **Khi cần dùng toàn bộ GPU/CPU của PC cho việc cá nhân hoặc tắt máy:**
  Chạy `.\deploy\pc\stop-ai-node.ps1` → Đóng Tunnel, giải phóng toàn bộ VRAM (`keep_alive=0`), khôi phục chế độ Sleep bình thường của Windows. Landing Page trên Vercel/Render tự động chuyển sang chế độ *"Tra cứu nhanh"* (SQL + Answer Cache).

### 11.3. Bảng quản lý rủi ro

| Mã | Rủi ro | Mức độ | Giải pháp trong thiết kế |
|---|---|---|---|
| **R1** | Cấu hình Cloud hoặc chạy Docker Desktop quá sớm làm tốn RAM và chậm tiến độ code | Trung bình | Áp dụng chiến lược **Local-First (No-Docker), Deploy-Last**: Hoàn tất và kiểm thử 100% trên Local Native (P0–P6) rồi mới setup Cloud ở P7 |
| **R2** | Máy tính cá nhân tắt hoặc mất mạng khi khách đang vào Landing Page | Cao | Website + DB nằm trên Vercel/Render/Neon 24/7; Chat tự động trả lời từ SQL Fast-path, Answer Cache (40+ câu hỏi) và Lexical Search trong ≤ 4s |
| **R3** | Render Free ngủ sau 15 phút không có truy cập | Trung bình | `warmup.ts` gọi `/health` ngay khi khách vừa mở trang; prerender nội dung tĩnh trên Vercel |
| **R4** | LLM tự bịa giá tiền hoặc tư vấn sai chất gây dị ứng | Cao | Giá và thành phần dị ứng chỉ lấy từ SQL; Product Cards do backend dựng từ kết quả SQL; hậu kiểm số tiền trước khi hoàn tất câu trả lời |
| **R5** | Mở rộng thêm App 2 (Đặt hàng) & App 3 (Admin) gây xung đột schema | Thấp | Schema đã chuẩn bị sẵn `sku`, `slug`, `version`, `is_active` và tách cấu trúc repo `apps/*` ngay từ đầu |

---

## 12. Hướng dẫn Thiết lập Hạ tầng Cloud & Deploy từng bước (Thực hiện ở giai đoạn cuối)

> **Lưu ý quan trọng:** Toàn bộ Mục 12 này thuộc **Giai đoạn P7 (Cuối Tuần 8)** — chỉ bắt đầu thực hiện sau khi ứng dụng đã chạy hoàn tất, mượt mà và vượt qua mọi bài kiểm thử trên môi trường Local (Mục 8 & Mục 9).

### 12.1. Bước 1: Thiết lập Neon PostgreSQL (Cloud DB) & Đẩy dữ liệu đã kiểm chứng từ Local lên Neon

1. Tạo project mới trên **Neon** (chọn region **AWS Asia Pacific (Singapore) — `ap-southeast-1`**, PostgreSQL 17).
2. Chạy script [`scripts/sql/init_neon.sql`](./cafe-digital-platform/scripts/sql/init_neon.sql) trên Neon SQL Editor để bật `vector`, `pg_trgm`, `unaccent`, `pgcrypto` và tạo user `landing_app_user` (chỉ có quyền `SELECT` trên catalog/knowledge và `SELECT, INSERT, UPDATE` trên `chat_*`, `answer_cache`).
3. Trên PC cá nhân, trỏ tạm `MIGRATION_DATABASE_URL` trong `.env` sang connection string `cafe_owner` của Neon và chạy bộ lệnh đồng bộ dữ liệu:
   ```powershell
   cd services/landing-api
   alembic upgrade head
   cd ../..
   python scripts/seed_database.py
   python scripts/ingest_knowledge.py --path data/knowledge_base
   python scripts/prewarm_cache.py
   ```
   *(Nhờ Ollama chạy ngay trên PC của bạn, quá trình embed và đẩy dữ liệu lên Neon chỉ mất chưa tới 1 phút).*

### 12.2. Bước 2: Thiết lập Cloudflare Tunnel (`cloudflared`) + Zero Trust + WAF trên PC

#### A. Tạo Named Tunnel nối vào Ollama Local (`127.0.0.1:11434`)
```powershell
winget install Cloudflare.cloudflared
cloudflared tunnel login
cloudflared tunnel create brewbean-ai
cloudflared tunnel route dns brewbean-ai ai.<domain>
```

File `C:\Users\Admin\.cloudflared\config.yml`:
```yaml
tunnel: <TUNNEL_UUID>
credentials-file: C:\Users\Admin\.cloudflared\<TUNNEL_UUID>.json

ingress:
  - hostname: ai.<domain>
    service: http://127.0.0.1:11434
    originRequest:
      httpHostHeader: "127.0.0.1:11434"   # Bắt buộc để Ollama không chặn 403
      connectTimeout: 5s
      keepAliveTimeout: 90s
  - service: http_status:404
```

#### B. Khóa bảo mật tại Cloudflare Edge (Zero Trust + WAF)
1. **Cloudflare Zero Trust → Access → Service Auth → Service Tokens:** Tạo token `render-landing-api`, lưu lại `CF-Access-Client-Id` và `CF-Access-Client-Secret`.
2. **Access → Applications:** Tạo Self-hosted App cho `ai.<domain>`, gắn policy **Service Auth** với token vừa tạo.
3. **Security → WAF → Custom rules:** Chặn mọi path ngoài 4 endpoint cần thiết:
   ```text
   (http.host eq "ai.<domain>" and not http.request.uri.path in {"/api/chat" "/api/embed" "/api/version" "/api/ps"}) -> Block
   ```

### 12.3. Bước 3: Thiết lập & Deploy Backend FastAPI lên Render (`render.yaml`)

Đặt `render.yaml` ở thư mục gốc của repo `cafe-digital-platform` với `rootDir: services/landing-api`:

```yaml
services:
  - type: web
    name: brew-bean-landing-api
    runtime: python
    region: singapore
    plan: free
    branch: main
    rootDir: services/landing-api
    autoDeployTrigger: checksPass
    buildCommand: pip install --upgrade pip && pip install -r requirements-api.txt
    startCommand: >-
      alembic upgrade head &&
      uvicorn app.main:app --host 0.0.0.0 --port $PORT
      --proxy-headers --forwarded-allow-ips="*" --workers 1
    healthCheckPath: /health
    envVars:
      - key: PYTHON_VERSION
        value: "3.12.8"
      - key: APP_ENV
        value: production
      - key: DATABASE_URL
        sync: false
      - key: MIGRATION_DATABASE_URL
        sync: false
      - key: CORS_ORIGINS
        value: '["https://brew-bean.vercel.app"]'
      - key: CORS_ORIGIN_REGEX
        value: '^https://brew-bean-[a-z0-9-]+-<team-slug>\.vercel\.app$'
      - key: SESSION_TOKEN_PEPPER
        generateValue: true
      - key: OLLAMA_BASE_URL
        value: https://ai.<domain>
      - key: CF_ACCESS_CLIENT_ID
        sync: false
      - key: CF_ACCESS_CLIENT_SECRET
        sync: false
      - key: LLM_MODEL
        value: qwen3:8b
      - key: EMBEDDING_MODEL
        value: bge-m3
```

### 12.4. Bước 4: Thiết lập & Deploy Frontend React lên Vercel (`apps/landing-page/vercel.json`)

Khi import repo `cafe-digital-platform` vào Vercel ở giai đoạn cuối, đặt **Root Directory = `apps/landing-page`**:

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "framework": "vite",
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }],
  "headers": [
    {
      "source": "/assets/(.*)",
      "headers": [{ "key": "Cache-Control", "value": "public, max-age=31536000, immutable" }]
    },
    {
      "source": "/(.*)",
      "headers": [
        { "key": "X-Content-Type-Options", "value": "nosniff" },
        { "key": "Referrer-Policy", "value": "strict-origin-when-cross-origin" },
        { "key": "X-Frame-Options", "value": "DENY" },
        { "key": "Permissions-Policy", "value": "camera=(), microphone=(), geolocation=()" }
      ]
    }
  ]
}
```

Biến môi trường trên Vercel:
- `VITE_API_BASE_URL`: `https://api.<domain>/api/v1` (hoặc `https://brew-bean-landing-api.onrender.com/api/v1`)
- `VITE_ORDERING_APP_URL`: để trống ở giai đoạn đầu (khi Ứng dụng 2 hoàn thành sẽ điền `https://order.<domain>`)

### 12.5. Bước 5: Kích hoạt CI/CD, Quy trình cập nhật nội dung & Runbook Production

#### A. Luồng CI/CD cho Code (Sau khi đã deploy lần đầu ở P7)
```mermaid
flowchart LR
    PR["Push / PR vào apps/landing-page\nhoặc services/landing-api"] --> GH["GitHub Actions (ci-landing.yml)"]
    GH -->|"PR"| V_PREV["Vercel Preview Deploy"]
    GH -->|"Merge main + CI xanh"| R_PROD["Render Auto-Deploy Backend"]
    GH -->|"Merge main"| V_PROD["Vercel Auto-Deploy Frontend"]
```

#### B. Luồng cập nhật Menu & Tri thức sau khi Go-live
1. Sửa file `data/seed/products.json` hoặc thêm file Markdown vào `data/knowledge_base/`, kiểm tra nhanh trên Local nếu cần.
2. Chạy script đồng bộ từ PC lên Neon:
   ```powershell
   python scripts/seed_database.py
   python scripts/ingest_knowledge.py
   python scripts/prewarm_cache.py
   ```
3. Commit các file JSON/Markdown vào Git để lưu lịch sử.

#### C. Backup Database tự động & Runbook xử lý sự cố Production
- **Backup trên Cloud (24/7):** `.github/workflows/db-backup.yml` chạy `pg_dump` hằng ngày từ Neon.
- **Backup về PC cá nhân:** `deploy/pc/backup_db.ps1` tải bản `.dump` về ổ cứng máy tính.

| Sự cố Production | Nguyên nhân phổ biến | Cách khắc phục |
|---|---|---|
| Render gọi Tunnel báo `403 Forbidden` | (1) Thiếu `httpHostHeader: "127.0.0.1:11434"` trong `.cloudflared\config.yml` khiến Ollama từ chối; hoặc (2) Sai `CF_ACCESS_CLIENT_ID`/`SECRET` | Kiểm tra lại `config.yml` của `cloudflared` và cặp biến môi trường trên Render |
| Render gọi Tunnel báo `530 (Error 1033)` | `cloudflared` trên PC chưa chạy hoặc mất kết nối mạng gia đình | Chạy `.\deploy\pc\start-ai-node.ps1` trên PC (trong lúc đó web vẫn tự động dùng chế độ Tra cứu nhanh) |
| Câu trả lời chat bị cắt giữa chừng sau ~100s | Quá giới hạn idle timeout 100s của Cloudflare do quên tắt thinking mode | Đảm bảo payload `/api/chat` luôn có `"think": false` và `"stream": true` |
| Đổi sang một máy tính cá nhân khác | Nâng cấp PC hoặc dùng laptop đi thuyết trình/demo | Cài Ollama + `cloudflared` trên máy mới, copy file `<TUNNEL_UUID>.json` + `config.yml`, chạy `start-ai-node.ps1` (không cần đổi cấu hình trên Render hay Vercel) |

---

## 13. Checklist Nghiệm thu Local & Go-live Production (Definition of Done)

### 13.1. Cổng nghiệm thu 1 — Hoàn tất & Ổn định 100% trên Local, Không dùng Docker (Cuối Giai đoạn P6, trước khi Setup Deploy)
- [ ] **Local Native Infrastructure (No Docker):** PostgreSQL 17 (`pgvector`, `pg_trgm`, `unaccent`, `pgcrypto`) và Ollama (`127.0.0.1:11434` với `qwen3` + `bge-m3`) hoạt động ổn định mà không cần chạy Docker Desktop.
- [ ] **Data & RAG Ingestion Local:** Đã chạy thành công `alembic upgrade head`, `seed_database.py` (3 cửa hàng, 6 danh mục, 28–32 sản phẩm, 3 khuyến mãi), `ingest_knowledge.py` (≥ 25 tài liệu Markdown) và `prewarm_cache.py` (40+ câu hỏi phổ biến).
- [ ] **Frontend 6 trang trên Local (`localhost:5173`):** Hoàn thiện Home (có Interactive Taste Finder), Menu (bộ lọc đa chiều), Product Detail (Flavor Meter & cảnh báo dị ứng), About, Promotions, Visit; `npm run lint` và `npm run build` thành công 100%.
- [ ] **Bean AI Chat & RAG Evaluation trên Local (`localhost:8000`):** Toàn bộ `pytest` xanh; vượt qua bộ đánh giá 80 câu hỏi RAG (Recall@5 ≥ 0.85) và 3 bài test bắt buộc (Exact Price 100%, Allergen/Grounding Safety, Offline Ollama Fallback khi tắt Ollama local).

### 13.2. Cổng nghiệm thu 2 — Thiết lập Hạ tầng Cloud & Go-live Production (Cuối Giai đoạn P7)
- [ ] **Neon PostgreSQL (Singapore):** Đã phân quyền `landing_app_user` Read-only trên toàn bộ bảng danh mục/tri thức và đồng bộ đầy đủ dữ liệu từ Local lên Neon.
- [ ] **Cloudflare Tunnel & Zero Trust:** Ollama trên PC chỉ lắng nghe tại `127.0.0.1:11434`; Cloudflare Tunnel cấu hình `httpHostHeader: "127.0.0.1:11434"`; Service Token + WAF Path Allowlist chặn đúng các endpoint quản trị.
- [ ] **Render & Vercel Production:** Backend trên Render (< 250 MB RAM) và Frontend trên Vercel kết nối thông suốt qua HTTPS/SSE; vượt qua bài test tắt PC thực tế (`stop-ai-node.ps1`) mà Website và Chat Fast-Lookup vẫn hoạt động 100%.

---

## 14. Phụ lục: File cấu hình (Local vs Production) & Lệnh vận hành

### 14.1. `services/landing-api/.env.example` (Mặc định sẵn sàng cho Local Dev P0–P6 — Không dùng Docker)

```dotenv
APP_ENV=development
LOG_LEVEL=DEBUG

# --- GIAI ĐOẠN P0-P6 (POSTGRESQL NATIVE TRÊN WINDOWS HOẶC NEON DEV DB - KHÔNG DÙNG DOCKER) ---
DATABASE_URL=postgresql+asyncpg://cafe_owner:password@localhost:5432/cafe_db
MIGRATION_DATABASE_URL=postgresql+asyncpg://cafe_owner:password@localhost:5432/cafe_db
# --- GIAI ĐOẠN P7 (NEON CLOUD PRODUCTION): Chỉ thay trên Render khi Deploy ---
# DATABASE_URL=postgresql+asyncpg://landing_app_user:<password>@<neon-host>/cafe_db?ssl=require
# MIGRATION_DATABASE_URL=postgresql+asyncpg://cafe_owner:<password>@<neon-host>/cafe_db?ssl=require

CORS_ORIGINS=["http://localhost:5173"]
CORS_ORIGIN_REGEX=

SESSION_TOKEN_PEPPER=change-this-secret-pepper

# --- GIAI ĐOẠN P0-P6 (OLLAMA LOCAL TRỰC TIẾP, KHÔNG CẦN TUNNEL) ---
OLLAMA_BASE_URL=http://127.0.0.1:11434
CF_ACCESS_CLIENT_ID=
CF_ACCESS_CLIENT_SECRET=
# --- GIAI ĐOẠN P7 (PRODUCTION QUA CLOUDFLARE TUNNEL): Chỉ điền trên Render ---
# OLLAMA_BASE_URL=https://ai.<domain>

LLM_MODEL=qwen3:8b
EMBEDDING_MODEL=bge-m3
EMBEDDING_DIMENSION=1024
OLLAMA_CONNECT_TIMEOUT_S=4
OLLAMA_READ_TIMEOUT_S=75
LLM_MAX_CONCURRENCY=1
LLM_QUEUE_TIMEOUT_S=20
LLM_NUM_CTX=4096
LLM_NUM_PREDICT=350
LLM_TEMPERATURE=0.3

RAG_TOP_K_DENSE=20
RAG_TOP_K_LEXICAL=20
RAG_RRF_K=60
RAG_FINAL_TOP_K=4
RAG_HISTORY_TURNS=4
RAG_MIN_RELEVANCE=0.35

SESSION_TTL_HOURS=24
CHAT_MAX_MESSAGE_LENGTH=1000
CHAT_RATE_LIMIT_PER_MIN=8
```

### 14.2. `apps/landing-page/.env.example`

```dotenv
# Giai đoạn P0-P6 (Local Dev): trỏ tới FastAPI Local
VITE_API_BASE_URL=http://localhost:8000/api/v1
# Giai đoạn P7 (Vercel Deploy): đổi thành https://brew-bean-landing-api.onrender.com/api/v1

# Điền URL của Ứng dụng 2 (Website đặt hàng trực tuyến) khi triển khai xong
VITE_ORDERING_APP_URL=
```

### 14.3. Tóm tắt lệnh làm việc theo 2 pha (Local Native No-Docker → Production Deploy)

```powershell
# =====================================================================
# PHA 1 (GIAI ĐOẠN P0 -> P6): PHÁT TRIỂN & KIỂM THỬ 100% TRÊN LOCAL (KHÔNG DÙNG DOCKER)
# =====================================================================

# 1. Đảm bảo PostgreSQL Native (localhost:5432) & Ollama Local (127.0.0.1:11434) đang chạy
# (Không cần bật Docker Desktop!)

# 2. Chạy migration & nạp dữ liệu Menu / Khuyến mãi / Chi nhánh vào PostgreSQL
cd services/landing-api
.\.venv\Scripts\Activate.ps1
alembic upgrade head
cd ../..
python scripts/seed_database.py

# 3. Embed tài liệu Knowledge Base qua Ollama Local & nạp sẵn Answer Cache
python scripts/ingest_knowledge.py --path data/knowledge_base
python scripts/prewarm_cache.py

# 4. Chạy Backend (port 8000) & Frontend (port 5173) trực tiếp trên Local
cd services/landing-api && uvicorn app.main:app --reload --port 8000
cd apps/landing-page && npm run dev

# 5. Kiểm thử & chạy bộ đánh giá chất lượng RAG 80 câu trên Local (Quality Gate P6)
cd services/landing-api && pytest -v
python -m services.landing_api.rag.evaluation.run_evaluation

# =====================================================================
# PHA 2 (GIAI ĐOẠN CUỐI P7): CHỈ CHẠY SAU KHI LOCAL ĐÃ HOÀN TOÀN ỔN ĐỊNH
# =====================================================================

# 6. Khởi động Ollama + Cloudflare Tunnel trên PC để nối ra Cloud
.\deploy\pc\start-ai-node.ps1

# 7. Đồng bộ Schema, Seed Data, Vectors & Answer Cache từ Local lên Neon Cloud
# (Sau khi cập nhật MIGRATION_DATABASE_URL trỏ tới Neon Production)
cd services/landing-api && alembic upgrade head && cd ../..
python scripts/seed_database.py
python scripts/ingest_knowledge.py --path data/knowledge_base
python scripts/prewarm_cache.py

# 8. Dừng AI Node & giải phóng VRAM khi không sử dụng
.\deploy\pc\stop-ai-node.ps1
```
