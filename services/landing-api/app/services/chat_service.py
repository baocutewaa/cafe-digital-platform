from __future__ import annotations

import hmac
import json
import time
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ResourceNotFoundError, UnauthorizedSessionError
from app.core.security import generate_session_token, hash_session_token
from app.integrations.ollama_client import ollama_client
from app.models.conversation import ChatSession
from app.repositories.chat_repo import ChatRepository
from app.repositories.store_repo import StoreRepository
from app.schemas.chat import (
    ChatFeedbackRequest,
    ChatFeedbackResponse,
    CreateChatSessionRequest,
    CreateChatSessionResponse,
)
from app.schemas.menu import ProductSummaryOut
from app.services.menu_service import build_product_summary
from app.services.rate_limit import chat_rate_limiter
from rag.generation.answer_generator import AnswerGenerator, GenerationMetrics
from rag.generation.fast_path import try_build_fast_path
from rag.generation.guards import is_corrupted_cached_answer
from rag.generation.intent_router import IntentType, classify_intent
from rag.retrieval.context_builder import HybridRetriever
from rag.retrieval.query_parser import parse_query

_CACHEABLE_INTENTS = {
    IntentType.COFFEE_KNOWLEDGE,
    IntentType.PRODUCT_RECOMMENDATION,
    IntentType.ALLERGEN_INGREDIENT,
}


def format_sse_event(event: str, data: Any) -> str:
    payload = json.dumps(data, ensure_ascii=False, default=str)
    return f"event: {event}\ndata: {payload}\n\n"


def _serialize_products(products: list[Any]) -> list[dict[str, Any]]:
    serialized: list[dict[str, Any]] = []
    for prod in products:
        if isinstance(prod, ProductSummaryOut):
            serialized.append(prod.model_dump(mode="json"))
        else:
            serialized.append(build_product_summary(prod).model_dump(mode="json"))
    return serialized


class ChatService:
    def __init__(self, session: AsyncSession) -> None:
        self.db = session
        self.repo = ChatRepository(session)
        self.store_repo = StoreRepository(session)
        self.retriever = HybridRetriever(session)
        self.generator = AnswerGenerator()

    async def create_session(
        self, payload: CreateChatSessionRequest
    ) -> CreateChatSessionResponse:
        store_id: uuid.UUID | None = None
        if payload.store_slug:
            store = await self.store_repo.get_by_slug(payload.store_slug)
            if store is None:
                raise ResourceNotFoundError(f"Không tìm thấy chi nhánh '{payload.store_slug}'.")
            store_id = store.id

        raw_token = generate_session_token()
        token_hash = hash_session_token(raw_token)
        expires_at = datetime.now(UTC) + timedelta(hours=settings.SESSION_TTL_HOURS)

        chat_session = await self.repo.create_session(
            session_token_hash=token_hash,
            language=payload.language,
            store_id=store_id,
            expires_at=expires_at,
        )
        await self.db.commit()

        health = await ollama_client.check_health(use_cache=True)
        ai_mode = "online" if health.get("connected") else "fast_lookup_only"

        return CreateChatSessionResponse(
            session_id=chat_session.id,
            session_token=raw_token,
            language=payload.language,
            expires_at=expires_at,
            ai_mode=ai_mode,
        )

    async def verify_session(
        self, session_id: uuid.UUID, raw_token: str | None
    ) -> ChatSession:
        if not raw_token:
            raise UnauthorizedSessionError("Thiếu X-Session-Token header.")

        chat_session = await self.repo.get_active_session(session_id)
        if chat_session is None:
            raise UnauthorizedSessionError("Phiên chat không tồn tại hoặc đã hết hạn.")

        expected_hash = hash_session_token(raw_token)
        if not hmac.compare_digest(expected_hash, chat_session.session_token_hash):
            raise UnauthorizedSessionError("Session token không hợp lệ.")
        return chat_session

    async def submit_feedback(
        self,
        message_id: uuid.UUID,
        raw_token: str | None,
        payload: ChatFeedbackRequest,
    ) -> ChatFeedbackResponse:
        if not raw_token:
            raise UnauthorizedSessionError("Thiếu X-Session-Token header.")

        row = await self.repo.get_message_with_session(message_id)
        if row is None:
            raise ResourceNotFoundError(f"Không tìm thấy tin nhắn '{message_id}'.")

        msg, chat_session = row
        expected_hash = hash_session_token(raw_token)
        if not hmac.compare_digest(expected_hash, chat_session.session_token_hash):
            raise UnauthorizedSessionError("Không có quyền đánh giá tin nhắn này.")

        fb = await self.repo.upsert_feedback(
            message_id=msg.id,
            rating=payload.rating,
            comment=payload.comment,
        )
        await self.db.commit()
        return ChatFeedbackResponse.model_validate(fb)

    async def prepare_stream(
        self,
        *,
        chat_session: ChatSession,
        client_message_id: str | None,
        client_ip: str,
    ) -> tuple[Any, Any] | None:
        """
        Check idempotent replay and enforce rate limit BEFORE StreamingResponse starts,
        so RateLimitExceededError produces a proper HTTP 429 JSON response.
        """
        if client_message_id:
            existing_user = await self.repo.find_user_message_by_client_id(
                chat_session.id, client_message_id
            )
            if existing_user is not None:
                prev_reply = await self.repo.find_next_assistant_reply(
                    chat_session.id, existing_user.created_at
                )
                if prev_reply is not None:
                    return existing_user, prev_reply

        chat_rate_limiter.check_and_record(str(chat_session.id), client_ip)
        return None

    async def stream_message(
        self,
        *,
        chat_session: ChatSession,
        content: str,
        client_message_id: str | None,
        client_ip: str,
        replayed: tuple[Any, Any] | None = None,
        rate_limit_checked: bool = False,
    ) -> AsyncGenerator[str, None]:
        t_start = time.perf_counter()
        clean_content = content.strip()

        if replayed is None and not rate_limit_checked:
            replayed = await self.prepare_stream(
                chat_session=chat_session,
                client_message_id=client_message_id,
                client_ip=client_ip,
            )

        if replayed is not None:
            existing_user, prev_reply = replayed
            prods = await self.repo.get_products_by_slugs(
                list(prev_reply.recommended_product_slugs or [])
            )
            yield format_sse_event(
                "meta",
                {
                    "session_id": str(chat_session.id),
                    "user_message_id": str(existing_user.id),
                    "assistant_message_id": str(prev_reply.id),
                    "intent": prev_reply.intent,
                    "replayed": True,
                },
            )
            if prods:
                yield format_sse_event("products", _serialize_products(prods))
            yield format_sse_event("token", {"delta": prev_reply.content})
            if prev_reply.citations:
                yield format_sse_event("sources", prev_reply.citations)
            yield format_sse_event(
                "done",
                {
                    "message_id": str(prev_reply.id),
                    "intent": prev_reply.intent,
                    "model": prev_reply.model,
                    "ttft_ms": prev_reply.ttft_ms or 0,
                    "latency_ms": prev_reply.latency_ms or 0,
                    "cached": prev_reply.cached,
                    "degraded": prev_reply.degraded,
                },
            )
            return

        parsed_preview = parse_query(clean_content)
        predicted_intent = classify_intent(parsed_preview)

        # Fetch prior turns BEFORE inserting current user message
        history = await self.repo.get_recent_history(chat_session.id)

        user_msg = await self.repo.create_message(
            session_id=chat_session.id,
            role="user",
            content=clean_content,
            client_message_id=client_message_id,
            intent=predicted_intent.value,
        )

        # Persist extracted session preferences cleanly
        merged_prefs = dict(chat_session.preferences or {})
        if parsed_preview.max_price is not None:
            merged_prefs["max_price"] = parsed_preview.max_price
        if parsed_preview.excluded_allergens:
            merged_prefs["excluded_allergens"] = sorted(
                set(merged_prefs.get("excluded_allergens", []))
                | set(parsed_preview.excluded_allergens)
            )
        if parsed_preview.taste_tags:
            merged_prefs["taste_tags"] = parsed_preview.taste_tags
        if merged_prefs != (chat_session.preferences or {}):
            await self.repo.update_session_preferences(chat_session.id, merged_prefs)

        await self.db.commit()

        assistant_id = uuid.uuid4()
        yield format_sse_event(
            "meta",
            {
                "session_id": str(chat_session.id),
                "user_message_id": str(user_msg.id),
                "assistant_message_id": str(assistant_id),
                "intent": predicted_intent.value,
            },
        )
        yield format_sse_event("status", {"stage": "retrieving"})

        # 1. Check Answer Cache early for standalone knowledge/recommendation queries
        kb_version = await self.repo.get_current_knowledge_version()
        if predicted_intent in _CACHEABLE_INTENTS:
            cache_hit = await self.repo.lookup_answer_cache(
                normalized_query=parsed_preview.normalized_query,
                language=parsed_preview.language,
                knowledge_version=kb_version,
            )
            if cache_hit is not None:
                cached_prods = await self.repo.get_products_by_slugs(
                    list(cache_hit.product_slugs or [])
                )
                if cached_prods:
                    yield format_sse_event("products", _serialize_products(cached_prods))
                yield format_sse_event("token", {"delta": cache_hit.answer})
                if cache_hit.citations:
                    yield format_sse_event("sources", list(cache_hit.citations))

                total_ms = int((time.perf_counter() - t_start) * 1000)
                saved = await self.repo.create_message(
                    session_id=chat_session.id,
                    role="assistant",
                    content=cache_hit.answer,
                    intent=cache_hit.intent,
                    model="answer-cache",
                    ttft_ms=total_ms,
                    latency_ms=total_ms,
                    cached=True,
                    degraded=False,
                    recommended_product_slugs=list(cache_hit.product_slugs or []),
                    citations=list(cache_hit.citations or []),
                )
                await self.db.commit()
                yield format_sse_event(
                    "done",
                    {
                        "message_id": str(saved.id),
                        "intent": cache_hit.intent,
                        "model": "answer-cache",
                        "ttft_ms": total_ms,
                        "latency_ms": total_ms,
                        "cached": True,
                        "degraded": False,
                    },
                )
                return

        # 2. Run Hybrid Retrieval + SQL Retrieval
        retrieval = await self.retriever.retrieve(clean_content, history=history)
        product_payload = _serialize_products(retrieval.products)
        product_slugs = [p.slug for p in retrieval.products]
        chunk_ids = [str(c.chunk_id) for c in retrieval.chunks]
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

        if product_payload:
            yield format_sse_event("products", product_payload)

        # 3. Check SQL Fast-path
        fast_res = try_build_fast_path(retrieval)
        if fast_res.handled:
            yield format_sse_event("token", {"delta": fast_res.answer})
            total_ms = int((time.perf_counter() - t_start) * 1000)
            saved = await self.repo.create_message(
                session_id=chat_session.id,
                role="assistant",
                content=fast_res.answer,
                intent=retrieval.intent.value,
                model="sql-fast-path",
                ttft_ms=total_ms,
                latency_ms=total_ms,
                cached=False,
                degraded=False,
                recommended_product_slugs=product_slugs,
                citations=[],
            )
            await self.db.commit()
            yield format_sse_event(
                "done",
                {
                    "message_id": str(saved.id),
                    "intent": retrieval.intent.value,
                    "model": "sql-fast-path",
                    "ttft_ms": total_ms,
                    "latency_ms": total_ms,
                    "cached": False,
                    "degraded": False,
                },
            )
            return

        # 4. Stream via Ollama (qwen3:4b, think=false) or Offline Fallback
        unsafe_names = await self.repo.get_unsafe_product_names(
            retrieval.parsed_query.excluded_allergens
        )
        yield format_sse_event("status", {"stage": "generating"})

        final_metrics: GenerationMetrics | None = None
        async for delta, metrics in self.generator.stream_answer(
            retrieval, history=history, unsafe_product_names=unsafe_names
        ):
            if delta:
                yield format_sse_event("token", {"delta": delta})
            if metrics is not None:
                final_metrics = metrics

        assert final_metrics is not None
        if citations_payload:
            yield format_sse_event("sources", citations_payload)

        total_ms = int((time.perf_counter() - t_start) * 1000)
        saved = await self.repo.create_message(
            session_id=chat_session.id,
            role="assistant",
            content=final_metrics.answer,
            intent=retrieval.intent.value,
            model=final_metrics.model,
            ttft_ms=final_metrics.ttft_ms,
            latency_ms=total_ms,
            cached=False,
            degraded=final_metrics.degraded,
            retrieved_chunk_ids=chunk_ids,
            recommended_product_slugs=product_slugs,
            citations=citations_payload,
        )

        # Write to answer_cache only for healthy, non-degraded, grounded replies
        if (
            not final_metrics.degraded
            and final_metrics.model != "abstention"
            and retrieval.intent in _CACHEABLE_INTENTS
            and not is_corrupted_cached_answer(
                final_metrics.answer, retrieval.parsed_query.language
            )
        ):
            await self.repo.upsert_answer_cache(
                normalized_query=retrieval.parsed_query.normalized_query,
                language=retrieval.parsed_query.language,
                intent=retrieval.intent.value,
                answer=final_metrics.answer,
                product_slugs=product_slugs,
                citations=citations_payload,
                knowledge_version=kb_version,
            )

        await self.db.commit()
        yield format_sse_event(
            "done",
            {
                "message_id": str(saved.id),
                "intent": retrieval.intent.value,
                "model": final_metrics.model,
                "ttft_ms": final_metrics.ttft_ms,
                "latency_ms": total_ms,
                "cached": False,
                "degraded": final_metrics.degraded,
            },
        )
