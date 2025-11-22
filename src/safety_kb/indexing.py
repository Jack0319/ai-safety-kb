"""High-level ingestion and indexing helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, Sequence

from .config import Settings, get_settings
from .models import Document
from .sources.base import BaseSource
from .storage import SQLAlchemyStore
from .utils.chunking import build_chunks
from .utils.embedding import get_embedding_provider


async def ingest_source(
    source: BaseSource,
    store: SQLAlchemyStore | None = None,
    limit: int | None = None,
    settings: Settings | None = None,
) -> int:
    """Fetch new records from a source and index them."""
    settings = settings or get_settings()
    store = store or SQLAlchemyStore(settings=settings)
    provider = get_embedding_provider(settings)
    await store.upsert_source(source.registry_source)
    db_source = await store.get_source(source.registry_source.id)
    if db_source and not db_source.is_active:
        return 0

    records = await source.discover(limit=limit or settings.fetch_batch_size)
    processed = 0
    status = "pending"
    error_message: str | None = None
    try:
        for record in records:
            document = await source.fetch_document(record)
            if not document.added_at:
                document.added_at = datetime.now(timezone.utc)
            chunks = build_chunks(document, settings=settings)
            if not chunks:
                continue
            embeddings = await provider.embed([chunk.text for chunk in chunks])
            for chunk, vector in zip(chunks, embeddings):
                chunk.embedding = vector
            await store.upsert_document(document, chunks)
            processed += 1
        status = "success"
    except Exception as exc:  # pragma: no cover - surfaced to orchestrator
        status = "failed"
        error_message = str(exc)
        raise
    finally:
        await store.record_ingestion_status(
            source.registry_source.id, status, error=error_message
        )
    return processed


async def ingest_documents(
    documents: Iterable[Document],
    store: SQLAlchemyStore | None = None,
    settings: Settings | None = None,
) -> int:
    """Ingest already materialized documents."""
    settings = settings or get_settings()
    store = store or SQLAlchemyStore(settings=settings)
    provider = get_embedding_provider(settings)
    processed = 0
    for document in documents:
        if not document.added_at:
            document.added_at = datetime.now(timezone.utc)
        chunks = build_chunks(document, settings=settings)
        if not chunks:
            continue
        embeddings = await provider.embed([chunk.text for chunk in chunks])
        for chunk, vector in zip(chunks, embeddings):
            chunk.embedding = vector
        await store.upsert_document(document, chunks)
        processed += 1
    return processed

