"""Persistence helpers wrapping SQLAlchemy for async workflows."""

from __future__ import annotations

import argparse
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncIterator, List, Sequence

from sqlalchemy import delete, select, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .config import Settings, get_settings
from .models import Chunk, Document, SearchFilters, Source
from .schemas import Base, ChunkORM, DocumentORM, SourceORM


class StorageError(RuntimeError):
    """Base storage exception."""


class SQLAlchemyStore:
    """Async SQLAlchemy-based store for documents and chunks."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.engine = create_async_engine(self.settings.database_url, future=True)
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False)

    async def init_db(self) -> None:
        """Create tables if they do not exist."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        async with self.session_factory() as sess:
            yield sess

    async def upsert_document(self, document: Document, chunks: Sequence[Chunk]) -> None:
        """Insert or update a document and replace its chunks."""
        async with self.session() as sess:
            existing = await sess.get(DocumentORM, document.id)
            if existing:
                await self._update_document(existing, document)
                await sess.flush()
                await sess.execute(delete(ChunkORM).where(ChunkORM.doc_id == document.id))
            else:
                sess.add(self._document_to_orm(document))
                await sess.flush()
            for chunk in chunks:
                sess.add(self._chunk_to_orm(chunk))
            await sess.flush()
            await self._refresh_source_doc_count(sess, document.source_id)
            await sess.commit()

    async def upsert_source(self, source: Source) -> None:
        """Create or update a source registry entry."""
        async with self.session() as sess:
            existing = await sess.get(SourceORM, source.id)
            if existing:
                self._update_source(existing, source)
            else:
                sess.add(self._source_to_orm(source))
            await sess.commit()

    async def record_ingestion_status(
        self, source_id: str, status: str, error: str | None = None
    ) -> None:
        """Update ingestion status metadata for a source."""
        async with self.session() as sess:
            source = await sess.get(SourceORM, source_id)
            if not source:
                return
            source.last_ingested_at = datetime.now(timezone.utc)
            source.last_ingestion_status = status
            source.last_error_message = error
            await sess.commit()

    async def list_sources(self) -> List[Source]:
        async with self.session() as sess:
            stmt = select(SourceORM).order_by(SourceORM.name.asc())
            result = await sess.execute(stmt)
            return [row[0].to_source() for row in result.fetchall()]

    async def find_sources_by_url(self, url: str) -> List[Source]:
        async with self.session() as sess:
            stmt = select(SourceORM).where(SourceORM.canonical_url == url)
            result = await sess.execute(stmt)
            return [row[0].to_source() for row in result.fetchall()]

    async def delete_sources_by_ids(self, source_ids: Sequence[str]) -> None:
        if not source_ids:
            return
        async with self.session() as sess:
            await sess.execute(delete(SourceORM).where(SourceORM.id.in_(list(source_ids))))
            await sess.commit()

    async def get_source(self, source_id: str) -> Source | None:
        async with self.session() as sess:
            instance = await sess.get(SourceORM, source_id)
            return instance.to_source() if instance else None

    async def get_document(self, doc_id: str) -> Document | None:
        async with self.session() as sess:
            instance = await sess.get(DocumentORM, doc_id)
            return instance.to_document() if instance else None

    async def get_chunks_for_document(self, doc_id: str) -> List[Chunk]:
        async with self.session() as sess:
            stmt = select(ChunkORM).where(ChunkORM.doc_id == doc_id).order_by(ChunkORM.chunk_index)
            result = await sess.execute(stmt)
            return [row[0].to_chunk() for row in result.fetchall()]

    async def list_topics(self) -> List[str]:
        async with self.session() as sess:
            stmt = select(DocumentORM.topics)
            result = await sess.execute(stmt)
            topics: set[str] = set()
            for row in result.scalars().all():
                topics.update(row or [])
            return sorted(topics)

    async def fetch_candidate_chunks(
        self, filters: SearchFilters | None, limit: int
    ) -> List[tuple[Chunk, Document]]:
        filters = filters or SearchFilters()
        async with self.session() as sess:
            stmt = (
                select(ChunkORM, DocumentORM)
                .join(DocumentORM, ChunkORM.doc_id == DocumentORM.id)
                .order_by(ChunkORM.created_at.desc())
                .limit(limit)
            )

            if filters.topics:
                stmt = stmt.where(ChunkORM.topics.contains(filters.topics))
            if filters.sources:
                stmt = stmt.where(DocumentORM.source.in_(filters.sources))
            if filters.risk_areas:
                stmt = stmt.where(ChunkORM.risk_areas.contains(filters.risk_areas))
            if filters.year_min:
                stmt = stmt.where(
                    DocumentORM.published_at
                    >= datetime(filters.year_min, 1, 1, tzinfo=timezone.utc)
                )
            if filters.year_max:
                stmt = stmt.where(
                    DocumentORM.published_at
                    <= datetime(filters.year_max, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
                )

            results = await sess.execute(stmt)
            pairs: List[tuple[Chunk, Document]] = []
            for chunk_orm, doc_orm in results.fetchall():
                doc = doc_orm.to_document()
                chunk = chunk_orm.to_chunk()
                if filters.metadata:
                    skip = False
                    for key, value in filters.metadata.items():
                        if doc.metadata.get(key) != value:
                            skip = True
                            break
                    if skip:
                        continue
                pairs.append((chunk, doc))
            return pairs

    def _document_to_orm(self, document: Document) -> DocumentORM:
        return DocumentORM(
            id=document.id,
            external_id=document.external_id,
            source=document.source,
            source_id=document.source_id,
            title=document.title,
            url=document.url,
            authors=document.authors,
            published_at=document.published_at,
            added_at=document.added_at,
            abstract=document.abstract,
            text=document.text,
            raw_uri=document.raw_uri,
            checksum=document.checksum,
            topics=document.topics,
            risk_areas=document.risk_areas,
            tags=document.tags,
            extra_metadata=document.metadata,
            version=document.version,
        )

    def _chunk_to_orm(self, chunk: Chunk) -> ChunkORM:
        return ChunkORM(
            id=chunk.id,
            doc_id=chunk.doc_id,
            chunk_index=chunk.chunk_index,
            text=chunk.text,
            embedding=chunk.embedding,
            topics=chunk.topics,
            risk_areas=chunk.risk_areas,
            extra_metadata=chunk.metadata,
        )

    async def _update_document(self, orm: DocumentORM, document: Document) -> None:
        orm.external_id = document.external_id
        orm.source = document.source
        orm.source_id = document.source_id
        orm.title = document.title
        orm.url = document.url
        orm.authors = document.authors
        orm.published_at = document.published_at
        orm.abstract = document.abstract
        orm.text = document.text
        orm.raw_uri = document.raw_uri
        orm.checksum = document.checksum
        orm.topics = document.topics
        orm.risk_areas = document.risk_areas
        orm.tags = document.tags
        orm.extra_metadata = document.metadata
        orm.version = document.version

    def _source_to_orm(self, source: Source) -> SourceORM:
        return SourceORM(
            id=source.id,
            name=source.name,
            kind=source.kind,
            canonical_url=source.canonical_url,
            ingestion_mode=source.ingestion_mode,
            is_active=source.is_active,
            last_ingested_at=source.last_ingested_at,
            last_ingestion_status=source.last_ingestion_status,
            last_error_message=source.last_error_message,
            doc_count=source.doc_count,
            metadata_json=source.metadata,
        )

    def _update_source(self, orm: SourceORM, source: Source) -> None:
        orm.name = source.name
        orm.kind = source.kind
        orm.canonical_url = source.canonical_url
        orm.ingestion_mode = source.ingestion_mode
        orm.is_active = source.is_active
        orm.metadata_json = source.metadata

    async def _refresh_source_doc_count(self, sess: AsyncSession, source_id: str) -> None:
        count_stmt = select(func.count()).select_from(DocumentORM).where(
            DocumentORM.source_id == source_id
        )
        count = await sess.scalar(count_stmt)
        source = await sess.get(SourceORM, source_id)
        if source:
            source.doc_count = int(count or 0)


async def _cli_init_db(settings: Settings) -> None:
    store = SQLAlchemyStore(settings=settings)
    await store.init_db()
    print(f"Initialized database at {settings.database_url}")


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Safety KB storage utilities")
    parser.add_argument("--init-db", action="store_true", help="Create database tables")
    return parser


def main() -> None:
    parser = _build_arg_parser()
    args = parser.parse_args()
    settings = get_settings()
    if args.init_db:
        asyncio.run(_cli_init_db(settings))


if __name__ == "__main__":  # pragma: no cover - CLI helper
    main()

