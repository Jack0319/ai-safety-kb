"""Governance and policy ingestion."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from ..models import Document, Source, SourceRecord
from ..utils.checksums import sha256_text
from ..utils.text_cleaning import clean_text
from .base import BaseSource


class GovernanceSource(BaseSource):
    """Ingests regulatory and standards documents."""

    name = "governance"

    def build_source(self) -> Source:
        return Source(
            id="source_governance_reports",
            name="Global Governance Reports",
            kind="pdf",
            canonical_url="https://example.org/governance",
            ingestion_mode="manual",
        )

    async def discover(self, limit: int | None = None) -> List[SourceRecord]:
        records = [
            SourceRecord(
                id="governance_demo",
                source=self.name,
                external_id="policy-001",
                last_fetched_at=datetime.now(timezone.utc),
                status="parsed",
            )
        ]
        return records[: limit or len(records)]

    async def fetch_document(self, record: SourceRecord) -> Document:
        text = "Governance blueprint outlining evaluation and disclosure requirements."
        return Document(
            id=f"doc_{record.external_id}",
            external_id=record.external_id,
            source=self.name,
            source_id=self.registry_source.id,
            title="Safety Governance Blueprint",
            authors=["Policy Working Group"],
            published_at=record.last_fetched_at,
            added_at=datetime.now(timezone.utc),
            abstract=text,
            text=clean_text(text),
            raw_uri=f"{self.registry_source.canonical_url}/{record.external_id}.pdf",
            checksum=sha256_text(text),
            topics=["governance", "policy"],
            risk_areas=["governance"],
            tags=["policy"],
            metadata={"jurisdiction": "global"},
            version=1,
        )

