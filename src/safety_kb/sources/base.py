"""Abstract base class for ingestion sources."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable, List

from ..models import Document, Source, SourceRecord


class BaseSource(ABC):
    """Common interface for data sources."""

    name: str

    def __init__(self) -> None:
        if not getattr(self, "name", None):
            raise ValueError("Source classes must define `name`.")
        self._registry_source = self.build_source()

    @abstractmethod
    def build_source(self) -> Source:
        """Return the Source registry entry for this ingestion pipeline."""

    @property
    def registry_source(self) -> Source:
        return self._registry_source

    @abstractmethod
    async def discover(self, limit: int | None = None) -> List[SourceRecord]:
        """Return SourceRecords representing new or updated items."""

    @abstractmethod
    async def fetch_document(self, record: SourceRecord) -> Document:
        """Fetch and parse a document for a previously discovered record."""

