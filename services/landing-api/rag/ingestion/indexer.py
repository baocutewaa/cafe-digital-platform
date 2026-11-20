from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.conversation import AnswerCache
from app.models.knowledge import DocumentChunk, KnowledgeDocument, KnowledgeSource
from rag.ingestion.chunker import TextChunk, chunk_document
from rag.ingestion.embedder import OllamaEmbedder
from rag.ingestion.loaders import LoadedDocument, load_knowledge_directory


@dataclass(slots=True)
class IngestionReport:
    total_files: int
    changed_files: int
    skipped_files: int
    total_chunks_written: int
    invalidated_cache_rows: int
    duration_seconds: float
    dry_run: bool = False


async def _find_active_hashes(session: AsyncSession) -> dict[str, tuple[KnowledgeSource, str]]:
    stmt = (
        select(KnowledgeSource, KnowledgeDocument.content_hash)
        .join(
            KnowledgeDocument,
            (KnowledgeDocument.source_id == KnowledgeSource.id)
            & (KnowledgeDocument.is_active.is_(True)),
        )
    )
    rows = (await session.execute(stmt)).all()
    return {source.source_key: (source, doc_hash) for source, doc_hash in rows}


async def ingest_knowledge_path(
    path: Path,
    database_url: str | None = None,
    embedder: OllamaEmbedder | None = None,
    force: bool = False,
    dry_run: bool = False,
    batch_size: int = 16,
) -> IngestionReport:
    t0 = time.perf_counter()
    docs = load_knowledge_directory(path)

    if dry_run:
        total_chunks = sum(len(chunk_document(doc)) for doc in docs)
        return IngestionReport(
            total_files=len(docs),
            changed_files=len(docs),
            skipped_files=0,
            total_chunks_written=total_chunks,
            invalidated_cache_rows=0,
            duration_seconds=round(time.perf_counter() - t0, 2),
            dry_run=True,
        )

    db_url = database_url or settings.MIGRATION_DATABASE_URL
    engine = create_async_engine(db_url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    client = embedder or OllamaEmbedder()

    try:
        async with session_factory() as session:
            existing = await _find_active_hashes(session)

        to_ingest: list[tuple[LoadedDocument, list[TextChunk], KnowledgeSource | None]] = []
        skipped = 0

        for doc in docs:
            entry = existing.get(doc.source_key)
            if not force and entry is not None:
                source_obj, active_hash = entry
                if source_obj.checksum == doc.content_hash and active_hash == doc.content_hash:
                    skipped += 1
                    continue
                to_ingest.append((doc, chunk_document(doc), source_obj))
            else:
                source_obj = entry[0] if entry else None
                to_ingest.append((doc, chunk_document(doc), source_obj))

        if not to_ingest:
            return IngestionReport(
                total_files=len(docs),
                changed_files=0,
                skipped_files=skipped,
                total_chunks_written=0,
                invalidated_cache_rows=0,
                duration_seconds=round(time.perf_counter() - t0, 2),
            )

        # Embed all chunks outside DB write lock, then persist atomically in 1 transaction
        flat_texts = [chunk.content for _, chunks, _ in to_ingest for chunk in chunks]
        flat_vectors = await client.embed_batch(flat_texts, batch_size=batch_size)

        offset = 0
        total_chunks_written = 0
        invalidated_cache_rows = 0

        async with session_factory() as session, session.begin():
            for doc, chunks, _ in to_ingest:
                source_row = (
                    await session.execute(
                        select(KnowledgeSource).where(KnowledgeSource.source_key == doc.source_key)
                    )
                ).scalar_one_or_none()

                if source_row is None:
                    new_version = 1
                    source_row = KnowledgeSource(
                        source_key=doc.source_key,
                        source_type="markdown",
                        title=doc.title,
                        checksum=doc.content_hash,
                        current_version=new_version,
                        status="active",
                    )
                    session.add(source_row)
                    await session.flush()
                else:
                    new_version = source_row.current_version + 1
                    source_row.title = doc.title
                    source_row.checksum = doc.content_hash
                    source_row.current_version = new_version
                    source_row.status = "active"

                await session.execute(
                    update(KnowledgeDocument)
                    .where(
                        KnowledgeDocument.doc_key == doc.doc_key,
                        KnowledgeDocument.is_active.is_(True),
                    )
                    .values(is_active=False)
                )

                new_doc = KnowledgeDocument(
                    source_id=source_row.id,
                    doc_key=doc.doc_key,
                    title=doc.title,
                    category=doc.category,
                    language=doc.language,
                    content=doc.clean_body,
                    metadata_=doc.metadata,
                    version=new_version,
                    content_hash=doc.content_hash,
                    is_active=True,
                )
                session.add(new_doc)
                await session.flush()

                for chunk in chunks:
                    vec = flat_vectors[offset]
                    offset += 1
                    session.add(
                        DocumentChunk(
                            document_id=new_doc.id,
                            chunk_index=chunk.chunk_index,
                            content=chunk.content,
                            search_text=chunk.search_text,
                            embedding=vec,
                            embedding_model=client.model,
                            token_count=chunk.token_count,
                            metadata_=chunk.metadata,
                        )
                    )
                    total_chunks_written += 1

            del_res = await session.execute(delete(AnswerCache))
            invalidated_cache_rows = int(del_res.rowcount or 0)

        return IngestionReport(
            total_files=len(docs),
            changed_files=len(to_ingest),
            skipped_files=skipped,
            total_chunks_written=total_chunks_written,
            invalidated_cache_rows=invalidated_cache_rows,
            duration_seconds=round(time.perf_counter() - t0, 2),
        )
    finally:
        await engine.dispose()
