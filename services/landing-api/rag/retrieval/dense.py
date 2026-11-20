from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.knowledge import DocumentChunk, KnowledgeDocument, KnowledgeSource
from rag.retrieval import RetrievedChunk


class DenseRetriever:
    """Dense vector similarity search over document_chunks using pgvector cosine distance."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def search(
        self,
        query_embedding: list[float],
        top_k: int | None = None,
        category: str | None = None,
    ) -> list[RetrievedChunk]:
        limit = top_k or settings.RAG_TOP_K_DENSE
        distance_expr = DocumentChunk.embedding.cosine_distance(query_embedding)
        similarity_expr = (1.0 - distance_expr).label("dense_score")

        stmt = (
            select(
                DocumentChunk,
                KnowledgeDocument.title,
                KnowledgeDocument.category,
                KnowledgeSource.source_key,
                similarity_expr,
            )
            .join(KnowledgeDocument, DocumentChunk.document_id == KnowledgeDocument.id)
            .join(KnowledgeSource, KnowledgeDocument.source_id == KnowledgeSource.id)
            .where(
                KnowledgeDocument.is_active.is_(True),
                KnowledgeSource.status == "active",
            )
            .order_by(distance_expr.asc())
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
                    dense_score=round(float(score), 6),
                    dense_rank=rank,
                    metadata=meta,
                )
            )
        return results
