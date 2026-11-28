from __future__ import annotations

import re
import time
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import OllamaUnavailableError
from app.integrations.ollama_client import OllamaClient, ollama_client
from app.schemas.menu import ProductDetailOut
from app.schemas.promotion import PromotionOut
from app.schemas.store import StoreOut
from rag.generation.intent_router import IntentType, classify_intent
from rag.retrieval import CitationRef, RetrievedChunk
from rag.retrieval.dense import DenseRetriever
from rag.retrieval.lexical import LexicalRetriever
from rag.retrieval.query_parser import ParsedQuery, parse_query
from rag.retrieval.rrf import reciprocal_rank_fusion
from rag.retrieval.sql_retriever import SqlProductRetriever


@dataclass(slots=True)
class RetrievalResult:
    parsed_query: ParsedQuery
    intent: IntentType
    chunks: list[RetrievedChunk] = field(default_factory=list)
    products: list[ProductDetailOut] = field(default_factory=list)
    stores: list[StoreOut] = field(default_factory=list)
    promotions: list[PromotionOut] = field(default_factory=list)
    citations: list[CitationRef] = field(default_factory=list)
    formatted_context: str = ""
    degraded: bool = False
    retrieval_latency_ms: float = 0.0


def build_citations(chunks: list[RetrievedChunk]) -> list[CitationRef]:
    seen: set[tuple[str, str]] = set()
    citations: list[CitationRef] = []
    for chunk in chunks:
        key = (chunk.source_key, chunk.section)
        if key in seen:
            continue
        seen.add(key)
        cleaned_chunk = re.sub(r"(?m)^\s*\[[^\]\n]+\]\s*\n?", "", chunk.content)
        snippet = cleaned_chunk.replace("\n", " ").strip()[:180]
        citations.append(
            CitationRef(
                source_key=chunk.source_key,
                title=chunk.title,
                category=chunk.category,
                section=chunk.section,
                snippet=snippet,
            )
        )
    return citations


_TEMP_LABEL_VI = {
    "hot": "Chỉ phục vụ nóng",
    "iced": "Chỉ phục vụ đá",
    "both": "Phục vụ nóng & đá",
}

_PAIRING_OR_ALTERNATIVES_SIGNALS = (
    "uong kem",
    "an kem",
    "dung kem",
    "ghep cap",
    "pair",
    "mon khac",
    "con mon nao",
    "ngoai ra",
    "tuong tu",
)


def _is_pairing_or_alternatives_query(ascii_query: str) -> bool:
    return any(sig in ascii_query for sig in _PAIRING_OR_ALTERNATIVES_SIGNALS)


def _filter_safe_products(
    products: list[ProductDetailOut],
    excluded_allergens: list[str],
) -> list[ProductDetailOut]:
    if not excluded_allergens:
        return products
    excluded_set = set(excluded_allergens)
    safe: list[ProductDetailOut] = []
    for prod in products:
        if "DAIRY" in excluded_set and prod.has_milk:
            continue
        required_allergens = {
            ing.allergen_code
            for ing in prod.ingredients
            if not ing.is_optional and ing.allergen_code
        }
        if required_allergens & excluded_set:
            continue
        safe.append(prod)
    return safe


def format_rag_context(
    chunks: list[RetrievedChunk],
    products: list[ProductDetailOut],
) -> str:
    parts: list[str] = []

    if products:
        prod_lines = ["[SQL VERIFIED MENU DATA]"]
        for prod in products:
            variants_str = ", ".join(
                f"{v.size}: {v.price_vnd:,}đ ({v.calories_kcal or '?'} kcal, "
                f"{_TEMP_LABEL_VI.get(v.temperature, v.temperature)})".replace(",", ".")
                for v in prod.variants
                if v.is_available
            )
            allergens_str = (
                ", ".join(prod.allergens) if prod.allergens else "Không dị ứng phổ biến"
            )
            ingredients_str = ", ".join(
                f"{ing.name_vi}"
                + (" (tùy chọn)" if ing.is_optional else "")
                + (f" [{ing.allergen_code}]" if ing.allergen_code else "")
                for ing in prod.ingredients
            )
            desc_line = prod.short_description_vi
            if prod.story_vi:
                desc_line = f"{desc_line} {prod.story_vi}"
            prod_lines.append(
                f"- {prod.name_vi} ({prod.name_en}) [slug={prod.slug}]: "
                f"Giá [{variants_str}] | Caffeine={prod.caffeine_level} | "
                f"Độ đắng={prod.bitterness_level}/5 | Độ ngọt chuẩn={prod.sweetness_level}/5 | "
                f"Có sữa bò={prod.has_milk} | Dị ứng=[{allergens_str}]"
                + (f" | Nguyên liệu=[{ingredients_str}]" if ingredients_str else "")
                + (f"\n  Mô tả & Hương vị: {desc_line}" if desc_line else "")
            )
        parts.append("\n".join(prod_lines))

    if chunks:
        kb_lines = ["[KNOWLEDGE BASE CONTEXT]"]
        for idx, chunk in enumerate(chunks, start=1):
            kb_lines.append(
                f"({idx}) [{chunk.title} | {chunk.source_key}]\n{chunk.content}"
            )
        parts.append("\n\n".join(kb_lines))

    return "\n\n".join(parts)


class HybridRetriever:
    """
    Orchestrates Query Parsing, Intent Routing, SQL Retrieval,
    Hybrid Search (pgvector + FTS/trgm -> RRF k=60), and Offline Lexical+SQL Fallback.
    """

    def __init__(
        self,
        session: AsyncSession,
        ai_client: OllamaClient | None = None,
    ) -> None:
        self.session = session
        self.ai_client = ai_client or ollama_client
        self.dense = DenseRetriever(session)
        self.lexical = LexicalRetriever(session)
        self.sql = SqlProductRetriever(session)

    async def _resolve_products_from_history(
        self, history: list[dict[str, str]] | None
    ) -> list[ProductDetailOut]:
        if not history:
            return []
        for turn in reversed(history[-4:]):
            text = (turn.get("content") or "").strip()
            if not text:
                continue
            hist_parsed = parse_query(text)
            found = await self.sql.find_products_by_name(hist_parsed, limit=2)
            if found:
                return found
        return []

    async def retrieve(
        self,
        raw_query: str,
        top_k: int | None = None,
        offline_fallback: bool = False,
        history: list[dict[str, str]] | None = None,
    ) -> RetrievalResult:
        t0 = time.perf_counter()
        parsed = parse_query(raw_query)
        intent = classify_intent(parsed)
        final_k = top_k or settings.RAG_FINAL_TOP_K

        if intent == IntentType.OUT_OF_SCOPE:
            return RetrievalResult(
                parsed_query=parsed,
                intent=intent,
                degraded=offline_fallback,
                retrieval_latency_ms=round((time.perf_counter() - t0) * 1000.0, 2),
            )

        products: list[ProductDetailOut] = []
        stores: list[StoreOut] = []
        promotions: list[PromotionOut] = []
        wants_pairing_or_alts = _is_pairing_or_alternatives_query(parsed.ascii_query)

        # 1. SQL Retrieval by Intent
        if intent == IntentType.STORE_INFO:
            stores = await self.sql.search_stores(parsed)
        elif intent == IntentType.PROMOTION_LOOKUP:
            promotions = await self.sql.search_promotions()
        elif intent == IntentType.PRODUCT_LOOKUP:
            products = await self.sql.find_products_by_name(parsed, limit=5)
            if not products and parsed.has_pronoun_reference:
                products = await self._resolve_products_from_history(history)
            if not products:
                products = await self.sql.search_products(parsed, limit=6)
        elif intent == IntentType.PRODUCT_RECOMMENDATION:
            has_discovery_filters = bool(
                parsed.max_price is not None
                or parsed.max_sweetness is not None
                or parsed.max_bitterness is not None
                or parsed.caffeine_level is not None
                or parsed.has_milk is not None
                or parsed.excluded_allergens
                or parsed.is_signature_only is not None
            )
            named = await self.sql.find_products_by_name(
                parsed, limit=4, exact_only=has_discovery_filters
            )
            if (
                not named
                and not has_discovery_filters
                and (parsed.has_pronoun_reference or parsed.is_customization_query)
            ):
                named = await self._resolve_products_from_history(history)
            named_safe = _filter_safe_products(named, parsed.excluded_allergens)

            if named_safe and not wants_pairing_or_alts and not (
                parsed.max_price is not None or parsed.max_sweetness is not None
            ):
                # User is asking specifically about named drink(s) (e.g. how to enjoy / customize)
                products = named_safe
            else:
                searched = await self.sql.search_products(parsed, limit=6)
                if named_safe and wants_pairing_or_alts:
                    seen_slugs = {p.slug for p in named_safe}
                    products = [
                        *named_safe[:2],
                        *(p for p in searched if p.slug not in seen_slugs),
                    ][:6]
                else:
                    products = searched
                if not products and not parsed.excluded_allergens:
                    products = named or await self.sql.find_products_by_name(parsed, limit=5)
        elif intent == IntentType.ALLERGEN_INGREDIENT:
            if not parsed.excluded_allergens:
                # Ingredient/allergen inspection of a specific product ("Món X có chứa sữa bò không?")
                named = await self.sql.find_products_by_name(parsed, limit=4)
                if not named and parsed.has_pronoun_reference:
                    named = await self._resolve_products_from_history(history)
                products = named
            if not products:
                products = await self.sql.search_products(parsed, limit=6)
            if not products and not parsed.excluded_allergens:
                products = await self.sql.find_products_by_name(parsed, limit=5)

        # Fast-path intents do not require embedding or vector search
        if intent in (
            IntentType.PRODUCT_LOOKUP,
            IntentType.STORE_INFO,
            IntentType.PROMOTION_LOOKUP,
        ):
            return RetrievalResult(
                parsed_query=parsed,
                intent=intent,
                products=products,
                stores=stores,
                promotions=promotions,
                formatted_context=format_rag_context([], products),
                degraded=offline_fallback,
                retrieval_latency_ms=round((time.perf_counter() - t0) * 1000.0, 2),
            )

        # 2. Knowledge Base Hybrid Search (or Lexical Fallback when Ollama is offline)
        lexical_chunks = await self.lexical.search(
            raw_query, top_k=settings.RAG_TOP_K_LEXICAL
        )
        aux_ranked_lists: list[list[RetrievedChunk]] = []
        if parsed.is_customization_query:
            cust_chunks = await self.lexical.search(
                "tùy chỉnh độ ngọt lượng đá sữa hạt shot espresso",
                top_k=6,
            )
            if cust_chunks:
                aux_ranked_lists.append(cust_chunks)
        if len(products) == 1:
            prod_chunks = await self.lexical.search(products[0].name_vi, top_k=4)
            if prod_chunks:
                aux_ranked_lists.append(prod_chunks)

        dense_chunks: list[RetrievedChunk] = []
        degraded = offline_fallback or self.ai_client.is_circuit_open

        if not degraded:
            try:
                embeddings = await self.ai_client.embed(raw_query)
                if embeddings:
                    dense_chunks = await self.dense.search(
                        embeddings[0], top_k=settings.RAG_TOP_K_DENSE
                    )
                else:
                    degraded = True
            except OllamaUnavailableError:
                degraded = True

        ranked_inputs: list[list[RetrievedChunk]] = []
        if dense_chunks:
            ranked_inputs.append(dense_chunks)
        if lexical_chunks:
            ranked_inputs.append(lexical_chunks)
        ranked_inputs.extend(aux_ranked_lists)

        fused = (
            reciprocal_rank_fusion(
                *ranked_inputs,
                k=settings.RAG_RRF_K,
                top_k=final_k,
            )
            if ranked_inputs
            else []
        )

        # Attach SQL grounding if COFFEE_KNOWLEDGE mentions specific product names (or history)
        if intent == IntentType.COFFEE_KNOWLEDGE and not products:
            products = await self.sql.find_products_by_name(parsed, limit=3)
            if not products and (parsed.has_pronoun_reference or parsed.is_customization_query):
                products = await self._resolve_products_from_history(history)

        citations = build_citations(fused)
        formatted = format_rag_context(fused, products)

        return RetrievalResult(
            parsed_query=parsed,
            intent=intent,
            chunks=fused,
            products=products,
            stores=stores,
            promotions=promotions,
            citations=citations,
            formatted_context=formatted,
            degraded=degraded,
            retrieval_latency_ms=round((time.perf_counter() - t0) * 1000.0, 2),
        )
