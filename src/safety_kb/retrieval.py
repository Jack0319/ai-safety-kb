"""Public retrieval API consumed by MCP tools."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

from .config import Settings, get_settings
from .models import Chunk, Document, SearchFilters, SearchResult
from .storage import SQLAlchemyStore
from .utils.embedding import cosine_similarity, get_embedding_provider


def _ensure_filters(filters: Optional[Dict[str, Any] | SearchFilters]) -> SearchFilters:
    if isinstance(filters, SearchFilters):
        return filters
    return SearchFilters(**(filters or {}))


async def search(
    query: str,
    k: int = 10,
    filters: Optional[Dict[str, Any]] = None,
    store: SQLAlchemyStore | None = None,
    settings: Settings | None = None,
) -> List[SearchResult]:
    """Semantic search over chunk embeddings with structured filters."""
    settings = settings or get_settings()
    store = store or SQLAlchemyStore(settings=settings)
    provider = get_embedding_provider(settings)
    query_vector = (await provider.embed([query]))[0]
    filter_model = _ensure_filters(filters)
    candidates = await store.fetch_candidate_chunks(
        filters=filter_model, limit=settings.max_candidate_chunks
    )

    scored: List[tuple[float, Chunk, Document]] = []
    for chunk, document in candidates:
        if not chunk.embedding:
            continue
        score = cosine_similarity(query_vector, chunk.embedding)
        if score <= 0:
            continue
        scored.append((score, chunk, document))

    scored.sort(key=lambda item: item[0], reverse=True)
    top_hits = scored[:k]
    results: List[SearchResult] = []
    for score, chunk, document in top_hits:
        snippet = chunk.text[:400]
        results.append(
            SearchResult(
                doc_id=document.id,
                title=document.title,
                url=document.url,
                snippet=snippet,
                score=score,
                source=document.source,
                topics=document.topics,
                risk_areas=document.risk_areas,
                metadata=document.metadata,
            )
        )
    return results


async def get_document(
    doc_id: str,
    store: SQLAlchemyStore | None = None,
    settings: Settings | None = None,
) -> Optional[Document]:
    """Return a single document by identifier."""
    settings = settings or get_settings()
    store = store or SQLAlchemyStore(settings=settings)
    return await store.get_document(doc_id)


async def get_chunks_for_document(
    doc_id: str,
    store: SQLAlchemyStore | None = None,
    settings: Settings | None = None,
) -> List[Chunk]:
    """Return all chunks for a document."""
    settings = settings or get_settings()
    store = store or SQLAlchemyStore(settings=settings)
    return await store.get_chunks_for_document(doc_id)


async def search_by_topic(
    topic: str,
    query: Optional[str] = None,
    k: int = 10,
    store: SQLAlchemyStore | None = None,
    settings: Settings | None = None,
) -> List[SearchResult]:
    """Search constrained to a single topic."""
    filters = {"topics": [topic]}
    if query:
        return await search(query=query, k=k, filters=filters, store=store, settings=settings)
    # No query: treat topic as query seed
    topic_query = f"Authoritative documents about {topic}"
    return await search(query=topic_query, k=k, filters=filters, store=store, settings=settings)


async def list_topics(
    store: SQLAlchemyStore | None = None,
    settings: Settings | None = None,
) -> List[str]:
    """List distinct topics currently stored."""
    settings = settings or get_settings()
    store = store or SQLAlchemyStore(settings=settings)
    return await store.list_topics()

