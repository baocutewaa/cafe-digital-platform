from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import BASE_DIR, settings
from app.db.session import AsyncSessionLocal
from app.repositories.chat_repo import ChatRepository

logger = logging.getLogger(__name__)


class AnswerCacheSeedItem(BaseModel):
    """Schema cho một bản ghi câu trả lời tĩnh trong data/seed/answer_cache.json."""

    normalized_query: str = Field(min_length=1)
    language: Literal["vi", "en"] = "vi"
    intent: str = Field(min_length=1, max_length=50)
    answer: str = Field(min_length=1)
    product_slugs: list[str] = Field(default_factory=list)
    citations: list[dict[str, Any]] = Field(default_factory=list)


def resolve_answer_cache_seed_path(explicit_path: str | Path | None = None) -> Path | None:
    """Tìm file seed answer_cache.json từ cấu hình hoặc vị trí mặc định trong repo."""
    candidates: list[Path] = []
    if explicit_path:
        candidates.append(Path(explicit_path))
    elif settings.ANSWER_CACHE_SEED_PATH.strip():
        candidates.append(Path(settings.ANSWER_CACHE_SEED_PATH.strip()))
    else:
        candidates.extend(
            [
                BASE_DIR.parents[1] / "data" / "seed" / "answer_cache.json",
                BASE_DIR / "data" / "seed" / "answer_cache.json",
            ]
        )

    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def load_answer_cache_seed(seed_path: Path) -> list[AnswerCacheSeedItem]:
    """Đọc và validate danh sách câu trả lời tĩnh từ JSON."""
    raw_text = seed_path.read_text(encoding="utf-8").strip()
    if not raw_text:
        return []
    payload = json.loads(raw_text)
    if not isinstance(payload, list):
        raise ValueError(f"File seed answer_cache phải là JSON array: {seed_path}")
    return [AnswerCacheSeedItem.model_validate(item) for item in payload]


async def seed_answer_cache_from_file(
    session: AsyncSession,
    *,
    seed_path: str | Path | None = None,
    force: bool = False,
    ttl_days: int | None = None,
) -> dict[str, int]:
    """
    Nạp các câu trả lời tĩnh vào bảng answer_cache mà không cần gọi Ollama.
    Mặc định chỉ chèn các khóa chưa có hoặc đã hết hạn để giữ nguyên hit_count hiện có.
    """
    resolved = resolve_answer_cache_seed_path(seed_path)
    if resolved is None:
        return {"total": 0, "seeded": 0, "skipped": 0}

    items = load_answer_cache_seed(resolved)
    if not items:
        return {"total": 0, "seeded": 0, "skipped": 0}

    repo = ChatRepository(session)
    kb_version = await repo.get_current_knowledge_version()
    existing_keys = (
        set() if force else await repo.get_active_answer_cache_keys(kb_version)
    )

    seeded = 0
    skipped = 0
    for item in items:
        key = (item.normalized_query, item.language, item.intent)
        if not force and key in existing_keys:
            skipped += 1
            continue
        await repo.upsert_answer_cache(
            normalized_query=item.normalized_query,
            language=item.language,
            intent=item.intent,
            answer=item.answer,
            product_slugs=item.product_slugs,
            citations=item.citations,
            knowledge_version=kb_version,
            ttl_days=ttl_days,
        )
        existing_keys.add(key)
        seeded += 1

    await session.commit()
    return {"total": len(items), "seeded": seeded, "skipped": skipped}


async def export_answer_cache_to_file(
    session: AsyncSession,
    output_path: Path,
) -> int:
    """Xuất các bản ghi answer_cache còn hiệu lực từ DB ra file seed JSON."""
    repo = ChatRepository(session)
    kb_version = await repo.get_current_knowledge_version()
    rows = await repo.list_active_answer_cache(kb_version)
    payload = [
        AnswerCacheSeedItem(
            normalized_query=row.normalized_query,
            language="en" if row.language == "en" else "vi",
            intent=row.intent,
            answer=row.answer,
            product_slugs=list(row.product_slugs or []),
            citations=list(row.citations or []),
        ).model_dump(mode="json")
        for row in rows
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return len(payload)


async def startup_seed_answer_cache() -> dict[str, int] | None:
    """Hook khởi động trong FastAPI lifespan; lỗi DB/file chỉ log cảnh báo, không chặn boot."""
    if not settings.AUTO_SEED_ANSWER_CACHE:
        return None
    try:
        async with AsyncSessionLocal() as session:
            stats = await seed_answer_cache_from_file(session)
        if stats["total"] > 0:
            logger.info(
                "Answer cache seed: total=%d, seeded=%d, skipped=%d",
                stats["total"],
                stats["seeded"],
                stats["skipped"],
            )
        return stats
    except Exception as exc:
        logger.warning("Bỏ qua auto-seed answer_cache khi khởi động: %s", exc)
        return None
