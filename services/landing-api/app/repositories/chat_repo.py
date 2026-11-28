from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import Float, and_, cast, delete, desc, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.conversation import AnswerCache, ChatFeedback, ChatMessage, ChatSession
from app.models.knowledge import KnowledgeSource
from app.models.menu import Ingredient, MenuCategory, Product, ProductIngredient
from app.schemas.menu import ProductSummaryOut
from app.services.menu_service import build_product_summary
from rag.generation.guards import is_corrupted_cached_answer
from rag.text.normalize import strip_vietnamese_accents

_CACHE_FILLER_TOKENS = {
    "a",
    "ad",
    "at",
    "ban",
    "bean",
    "brew",
    "cam",
    "cho",
    "cua",
    "giup",
    "hay",
    "hoi",
    "minh",
    "nha",
    "nhe",
    "o",
    "oi",
    "on",
    "please",
    "quan",
    "shop",
    "tai",
    "the",
    "va",
    "vay",
    "voi",
    "xin",
}
_SIZE_SENSITIVE_TOKENS = {"s", "m", "l", "nho", "vua", "lon", "small", "regular", "large"}


def _is_safe_fuzzy_cache_hit(query_norm: str, candidate_norm: str) -> bool:
    """
    Prevent pg_trgm fuzzy cache collisions when two queries share a long template
    (e.g. 'Mình đang xem <Product A>...' vs 'Mình đang xem <Product B>...') or
    differ in numbers/sizes (e.g. 45k vs 50k, Size M vs Size L).
    """
    q_ascii = strip_vietnamese_accents(query_norm.lower())
    c_ascii = strip_vietnamese_accents(candidate_norm.lower())

    q_nums = set(re.findall(r"\d+", q_ascii))
    c_nums = set(re.findall(r"\d+", c_ascii))
    if q_nums != c_nums:
        return False

    q_raw_tokens = set(re.findall(r"[a-z0-9]+", q_ascii))
    c_raw_tokens = set(re.findall(r"[a-z0-9]+", c_ascii))
    if (q_raw_tokens & _SIZE_SENSITIVE_TOKENS) != (c_raw_tokens & _SIZE_SENSITIVE_TOKENS):
        return False

    q_tokens = {t for t in q_raw_tokens if len(t) >= 2 and t not in _CACHE_FILLER_TOKENS}
    c_tokens = {t for t in c_raw_tokens if len(t) >= 2 and t not in _CACHE_FILLER_TOKENS}
    if not q_tokens or not c_tokens:
        return q_ascii == c_ascii

    # Reject if user mentioned substantive tokens absent from cached query (e.g. another drink name)
    if len(q_tokens - c_tokens) > 1 or len(c_tokens - q_tokens) > 2:
        return False

    jaccard = len(q_tokens & c_tokens) / len(q_tokens | c_tokens)
    return jaccard >= 0.8


class ChatRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_session(
        self,
        session_token_hash: str,
        language: str,
        store_id: uuid.UUID | None,
        expires_at: datetime,
    ) -> ChatSession:
        chat_session = ChatSession(
            session_token_hash=session_token_hash,
            language=language,
            store_id=store_id,
            preferences={},
            expires_at=expires_at,
        )
        self.session.add(chat_session)
        await self.session.flush()
        return chat_session

    async def get_active_session(self, session_id: uuid.UUID) -> ChatSession | None:
        now = datetime.now(UTC)
        stmt = select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.expires_at > now,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def update_session_preferences(
        self, session_id: uuid.UUID, preferences: dict[str, Any]
    ) -> None:
        await self.session.execute(
            update(ChatSession)
            .where(ChatSession.id == session_id)
            .values(preferences=preferences)
        )

    async def find_user_message_by_client_id(
        self, session_id: uuid.UUID, client_message_id: str
    ) -> ChatMessage | None:
        stmt = select(ChatMessage).where(
            ChatMessage.session_id == session_id,
            ChatMessage.client_message_id == client_message_id,
            ChatMessage.role == "user",
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def find_next_assistant_reply(
        self, session_id: uuid.UUID, after_created_at: datetime
    ) -> ChatMessage | None:
        stmt = (
            select(ChatMessage)
            .where(
                ChatMessage.session_id == session_id,
                ChatMessage.role == "assistant",
                ChatMessage.status == "completed",
                ChatMessage.created_at >= after_created_at,
            )
            .order_by(ChatMessage.created_at.asc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def create_message(
        self,
        *,
        session_id: uuid.UUID,
        role: str,
        content: str,
        client_message_id: str | None = None,
        status: str = "completed",
        intent: str | None = None,
        model: str | None = None,
        ttft_ms: int | None = None,
        latency_ms: int | None = None,
        cached: bool = False,
        degraded: bool = False,
        retrieved_chunk_ids: list[str] | None = None,
        recommended_product_slugs: list[str] | None = None,
        citations: list[dict[str, Any]] | None = None,
    ) -> ChatMessage:
        msg = ChatMessage(
            session_id=session_id,
            client_message_id=client_message_id,
            role=role,
            status=status,
            content=content,
            intent=intent,
            model=model,
            ttft_ms=ttft_ms,
            latency_ms=latency_ms,
            cached=cached,
            degraded=degraded,
            retrieved_chunk_ids=retrieved_chunk_ids or [],
            recommended_product_slugs=recommended_product_slugs or [],
            citations=citations or [],
        )
        self.session.add(msg)
        await self.session.flush()
        return msg

    async def get_recent_history(
        self, session_id: uuid.UUID, max_turns: int | None = None
    ) -> list[dict[str, str]]:
        turns = max_turns or settings.RAG_HISTORY_TURNS
        stmt = (
            select(ChatMessage)
            .where(
                ChatMessage.session_id == session_id,
                ChatMessage.status == "completed",
                ChatMessage.role.in_(("user", "assistant")),
            )
            .order_by(ChatMessage.created_at.desc())
            .limit(turns * 2)
        )
        rows = list((await self.session.execute(stmt)).scalars().all())
        rows.reverse()
        return [
            {"role": row.role, "content": row.content}
            for row in rows
            if row.role == "user" or not is_corrupted_cached_answer(row.content, "vi")
        ]

    async def get_message_with_session(
        self, message_id: uuid.UUID
    ) -> tuple[ChatMessage, ChatSession] | None:
        stmt = (
            select(ChatMessage, ChatSession)
            .join(ChatSession, ChatMessage.session_id == ChatSession.id)
            .where(ChatMessage.id == message_id)
        )
        row = (await self.session.execute(stmt)).first()
        if row is None:
            return None
        return row[0], row[1]

    async def upsert_feedback(
        self, message_id: uuid.UUID, rating: int, comment: str | None
    ) -> ChatFeedback:
        stmt = (
            insert(ChatFeedback)
            .values(message_id=message_id, rating=rating, comment=comment)
            .on_conflict_do_update(
                index_elements=[ChatFeedback.message_id],
                set_={"rating": rating, "comment": comment},
            )
            .returning(ChatFeedback)
        )
        return (await self.session.execute(stmt)).scalar_one()

    async def get_current_knowledge_version(self) -> int:
        stmt = select(func.coalesce(func.max(KnowledgeSource.current_version), 1)).where(
            KnowledgeSource.status == "active"
        )
        return int((await self.session.execute(stmt)).scalar_one())

    async def lookup_answer_cache(
        self,
        normalized_query: str,
        language: str,
        knowledge_version: int,
        min_similarity: float = 0.78,
    ) -> AnswerCache | None:
        now = datetime.now(UTC)
        exact_rows = list(
            (
                await self.session.execute(
                    select(AnswerCache)
                    .where(
                        AnswerCache.normalized_query == normalized_query,
                        AnswerCache.language == language,
                        AnswerCache.knowledge_version == knowledge_version,
                        AnswerCache.expires_at > now,
                    )
                    .limit(4)
                )
            )
            .scalars()
            .all()
        )

        poisoned_ids: list[uuid.UUID] = []
        hit: AnswerCache | None = None
        for row in exact_rows:
            if is_corrupted_cached_answer(row.answer, row.language):
                poisoned_ids.append(row.id)
            elif hit is None:
                hit = row

        if hit is None:
            sim_expr = cast(
                func.similarity(AnswerCache.normalized_query, normalized_query), Float
            )
            trgm_stmt = (
                select(AnswerCache)
                .where(
                    AnswerCache.language == language,
                    AnswerCache.knowledge_version == knowledge_version,
                    AnswerCache.expires_at > now,
                    sim_expr >= min_similarity,
                )
                .order_by(desc(sim_expr))
                .limit(4)
            )
            candidates = list((await self.session.execute(trgm_stmt)).scalars().all())
            for cand in candidates:
                if is_corrupted_cached_answer(cand.answer, cand.language):
                    poisoned_ids.append(cand.id)
                    continue
                if hit is None and _is_safe_fuzzy_cache_hit(
                    normalized_query, cand.normalized_query
                ):
                    hit = cand

        if poisoned_ids:
            await self.session.execute(
                delete(AnswerCache).where(AnswerCache.id.in_(poisoned_ids))
            )

        if hit is not None:
            await self.session.execute(
                update(AnswerCache)
                .where(AnswerCache.id == hit.id)
                .values(hit_count=AnswerCache.hit_count + 1)
            )
        return hit

    async def purge_corrupted_answer_cache(self) -> int:
        """Scan `answer_cache` and delete any rows containing leaked thinking or truncation."""
        rows = list((await self.session.execute(select(AnswerCache))).scalars().all())
        bad_ids = [
            row.id
            for row in rows
            if is_corrupted_cached_answer(row.answer, row.language)
        ]
        if bad_ids:
            await self.session.execute(delete(AnswerCache).where(AnswerCache.id.in_(bad_ids)))
        return len(bad_ids)

    async def upsert_answer_cache(
        self,
        *,
        normalized_query: str,
        language: str,
        intent: str,
        answer: str,
        product_slugs: list[str],
        citations: list[dict[str, Any]],
        knowledge_version: int,
        ttl_days: int | None = None,
    ) -> None:
        if is_corrupted_cached_answer(answer, language):
            return
        # Remove any stale cache row for the same query+language under a different old intent
        await self.session.execute(
            delete(AnswerCache).where(
                AnswerCache.normalized_query == normalized_query,
                AnswerCache.language == language,
                AnswerCache.knowledge_version == knowledge_version,
                AnswerCache.intent != intent,
            )
        )
        effective_ttl = ttl_days if ttl_days is not None else settings.ANSWER_CACHE_TTL_DAYS
        expires_at = datetime.now(UTC) + timedelta(days=effective_ttl)
        stmt = (
            insert(AnswerCache)
            .values(
                normalized_query=normalized_query,
                language=language,
                intent=intent,
                answer=answer,
                product_slugs=product_slugs,
                citations=citations,
                knowledge_version=knowledge_version,
                hit_count=0,
                expires_at=expires_at,
            )
            .on_conflict_do_update(
                constraint="uq_answer_cache_key",
                set_={
                    "answer": answer,
                    "product_slugs": product_slugs,
                    "citations": citations,
                    "expires_at": expires_at,
                },
            )
        )
        await self.session.execute(stmt)

    async def get_active_answer_cache_keys(
        self, knowledge_version: int
    ) -> set[tuple[str, str, str]]:
        now = datetime.now(UTC)
        stmt = select(
            AnswerCache.normalized_query,
            AnswerCache.language,
            AnswerCache.intent,
        ).where(
            AnswerCache.knowledge_version == knowledge_version,
            AnswerCache.expires_at > now,
        )
        rows = (await self.session.execute(stmt)).all()
        return {(row[0], row[1], row[2]) for row in rows}

    async def list_active_answer_cache(
        self, knowledge_version: int
    ) -> list[AnswerCache]:
        now = datetime.now(UTC)
        stmt = (
            select(AnswerCache)
            .where(
                AnswerCache.knowledge_version == knowledge_version,
                AnswerCache.expires_at > now,
            )
            .order_by(AnswerCache.intent.asc(), AnswerCache.normalized_query.asc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_products_by_slugs(self, slugs: list[str]) -> list[ProductSummaryOut]:
        if not slugs:
            return []
        stmt = (
            select(Product)
            .join(MenuCategory, Product.category_id == MenuCategory.id)
            .where(
                Product.slug.in_(slugs),
                Product.is_active.is_(True),
                MenuCategory.is_active.is_(True),
            )
            .options(
                selectinload(Product.category),
                selectinload(Product.variants),
                selectinload(Product.product_ingredients).selectinload(
                    ProductIngredient.ingredient
                ),
            )
        )
        rows = list((await self.session.execute(stmt)).scalars().all())
        by_slug = {p.slug: build_product_summary(p) for p in rows}
        return [by_slug[s] for s in slugs if s in by_slug]

    async def get_unsafe_product_names(self, excluded_allergens: list[str]) -> list[str]:
        if not excluded_allergens:
            return []
        stmt = select(Product.name_vi).where(
            Product.is_active.is_(True),
            Product.product_ingredients.any(
                and_(
                    ProductIngredient.is_optional.is_(False),
                    ProductIngredient.ingredient.has(
                        Ingredient.allergen_code.in_(excluded_allergens)
                    ),
                )
            ),
        )
        names = list((await self.session.execute(stmt)).scalars().all())
        if "DAIRY" in excluded_allergens:
            milk_stmt = select(Product.name_vi).where(
                Product.is_active.is_(True), Product.has_milk.is_(True)
            )
            names.extend((await self.session.execute(milk_stmt)).scalars().all())
        return sorted(set(names))
