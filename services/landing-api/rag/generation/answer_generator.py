from __future__ import annotations

import re
import time
from collections.abc import AsyncGenerator
from contextlib import aclosing
from dataclasses import dataclass

from app.core.exceptions import OllamaUnavailableError
from app.integrations.ollama_client import OllamaClient, ollama_client
from rag.generation.fast_path import build_offline_fallback_answer
from rag.generation.guards import (
    is_corrupted_cached_answer,
    looks_like_leaked_thinking,
    strip_think_tags,
)
from rag.generation.intent_router import IntentType
from rag.generation.prompts.system_prompts import build_rag_messages
from rag.retrieval.context_builder import RetrievalResult, _is_pairing_or_alternatives_query
from rag.text.normalize import strip_vietnamese_accents

_PRICE_VND_RE = re.compile(r"\b(\d{2,3})[.,](\d{3})\s*(?:đ|d|vnd|dong)?\b", re.IGNORECASE)
_PRICE_K_RE = re.compile(r"\b(\d{2,3})\s*k\b", re.IGNORECASE)


class _ThinkStreamFilter:
    """Buffers and strips `<think>...</think>` / `<thought>...</thought>` while streaming."""

    _OPEN_RE = re.compile(r"<(?:think|thought)>", re.IGNORECASE)
    _CLOSE_RE = re.compile(r"</(?:think|thought)>", re.IGNORECASE)
    _TAG_NAMES = ("<think>", "<thought>")

    def __init__(self) -> None:
        self._buf = ""
        self._in_think = False
        self._emitted_any = False

    def feed(self, chunk: str) -> str:
        self._buf += chunk
        out: list[str] = []

        while self._buf:
            if self._in_think:
                m_close = self._CLOSE_RE.search(self._buf)
                if m_close:
                    self._buf = self._buf[m_close.end() :]
                    if not self._emitted_any:
                        self._buf = self._buf.lstrip()
                    self._in_think = False
                    continue
                if len(self._buf) > 10:
                    self._buf = self._buf[-10:]
                break

            m_open = self._OPEN_RE.search(self._buf)
            if m_open:
                before = self._buf[: m_open.start()]
                if not self._emitted_any:
                    before = before.lstrip()
                if before:
                    out.append(before)
                    self._emitted_any = True
                self._buf = self._buf[m_open.end() :]
                self._in_think = True
                continue

            # Hold back any incomplete `<think` / `<thought` tag prefix at the end of the buffer
            hold_idx: int | None = None
            last_lt = self._buf.rfind("<")
            if last_lt != -1:
                tail = self._buf[last_lt:].lower()
                if any(tag.startswith(tail) for tag in self._TAG_NAMES):
                    hold_idx = last_lt

            emit_part = self._buf if hold_idx is None else self._buf[:hold_idx]
            if not self._emitted_any:
                emit_part = emit_part.lstrip()
            if emit_part:
                out.append(emit_part)
                self._emitted_any = True
            self._buf = "" if hold_idx is None else self._buf[hold_idx:]
            break

        return "".join(out)

    def enter_untagged_think(self) -> None:
        """
        Switch into thinking-suppression state when the model emitted untagged reasoning
        without an opening `<think>`, so tokens are discarded until `</think>` arrives.
        """
        self._buf = ""
        self._in_think = True

    def flush(self) -> str:
        if self._in_think or not self._buf:
            self._buf = ""
            return ""
        rest = self._buf if self._emitted_any else self._buf.lstrip()
        self._buf = ""
        if rest:
            self._emitted_any = True
        return rest


def extract_mentioned_prices_vnd(text: str) -> set[int]:
    prices: set[int] = set()
    for m in _PRICE_VND_RE.finditer(text):
        val = int(f"{m.group(1)}{m.group(2)}")
        if 10_000 <= val <= 500_000:
            prices.add(val)
    for m in _PRICE_K_RE.finditer(text):
        val = int(m.group(1)) * 1000
        if 10_000 <= val <= 500_000:
            prices.add(val)
    return prices


def post_check_answer(
    answer: str,
    retrieval: RetrievalResult,
    unsafe_product_names: list[str] | None = None,
) -> str:
    """
    Post-generation guard (Mục 10 P5 & R4):
    1. Detect ungrounded prices vs SQL-verified product_variants.
    2. Detect unsafe allergen product mentions when excluded_allergens is set.
    """
    cleaned = strip_think_tags(answer)
    notices: list[str] = []

    if retrieval.products:
        allowed_prices = {
            v.price_vnd
            for prod in retrieval.products
            for v in prod.variants
            if v.is_available
        }
        mentioned = extract_mentioned_prices_vnd(cleaned)
        # Allow promo discount numbers like 10.000đ if mentioned alongside cold brew promo
        invalid_prices = {
            p for p in mentioned if p not in allowed_prices and p != 10_000
        }
        if invalid_prices:
            price_summary = "; ".join(
                f"{p.name_vi}: từ {p.min_price_vnd:,}đ".replace(",", ".")
                for p in retrieval.products[:3]
            )
            notices.append(
                f"*Lưu ý giá niêm yết chính xác từ hệ thống:* {price_summary}."
            )

    if retrieval.parsed_query.excluded_allergens and unsafe_product_names:
        answer_ascii = strip_vietnamese_accents(cleaned.lower())
        flagged = [
            name
            for name in unsafe_product_names
            if strip_vietnamese_accents(name.lower()) in answer_ascii
        ]
        if flagged:
            safe_list = ", ".join(p.name_vi for p in retrieval.products[:5])
            excluded_str = ", ".join(retrieval.parsed_query.excluded_allergens)
            notices.append(
                f"*Cảnh báo kiểm tra dị ứng ({excluded_str}):* "
                f"Vui lòng tránh {', '.join(flagged)}. "
                f"Các món an toàn đã xác minh: {safe_list}."
            )

    if not notices:
        return cleaned
    return f"{cleaned}\n\n" + "\n".join(notices)


@dataclass(slots=True)
class GenerationMetrics:
    answer: str
    model: str | None
    ttft_ms: int | None
    latency_ms: int
    degraded: bool


class AnswerGenerator:
    def __init__(self, ai_client: OllamaClient | None = None) -> None:
        self.ai_client = ai_client or ollama_client

    async def stream_answer(
        self,
        retrieval: RetrievalResult,
        history: list[dict[str, str]] | None = None,
        unsafe_product_names: list[str] | None = None,
    ) -> AsyncGenerator[tuple[str, GenerationMetrics | None], None]:
        """
        Yield `(delta_text, None)` chunks while streaming, followed by a final
        `("", GenerationMetrics)` summary item. Falls back gracefully if Ollama fails.
        """
        t0 = time.perf_counter()
        ttft_ms: int | None = None

        # Abstain cleanly when COFFEE_KNOWLEDGE has zero relevant context and no SQL products
        if (
            retrieval.intent == IntentType.COFFEE_KNOWLEDGE
            and not retrieval.chunks
            and not retrieval.products
        ):
            msg = (
                "Mình chưa tìm thấy thông tin xác thực về câu hỏi này trong tài liệu hiện tại "
                "của BREW & BEAN. Bạn có thể hỏi về menu, giá món, thành phần dị ứng, chi nhánh "
                "hoặc phương pháp pha chế nhé!"
            )
            yield msg, None
            yield "", GenerationMetrics(
                answer=msg,
                model="abstention",
                ttft_ms=0,
                latency_ms=int((time.perf_counter() - t0) * 1000),
                degraded=retrieval.degraded,
            )
            return

        if retrieval.degraded or self.ai_client.is_circuit_open:
            fallback = build_offline_fallback_answer(retrieval)
            yield fallback, None
            yield "", GenerationMetrics(
                answer=fallback,
                model="lexical-sql-fallback",
                ttft_ms=int((time.perf_counter() - t0) * 1000),
                latency_ms=int((time.perf_counter() - t0) * 1000),
                degraded=True,
            )
            return

        single_focus = len(retrieval.products) == 1 and not _is_pairing_or_alternatives_query(
            retrieval.parsed_query.ascii_query
        )
        messages = build_rag_messages(
            user_query=retrieval.parsed_query.raw_query,
            formatted_context=retrieval.formatted_context,
            intent=retrieval.intent,
            language=retrieval.parsed_query.language,
            history=history,
            single_product_focus=single_focus,
        )

        lang = retrieval.parsed_query.language
        can_promote_fn = getattr(self.ai_client, "can_promote_think_mode", None)
        promote_fn = getattr(self.ai_client, "promote_to_separate_thinking", None)

        stream_filter = _ThinkStreamFilter()
        preamble_buf = ""
        preamble_flushed = False
        visible_answer_parts: list[str] = []

        for attempt in range(2):
            stream_filter = _ThinkStreamFilter()
            preamble_buf = ""
            preamble_flushed = False
            visible_answer_parts = []
            need_promote_retry = False

            try:
                async with aclosing(self.ai_client.stream_chat(messages)) as token_stream:
                    async for token in token_stream:
                        if ttft_ms is None:
                            ttft_ms = int((time.perf_counter() - t0) * 1000)
                        visible = stream_filter.feed(token)
                        if not visible:
                            continue

                        if not preamble_flushed:
                            preamble_buf += visible
                            trimmed_pre = preamble_buf.strip()
                            # Detect leaked thinking early (at >= 16 chars) before flushing anything
                            if len(trimmed_pre) >= 16 and looks_like_leaked_thinking(
                                trimmed_pre, lang
                            ):
                                if (
                                    attempt == 0
                                    and callable(can_promote_fn)
                                    and callable(promote_fn)
                                    and can_promote_fn()
                                ):
                                    promote_fn()
                                    need_promote_retry = True
                                    break
                                # Already in separate mode (or mock client): discard until </think>
                                preamble_buf = ""
                                stream_filter.enter_untagged_think()
                                continue

                            if len(trimmed_pre) < 64:
                                continue

                            preamble_flushed = True
                            visible_answer_parts.append(preamble_buf)
                            yield preamble_buf, None
                            preamble_buf = ""
                        else:
                            visible_answer_parts.append(visible)
                            yield visible, None
            except OllamaUnavailableError:
                if preamble_flushed and visible_answer_parts:
                    partial_visible = "".join(visible_answer_parts)
                    partial = post_check_answer(
                        partial_visible, retrieval, unsafe_product_names=unsafe_product_names
                    )
                    if looks_like_leaked_thinking(partial, lang):
                        final_text = build_offline_fallback_answer(retrieval)
                        yield f"\n\n{final_text}", None
                    else:
                        rem = stream_filter.flush()
                        if rem:
                            visible_answer_parts.append(rem)
                            yield rem, None
                        suffix = (
                            "\n\n*(Kết nối AI tạm gián đoạn — "
                            "bạn có thể xem thẻ sản phẩm gợi ý đi kèm.)*"
                        )
                        yield suffix, None
                        final_text = f"{''.join(visible_answer_parts)}{suffix}"
                else:
                    final_text = build_offline_fallback_answer(retrieval)
                    yield final_text, None

                yield "", GenerationMetrics(
                    answer=final_text,
                    model="lexical-sql-fallback",
                    ttft_ms=ttft_ms,
                    latency_ms=int((time.perf_counter() - t0) * 1000),
                    degraded=True,
                )
                return

            if need_promote_retry:
                continue
            break

        tail = stream_filter.flush()
        if not preamble_flushed:
            combined_head = (preamble_buf + tail).strip()
            if combined_head and not looks_like_leaked_thinking(combined_head, lang):
                visible_answer_parts.append(preamble_buf + tail)
                yield preamble_buf + tail, None
                preamble_flushed = True
        elif tail:
            visible_answer_parts.append(tail)
            yield tail, None

        clean_visible = "".join(visible_answer_parts).strip()
        if not clean_visible or is_corrupted_cached_answer(clean_visible, lang):
            fallback = build_offline_fallback_answer(retrieval)
            if not preamble_flushed:
                yield fallback, None
                final_answer = fallback
            else:
                final_answer = f"{clean_visible}\n\n{fallback}".strip()
                yield f"\n\n{fallback}", None
            yield "", GenerationMetrics(
                answer=final_answer,
                model="lexical-sql-fallback",
                ttft_ms=ttft_ms,
                latency_ms=int((time.perf_counter() - t0) * 1000),
                degraded=True,
            )
            return

        checked = post_check_answer(
            clean_visible, retrieval, unsafe_product_names=unsafe_product_names
        )
        stripped_vis = strip_think_tags(clean_visible)
        if len(checked) > len(stripped_vis):
            extra = checked[len(stripped_vis) :]
            yield extra, None

        yield "", GenerationMetrics(
            answer=checked,
            model=self.ai_client.base_url and self._model_name(),
            ttft_ms=ttft_ms,
            latency_ms=int((time.perf_counter() - t0) * 1000),
            degraded=False,
        )

    def _model_name(self) -> str:
        from app.core.config import settings

        return settings.LLM_MODEL

    async def generate_complete(
        self,
        retrieval: RetrievalResult,
        history: list[dict[str, str]] | None = None,
        unsafe_product_names: list[str] | None = None,
    ) -> GenerationMetrics:
        t0 = time.perf_counter()
        if retrieval.degraded or self.ai_client.is_circuit_open:
            fallback = build_offline_fallback_answer(retrieval)
            return GenerationMetrics(
                answer=fallback,
                model="lexical-sql-fallback",
                ttft_ms=0,
                latency_ms=int((time.perf_counter() - t0) * 1000),
                degraded=True,
            )

        single_focus = len(retrieval.products) == 1 and not _is_pairing_or_alternatives_query(
            retrieval.parsed_query.ascii_query
        )
        messages = build_rag_messages(
            user_query=retrieval.parsed_query.raw_query,
            formatted_context=retrieval.formatted_context,
            intent=retrieval.intent,
            language=retrieval.parsed_query.language,
            history=history,
            single_product_focus=single_focus,
        )
        lang = retrieval.parsed_query.language
        can_promote_fn = getattr(self.ai_client, "can_promote_think_mode", None)
        promote_fn = getattr(self.ai_client, "promote_to_separate_thinking", None)

        try:
            raw = await self.ai_client.chat(messages)
            checked = post_check_answer(
                raw, retrieval, unsafe_product_names=unsafe_product_names
            )
            if (
                is_corrupted_cached_answer(checked, lang)
                and callable(can_promote_fn)
                and callable(promote_fn)
                and can_promote_fn()
            ):
                promote_fn()
                raw = await self.ai_client.chat(messages)
                checked = post_check_answer(
                    raw, retrieval, unsafe_product_names=unsafe_product_names
                )
            latency_ms = int((time.perf_counter() - t0) * 1000)
            if is_corrupted_cached_answer(checked, lang):
                fallback = build_offline_fallback_answer(retrieval)
                return GenerationMetrics(
                    answer=fallback,
                    model="lexical-sql-fallback",
                    ttft_ms=latency_ms,
                    latency_ms=latency_ms,
                    degraded=True,
                )
            return GenerationMetrics(
                answer=checked,
                model=self._model_name(),
                ttft_ms=latency_ms,
                latency_ms=latency_ms,
                degraded=False,
            )
        except OllamaUnavailableError:
            fallback = build_offline_fallback_answer(retrieval)
            return GenerationMetrics(
                answer=fallback,
                model="lexical-sql-fallback",
                ttft_ms=None,
                latency_ms=int((time.perf_counter() - t0) * 1000),
                degraded=True,
            )
