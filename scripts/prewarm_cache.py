#!/usr/bin/env python3
"""
BREW & BEAN — Answer Cache Pre-warming CLI (Giai đoạn P5)
Sinh trước và lưu câu trả lời chuẩn vào bảng answer_cache cho 40+ câu hỏi
phổ biến & toàn bộ Suggested Questions trên Landing Page (dùng LLM_MODEL từ .env).
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LANDING_API_DIR = REPO_ROOT / "services" / "landing-api"
if str(LANDING_API_DIR) not in sys.path:
    sys.path.insert(0, str(LANDING_API_DIR))

from app.core.config import settings
from app.repositories.chat_repo import ChatRepository
from app.services.cache_seed_service import (
    export_answer_cache_to_file,
    seed_answer_cache_from_file,
)
from rag.generation.answer_generator import AnswerGenerator
from rag.generation.guards import is_corrupted_cached_answer
from rag.retrieval.context_builder import HybridRetriever
from rag.retrieval.query_parser import parse_query
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

DEFAULT_SEED_PATH = REPO_ROOT / "data" / "seed" / "answer_cache.json"

# 44 câu hỏi thường gặp + toàn bộ Suggested Questions trên Landing Page
PREWARM_QUESTIONS: list[str] = [
    # 1. Suggested Questions trên Home / Menu / About / Promotions / Visit
    "Gợi ý giúp mình vài món Signature dễ uống tại BREW & BEAN.",
    "Mình không quen uống đắng, thích vị béo nhẹ thì nên chọn món nào?",
    "Mình muốn đồ uống ít đắng, béo nhẹ, dưới 50k uống buổi chiều",
    "Đồ uống nào dưới 45k, ít đắng và dễ uống nhất?",
    "Gợi ý giúp mình đồ uống không chứa sữa bò dưới 50k.",
    "Buổi tối muộn nên uống món gì để không bị mất ngủ?",
    "Cold Brew khác gì với Espresso pha đá thông thường vậy bạn?",
    "Giải thích giúp mình sự khác biệt giữa Arabica Cầu Đất và Robusta Buôn Ma Thuột.",
    "Mình đang xem Menu, hãy gợi ý món hợp khẩu vị giúp mình!",
    # 2. Tư vấn khẩu vị & thời điểm uống
    "Sáng sớm cần tỉnh táo mạnh thì nên uống món cà phê nào?",
    "Buổi chiều làm việc muốn uống món ít caffeine cho dễ ngủ tối?",
    "Trời nóng buổi trưa có món Cold Brew trái cây nào thanh mát không?",
    "Mình thích vị ngọt dịu, không thích vị chua gắt thì chọn món gì?",
    "Mình muốn tìm đồ uống ít calo nhất để giữ dáng.",
    "Quán có đồ uống nào có hương hoa hoặc trái cây nhẹ nhàng không?",
    "Cà phê muối Cầu Đất có vị như thế nào, có quá mặn hoặc quá đắng không?",
    "Cold Brew Cam Sả có ngọt lắm không và có chứa sữa không?",
    "Bạc Xỉu Cốt Dừa Nướng có nhiều caffeine không?",
    "Latte Sữa Yến Mạch Mật Ong hợp với ai?",
    "Matcha Latte Uji và Matcha Sữa Hạnh Nhân khác nhau điểm nào?",
    # 3. Dị ứng & Thành phần an toàn
    "Mình bị dị ứng sữa bò (DAIRY) thì uống món nào được?",
    "Mình bị dị ứng các loại hạt (NUTS) thì nên tránh và nên chọn món nào?",
    "Khách dị ứng đậu nành (SOY) cần lưu ý món nào trên menu?",
    "Quán có bánh ngọt nào không chứa Gluten hoặc không chứa sữa bò không?",
    "Người ăn thuần chay (vegan) uống được những món nào ở BREW & BEAN?",
    "Cacao Sữa Dừa Đá có chứa sữa bò hay các loại hạt cứng không?",
    "Sữa Đậu Nành Mè Đen có phù hợp cho người dị ứng sữa bò và dị ứng hạt không?",
    "Croissant Bơ Pháp và Basque Burnt Cheesecake có chứa sữa bò không?",
    # 4. Kiến thức pha chế & Tùy chỉnh đồ uống
    "Vì sao BREW & BEAN chọn rang vừa Medium Roast thay vì rang đậm?",
    "Uống Cold Brew ủ lạnh 18 giờ có bị cồn cào dạ dày không?",
    "Phương pháp Hand-Poured V60 có ở chi nhánh nào và hương vị ra sao?",
    "Quán có hỗ trợ giảm đường 70%, 50% hoặc pha không đường không?",
    "Tôi có thể đổi sữa tươi sang sữa yến mạch hoặc sữa hạnh nhân cho Latte được không?",
    "Bánh Croissant Bơ Pháp và Croissant Hạnh Nhân nên uống kèm cà phê nào?",
    "Tiramisu Espresso có chứa caffeine và sữa bò không?",
    # 5. Chính sách quán & Thương hiệu
    "Quán có chính sách pha lại miễn phí nếu đồ uống chưa hợp khẩu vị không?",
    "Quy định về nguy cơ nhiễm chéo dị ứng thực phẩm tại quầy bar ra sao?",
    "Quy định không gian yên tĩnh, Wi-Fi và mang thú cưng tại quán như thế nào?",
    "Khách mang bình cá nhân hoặc xin bã cà phê về trồng cây có được không?",
    "Câu chuyện thương hiệu và 3 giá trị cốt lõi của BREW & BEAN là gì?",
    "BREW & BEAN thu mua hạt cà phê từ vùng trồng nào?",
    # 6. Câu hỏi tiếng Anh phổ biến
    "What coffee do you recommend if I prefer less bitter and creamy taste?",
    "What dairy-free drinks do you have at BREW & BEAN?",
    "How is your 18h Cold Brew different from iced Espresso?",
]


async def prewarm(
    limit: int | None = None,
    force: bool = False,
    dry_run: bool = False,
    delay: float = 0.0,
) -> dict[str, int]:
    questions = PREWARM_QUESTIONS[:limit] if limit else PREWARM_QUESTIONS
    if dry_run:
        return {"total": len(questions), "generated": 0, "skipped": len(questions), "failed": 0}

    engine = create_async_engine(settings.MIGRATION_DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    generator = AnswerGenerator()

    generated = 0
    skipped = 0
    failed = 0

    try:
        async with session_factory() as session:
            repo = ChatRepository(session)
            purged = await repo.purge_corrupted_answer_cache()
            await session.commit()
            if purged:
                print(f"[BREW & BEAN] Đã dọn {purged} bản ghi answer_cache lỗi/dính thinking.")
            kb_version = await repo.get_current_knowledge_version()

        for idx, query in enumerate(questions, start=1):
            t0 = time.perf_counter()
            parsed = parse_query(query)
            async with session_factory() as session:
                repo = ChatRepository(session)
                if not force:
                    existing = await repo.lookup_answer_cache(
                        normalized_query=parsed.normalized_query,
                        language=parsed.language,
                        knowledge_version=kb_version,
                        min_similarity=0.98,
                    )
                    if existing is not None:
                        skipped += 1
                        print(f"[{idx}/{len(questions)}] SKIP (cached): {query[:60]}")
                        continue

                retriever = HybridRetriever(session)
                retrieval = await retriever.retrieve(query)
                unsafe_names = await repo.get_unsafe_product_names(
                    retrieval.parsed_query.excluded_allergens
                )

            metrics = await generator.generate_complete(
                retrieval, history=None, unsafe_product_names=unsafe_names
            )
            if metrics.degraded or is_corrupted_cached_answer(
                metrics.answer, retrieval.parsed_query.language
            ):
                failed += 1
                print(f"[{idx}/{len(questions)}] FAIL/DEGRADED ({metrics.model}): {query[:60]}")
                continue

            citations_payload = [
                {
                    "source_key": c.source_key,
                    "title": c.title,
                    "category": c.category,
                    "section": c.section,
                    "snippet": c.snippet,
                }
                for c in retrieval.citations
            ]
            async with session_factory() as session, session.begin():
                repo = ChatRepository(session)
                await repo.upsert_answer_cache(
                    normalized_query=retrieval.parsed_query.normalized_query,
                    language=retrieval.parsed_query.language,
                    intent=retrieval.intent.value,
                    answer=metrics.answer,
                    product_slugs=[p.slug for p in retrieval.products],
                    citations=citations_payload,
                    knowledge_version=kb_version,
                )
            generated += 1
            elapsed = time.perf_counter() - t0
            print(f"[{idx}/{len(questions)}] CACHED ({elapsed:.1f}s): {query[:60]}")
            if delay > 0 and idx < len(questions):
                await asyncio.sleep(delay)

        return {
            "total": len(questions),
            "generated": generated,
            "skipped": skipped,
            "failed": failed,
        }
    finally:
        await engine.dispose()


async def run_seed_export(seed_path: Path) -> int:
    engine = create_async_engine(settings.MIGRATION_DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            count = await export_answer_cache_to_file(session, seed_path)
        print(f"[BREW & BEAN] Đã xuất {count} bản ghi answer_cache -> {seed_path}")
        return 0
    finally:
        await engine.dispose()


async def run_seed_import(seed_path: Path, force: bool = False) -> int:
    engine = create_async_engine(settings.MIGRATION_DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            stats = await seed_answer_cache_from_file(
                session, seed_path=seed_path, force=force
            )
        print(
            f"[BREW & BEAN] Đã nạp answer_cache từ {seed_path}: "
            f"total={stats['total']}, seeded={stats['seeded']}, skipped={stats['skipped']}"
        )
        return 0
    finally:
        await engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description="Pre-warm BREW & BEAN answer_cache.")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of questions.")
    parser.add_argument("--force", action="store_true", help="Regenerate existing cached entries.")
    parser.add_argument("--dry-run", action="store_true", help="Count questions without calling LLM.")
    parser.add_argument(
        "--delay",
        type=float,
        default=0.0,
        help="Cooldown seconds between LLM calls to reduce laptop thermal load.",
    )
    parser.add_argument(
        "--export-seed",
        action="store_true",
        help="Export active answer_cache rows from PostgreSQL to seed JSON.",
    )
    parser.add_argument(
        "--import-seed",
        action="store_true",
        help="Import answer_cache entries from seed JSON into PostgreSQL.",
    )
    parser.add_argument(
        "--seed-path",
        type=Path,
        default=DEFAULT_SEED_PATH,
        help="Path to answer_cache seed JSON file.",
    )
    args = parser.parse_args()

    if args.export_seed:
        return asyncio.run(run_seed_export(args.seed_path))
    if args.import_seed:
        return asyncio.run(run_seed_import(args.seed_path, force=args.force))

    t0 = time.perf_counter()
    res = asyncio.run(
        prewarm(limit=args.limit, force=args.force, dry_run=args.dry_run, delay=args.delay)
    )
    print(
        f"\n[BREW & BEAN] Pre-warm answer_cache hoàn tất trong {time.perf_counter() - t0:.1f}s: "
        f"total={res['total']}, generated={res['generated']}, "
        f"skipped={res['skipped']}, failed={res['failed']}"
    )
    return 0 if res["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
