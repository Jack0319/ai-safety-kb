"""Chunking utilities for converting documents into retrieval units."""

from __future__ import annotations

from typing import Iterable, List

from ..config import Settings, get_settings
from ..models import Chunk, Document
from .text_cleaning import clean_text


def chunk_text(
    text: str,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> List[str]:
    """Split text into overlapping token windows."""
    settings = get_settings()
    chunk_size = chunk_size or settings.chunk_size
    chunk_overlap = chunk_overlap or settings.chunk_overlap

    words = text.split()
    if not words:
        return []

    chunks: List[str] = []
    start = 0
    step = max(chunk_size - chunk_overlap, 1)
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk_words = words[start:end]
        chunks.append(" ".join(chunk_words))
        start += step
    return chunks


def build_chunks(document: Document, settings: Settings | None = None) -> List[Chunk]:
    """Clean text and generate Chunk models."""
    settings = settings or get_settings()
    if not document.text:
        return []

    normalized = clean_text(document.text)
    body_chunks = chunk_text(
        normalized,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )

    chunks: List[Chunk] = []
    for idx, body in enumerate(body_chunks):
        chunks.append(
            Chunk(
                id=f"{document.id}_{idx}",
                doc_id=document.id,
                chunk_index=idx,
                text=body,
                topics=document.topics,
                risk_areas=document.risk_areas,
                metadata={"source": document.source, **document.metadata},
            )
        )
    return chunks

