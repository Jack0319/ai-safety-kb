"""Pydantic representations of KB entities."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class Document(BaseModel):
    """Logical representation of an ingested document or post."""

    model_config = ConfigDict(extra="ignore")

    id: str
    external_id: Optional[str] = None
    source: str
    source_id: str
    title: str
    url: Optional[str] = None
    authors: List[str] = Field(default_factory=list)
    published_at: Optional[datetime] = None
    added_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    abstract: Optional[str] = None
    text: Optional[str] = None
    raw_uri: Optional[str] = None
    checksum: Optional[str] = None
    topics: List[str] = Field(default_factory=list)
    risk_areas: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    version: int = 1


class Chunk(BaseModel):
    """Minimal retrieval unit referencing a document."""

    model_config = ConfigDict(extra="ignore")

    id: str
    doc_id: str
    chunk_index: int
    text: str
    embedding: Optional[List[float]] = None
    topics: List[str] = Field(default_factory=list)
    risk_areas: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SourceRecord(BaseModel):
    """Tracks ingestion provenance."""

    model_config = ConfigDict(extra="ignore")

    id: str
    source: str
    external_id: str
    last_fetched_at: Optional[datetime] = None
    doc_id: Optional[str] = None
    status: str = "new"
    error_message: Optional[str] = None


class SearchResult(BaseModel):
    """Chunk-level search hit aggregated to doc-level context."""

    doc_id: str
    title: str
    url: Optional[str]
    snippet: str
    score: float
    source: str
    topics: List[str]
    risk_areas: List[str]
    metadata: Dict[str, Any]


class SearchFilters(BaseModel):
    """Supported filters for structured queries."""

    model_config = ConfigDict(extra="ignore")

    topics: Optional[List[str]] = None
    sources: Optional[List[str]] = None
    risk_areas: Optional[List[str]] = None
    year_min: Optional[int] = None
    year_max: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Source(BaseModel):
    """Registry entry describing a canonical data source."""

    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    kind: str
    canonical_url: str
    ingestion_mode: str
    is_active: bool = True
    last_ingested_at: Optional[datetime] = None
    last_ingestion_status: Optional[str] = None
    last_error_message: Optional[str] = None
    doc_count: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

