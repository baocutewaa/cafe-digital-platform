from __future__ import annotations

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
        snippet = chunk.content.replace("\n", " ").strip()[:180]
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


def format_rag_context(
    chunks: list[RetrievedChunk],
    products: list[ProductDetailOut],
) -> str:
    parts: list[str] = []

    if products:
        prod_lines = ["[SQL VERIFIED MENU DATA]"]
        for prod in products:
            variants_str = ", ".join(
                f"{v.size}: {v.price_vnd:,}đ ({v.calories_kcal or '?'} kcal)".replace(",", ".")
                for v in prod.variants
                if v.is_available
            )
            allergens_str = ", ".join(prod.allergens) if prod.allergens else "Không dị ứng phổ biến"
            prod_lines.append(
                f"- {prod.name_vi} ({prod.name_en}) [slug={prod.slug}]: "
                f"Giá [{variants_str}] | Caffeine={prod.caffeine_level} | "
                f"Độ đắng={prod.bitterness_level}/5 | Độ ngọt={prod.sweetness_level}/5 | "
                f"Có sữa bò={prod.has_milk} | Dị ứng=[{allergens_str}]"
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

    async def retrieve(
        self,
        raw_query: str,
        top_k: int | None = None,
        offline_fallback: bool = False,
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

        # 1. SQL Retrieval by Intent
        if intent == IntentType.STORE_INFO:
            stores = await self.sql.search_stores(parsed)
        elif intent == IntentType.PROMOTION_LOOKUP:
            promotions = await self.sql.search_promotions()
        elif intent == IntentType.PRODUCT_LOOKUP:
            products = await self.sql.find_products_by_name(parsed, limit=5)
            if not products:
                products = await self.sql.search_products(parsed, limit=6)
        elif intent == IntentType.PRODUCT_RECOMMENDATION:
            has_strict_filters = bool(
                parsed.excluded_allergens
                or parsed.has_milk is not None
                or parsed.max_price is not None
                or parsed.caffeine_level is not None
                or parsed.max_bitterness is not None
                or parsed.is_signature_only is not None
            )
            if not has_strict_filters and parsed.search_terms:
                products = await self.sql.find_products_by_name(parsed, limit=4)
            if not products:
                products = await self.sql.search_products(parsed, limit=6)
            if not products and not parsed.excluded_allergens:
                products = await self.sql.find_products_by_name(parsed, limit=5)
        elif intent == IntentType.ALLERGEN_INGREDIENT:
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

        if dense_chunks:
            fused = reciprocal_rank_fusion(
                dense_chunks,
                lexical_chunks,
                k=settings.RAG_RRF_K,
                top_k=final_k,
            )
        else:
            fused = reciprocal_rank_fusion(
                lexical_chunks,
                k=settings.RAG_RRF_K,
                top_k=final_k,
            )

        # Attach SQL grounding if COFFEE_KNOWLEDGE mentions specific product names
        if intent == IntentType.COFFEE_KNOWLEDGE and not products:
            products = await self.sql.find_products_by_name(parsed, limit=3)

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
