"""arXiv ingestion helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from ..models import Document, Source, SourceRecord
from ..utils.checksums import sha256_text
from ..utils.text_cleaning import clean_text
from .base import BaseSource


class ArxivSource(BaseSource):
    """Parses arXiv search feeds for AI-safety related content."""

    name = "arxiv"

    def build_source(self) -> Source:
        return Source(
            id="source_arxiv_alignment",
            name="arXiv AI Safety Feed",
            kind="website",
            canonical_url="https://arxiv.org",
            ingestion_mode="poll",
            metadata={"query": "AI safety"},
        )

    async def discover(self, limit: int | None = None) -> List[SourceRecord]:
        records = [
            SourceRecord(
                id="arxiv_demo",
                source=self.name,
                external_id="2301.00001",
                last_fetched_at=datetime.now(timezone.utc),
                status="parsed",
            )
        ]
        return records[: limit or len(records)]

    async def fetch_document(self, record: SourceRecord) -> Document:
        text = "Paper abstract describing scalable oversight and evaluation protocols."
        return Document(
            id=f"doc_{record.external_id}",
            external_id=record.external_id,
            source=self.name,
            source_id=self.registry_source.id,
            title="Scalable Oversight Evaluations",
            authors=["Researcher One", "Researcher Two"],
            published_at=record.last_fetched_at,
            added_at=datetime.now(timezone.utc),
            abstract=text,
            text=clean_text(text),
            raw_uri=f"https://arxiv.org/abs/{record.external_id}",
            checksum=sha256_text(text),
            topics=["evals", "oversight"],
            risk_areas=["robustness"],
            tags=["arxiv"],
            metadata={"arxiv_category": "cs.AI"},
            version=1,
        )

