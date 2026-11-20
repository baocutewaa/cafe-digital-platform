#!/usr/bin/env python3
"""
BREW & BEAN — Knowledge Base Local CLI Ingestion (Giai đoạn P3)
Đọc tài liệu Markdown/FAQ, kiểm tra SHA-256 content_hash, chunk 250-400 tokens,
gọi Ollama Local (/api/embed với bge-m3) và lưu vào PostgreSQL trong 1 transaction.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LANDING_API_DIR = REPO_ROOT / "services" / "landing-api"
if str(LANDING_API_DIR) not in sys.path:
    sys.path.insert(0, str(LANDING_API_DIR))

from app.core.config import settings
from rag.ingestion.indexer import ingest_knowledge_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ingest BREW & BEAN Knowledge Base Markdown files into PostgreSQL + pgvector."
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=REPO_ROOT / "data" / "knowledge_base",
        help="Path to knowledge base directory or single markdown file.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-embed and re-index all files even if content_hash is unchanged.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and chunk documents without calling Ollama or modifying database.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=16,
        help="Number of chunks per Ollama /api/embed request.",
    )
    args = parser.parse_args()

    target_path = args.path if args.path.is_absolute() else (REPO_ROOT / args.path)
    report = asyncio.run(
        ingest_knowledge_path(
            path=target_path,
            database_url=settings.MIGRATION_DATABASE_URL,
            force=args.force,
            dry_run=args.dry_run,
            batch_size=args.batch_size,
        )
    )

    mode = "DRY-RUN" if report.dry_run else "LOCAL INGESTION"
    print(f"[BREW & BEAN] Knowledge Base {mode} hoàn tất trong {report.duration_seconds}s:")
    print(f"  - Tổng số tài liệu : {report.total_files}")
    if report.changed_files == 0 and not report.dry_run:
        print(f"  - Trạng thái       : 0 changed (skipped {report.skipped_files})")
    else:
        print(f"  - Tài liệu cập nhật: {report.changed_files} changed, {report.skipped_files} skipped")
    print(f"  - Chunks đã ghi    : {report.total_chunks_written}")
    if report.invalidated_cache_rows > 0:
        print(f"  - Cache vô hiệu hóa: {report.invalidated_cache_rows} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
