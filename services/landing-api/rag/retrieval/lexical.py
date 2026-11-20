from __future__ import annotations

import re

from sqlalchemy import Float, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.knowledge import DocumentChunk, KnowledgeDocument, KnowledgeSource
from rag.retrieval import RetrievedChunk
from rag.text.normalize import normalize_query, strip_vietnamese_accents

_TOKEN_RE = re.compile(r"[0-9a-zA-ZÀ-ỹ]+")

_LEXICAL_STOPWORDS = {
    "a", "an", "and", "are", "ban", "bao", "bi", "cac", "can", "cho", "co",
    "cua", "da", "dang", "de", "den", "di", "do", "duoc", "em", "gi", "giup",
    "hay", "hien", "hom", "how", "is", "khong", "khi", "la", "lam", "ma",
    "may", "minh", "mon", "muon", "nao", "nay", "nen", "neu", "nhieu", "nhung",
    "o", "oi", "phai", "ra", "sao", "tai", "the", "thi", "to", "toi", "trong",
    "tu", "va", "vay", "ve", "voi", "what", "which", "with", "you", "your",
}


def _build_or_tsquery_str(raw_query: str) -> tuple[str, str]:
    normalized = normalize_query(raw_query)
    ascii_q = strip_vietnamese_accents(normalized).lower()

    tokens: list[str] = []
    for text_variant in (normalized, ascii_q):
        for tok in _TOKEN_RE.findall(text_variant):
            clean = tok.lower().strip()
            clean_ascii = strip_vietnamese_accents(clean)
            if len(clean) >= 2 and clean_ascii not in _LEXICAL_STOPWORDS and clean not in tokens:
                tokens.append(clean)

    if not tokens:
        tokens = [tok.lower() for tok in _TOKEN_RE.findall(ascii_q) if len(tok) >= 2]

    ts_expr = " | ".join(tokens[:16])
    return ts_expr, ascii_q


class LexicalRetriever:
    """Lexical retrieval combining PostgreSQL simple FTS and pg_trgm word_similarity."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def search(
        self,
        query_text: str,
        top_k: int | None = None,
        category: str | None = None,
    ) -> list[RetrievedChunk]:
        limit = top_k or settings.RAG_TOP_K_LEXICAL
        ts_expr, ascii_q = _build_or_tsquery_str(query_text)
        if not ts_expr and not ascii_q:
            return []

        trgm_expr = cast(func.word_similarity(ascii_q, DocumentChunk.search_text), Float)

        if ts_expr:
            ts_query = func.to_tsquery("simple", ts_expr)
            fts_rank = cast(func.ts_rank_cd(DocumentChunk.search_vector, ts_query), Float)
            combined_score = (fts_rank * 2.0 + trgm_expr).label("lexical_score")
            match_condition = or_(
                DocumentChunk.search_vector.op("@@")(ts_query),
                trgm_expr >= 0.25,
            )
        else:
            combined_score = trgm_expr.label("lexical_score")
            match_condition = trgm_expr >= 0.25

        stmt = (
            select(
                DocumentChunk,
                KnowledgeDocument.title,
                KnowledgeDocument.category,
                KnowledgeSource.source_key,
                combined_score,
            )
            .join(KnowledgeDocument, DocumentChunk.document_id == KnowledgeDocument.id)
            .join(KnowledgeSource, KnowledgeDocument.source_id == KnowledgeSource.id)
            .where(
                KnowledgeDocument.is_active.is_(True),
                KnowledgeSource.status == "active",
                match_condition,
            )
            .order_by(combined_score.desc())
            .limit(limit)
        )

        if category:
            stmt = stmt.where(KnowledgeDocument.category == category)

        rows = (await self.session.execute(stmt)).all()
        results: list[RetrievedChunk] = []
        for rank, (chunk, title, doc_cat, source_key, score) in enumerate(rows, start=1):
            meta = dict(chunk.metadata_ or {})
            results.append(
                RetrievedChunk(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    source_key=source_key,
                    title=title,
                    category=doc_cat,
                    section=str(meta.get("section") or title),
                    content=chunk.content,
                    lexical_score=round(float(score), 6),
                    lexical_rank=rank,
                    metadata=meta,
                )
            )
        return results
