from __future__ import annotations

import uuid

from app.core.config import settings
from rag.retrieval import RetrievedChunk


def reciprocal_rank_fusion(
    *ranked_lists: list[RetrievedChunk],
    k: int | None = None,
    top_k: int | None = None,
) -> list[RetrievedChunk]:
    """
    Fuse multiple ranked chunk lists using Reciprocal Rank Fusion:
        RRF(d) = sum_{r in R} 1 / (k + rank_r(d))
    """
    rrf_k = k if k is not None else settings.RAG_RRF_K
    limit = top_k if top_k is not None else settings.RAG_FINAL_TOP_K

    merged: dict[uuid.UUID, RetrievedChunk] = {}

    for ranked in ranked_lists:
        for rank_idx, item in enumerate(ranked, start=1):
            existing = merged.get(item.chunk_id)
            if existing is None:
                existing = RetrievedChunk(
                    chunk_id=item.chunk_id,
                    document_id=item.document_id,
                    source_key=item.source_key,
                    title=item.title,
                    category=item.category,
                    section=item.section,
                    content=item.content,
                    dense_score=item.dense_score,
                    lexical_score=item.lexical_score,
                    dense_rank=item.dense_rank,
                    lexical_rank=item.lexical_rank,
                    rrf_score=0.0,
                    metadata=dict(item.metadata),
                )
                merged[item.chunk_id] = existing
            else:
                if item.dense_score is not None:
                    existing.dense_score = item.dense_score
                    existing.dense_rank = item.dense_rank
                if item.lexical_score is not None:
                    existing.lexical_score = item.lexical_score
                    existing.lexical_rank = item.lexical_rank

            existing.rrf_score += 1.0 / (rrf_k + rank_idx)

    ordered = sorted(
        merged.values(),
        key=lambda c: (
            c.rrf_score,
            c.dense_score if c.dense_score is not None else -1.0,
            c.lexical_score if c.lexical_score is not None else -1.0,
        ),
        reverse=True,
    )
    for item in ordered:
        item.rrf_score = round(item.rrf_score, 6)
    return ordered[:limit]
