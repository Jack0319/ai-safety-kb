"""SQLAlchemy ORM models backing the knowledge base."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from .models import Chunk, Document, Source, SourceRecord


class Base(DeclarativeBase):
    """Declarative base that other ORM models extend."""


class SourceORM(Base):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    canonical_url: Mapped[str] = mapped_column(Text, nullable=False)
    ingestion_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_ingested_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_ingestion_status: Mapped[Optional[str]] = mapped_column(String(32))
    last_error_message: Mapped[Optional[str]] = mapped_column(Text)
    doc_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    metadata_json: Mapped[Dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    documents: Mapped[List["DocumentORM"]] = relationship(
        "DocumentORM", back_populates="source_ref", cascade="all, delete-orphan"
    )

    def to_source(self) -> Source:
        return Source(
            id=self.id,
            name=self.name,
            kind=self.kind,
            canonical_url=self.canonical_url,
            ingestion_mode=self.ingestion_mode,
            is_active=self.is_active,
            last_ingested_at=self.last_ingested_at,
            last_ingestion_status=self.last_ingestion_status,
            last_error_message=self.last_error_message,
            doc_count=self.doc_count,
            metadata=self.metadata_json or {},
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class DocumentORM(Base):
    __tablename__ = "documents"
    __table_args__ = (
        Index("idx_documents_source", "source"),
        Index("idx_documents_published_at", "published_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    external_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    source_id: Mapped[str] = mapped_column(
        ForeignKey("sources.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    authors: Mapped[List[str]] = mapped_column(JSON, default=list)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    abstract: Mapped[Optional[str]] = mapped_column(Text)
    text: Mapped[Optional[str]] = mapped_column(Text)
    raw_uri: Mapped[Optional[str]] = mapped_column(Text)
    checksum: Mapped[Optional[str]] = mapped_column(String(128))
    topics: Mapped[List[str]] = mapped_column(JSON, default=list)
    risk_areas: Mapped[List[str]] = mapped_column(JSON, default=list)
    tags: Mapped[List[str]] = mapped_column(JSON, default=list)
    extra_metadata: Mapped[Dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    chunks: Mapped[List["ChunkORM"]] = relationship(
        "ChunkORM", back_populates="document", cascade="all, delete-orphan"
    )
    source_ref: Mapped[SourceORM] = relationship("SourceORM", back_populates="documents")

    def to_document(self) -> Document:
        return Document(
            id=self.id,
            external_id=self.external_id,
            source=self.source,
            source_id=self.source_id,
            title=self.title,
            url=self.url,
            authors=self.authors or [],
            published_at=self.published_at,
            added_at=self.added_at,
            abstract=self.abstract,
            text=self.text,
            raw_uri=self.raw_uri,
            checksum=self.checksum,
            topics=self.topics or [],
            risk_areas=self.risk_areas or [],
            tags=self.tags or [],
            metadata=self.extra_metadata or {},
            version=self.version,
        )


class ChunkORM(Base):
    __tablename__ = "chunks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    doc_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Optional[List[float]]] = mapped_column(JSON, nullable=True)
    topics: Mapped[List[str]] = mapped_column(JSON, default=list)
    risk_areas: Mapped[List[str]] = mapped_column(JSON, default=list)
    extra_metadata: Mapped[Dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    document: Mapped[DocumentORM] = relationship("DocumentORM", back_populates="chunks")

    __table_args__ = (Index("idx_chunks_doc_id", "doc_id"),)

    def to_chunk(self) -> Chunk:
        return Chunk(
            id=self.id,
            doc_id=self.doc_id,
            chunk_index=self.chunk_index,
            text=self.text,
            embedding=self.embedding,
            topics=self.topics or [],
            risk_areas=self.risk_areas or [],
            metadata=self.extra_metadata or {},
        )


class SourceRecordORM(Base):
    __tablename__ = "source_records"
    __table_args__ = (
        Index("idx_source_records_unique_source", "source", "external_id", unique=True),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    last_fetched_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    doc_id: Mapped[Optional[str]] = mapped_column(ForeignKey("documents.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="new", nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    def to_source_record(self) -> SourceRecord:
        return SourceRecord(
            id=self.id,
            source=self.source,
            external_id=self.external_id,
            last_fetched_at=self.last_fetched_at,
            doc_id=self.doc_id,
            status=self.status,
            error_message=self.error_message,
        )


def document_from_dict(payload: Dict[str, Any]) -> DocumentORM:
    """Helper used by ingestion to create ORM entities from plain dicts."""
    return DocumentORM(**payload)

