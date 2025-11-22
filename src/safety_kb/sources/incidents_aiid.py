"""AI Incident Database ingestion."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from ..models import Document, Source, SourceRecord
from ..utils.checksums import sha256_text
from ..utils.text_cleaning import clean_text
from .base import BaseSource


class AIIncidentSource(BaseSource):
    """Fetches cases from the Partnership on AI AIID dataset."""

    name = "ai_incidents"

    def build_source(self) -> Source:
        return Source(
            id="source_ai_incidents",
            name="AI Incident Database",
            kind="website",
            canonical_url="https://incidentdatabase.ai",
            ingestion_mode="poll",
        )

    async def discover(self, limit: int | None = None) -> List[SourceRecord]:
        records = [
            SourceRecord(
                id="aiid_demo",
                source=self.name,
                external_id="incident-demo",
                last_fetched_at=datetime.now(timezone.utc),
                status="parsed",
            )
        ]
        return records[: limit or len(records)]

    async def fetch_document(self, record: SourceRecord) -> Document:
        summary = "Incident involving model hallucination that bypassed guardrails."
        return Document(
            id=f"doc_{record.external_id}",
            external_id=record.external_id,
            source=self.name,
            source_id=self.registry_source.id,
            title="Demo Incident",
            authors=["Incident Reporter"],
            published_at=record.last_fetched_at,
            added_at=datetime.now(timezone.utc),
            abstract=summary,
            text=clean_text(summary),
            raw_uri=f"https://incidentdatabase.ai/cases/{record.external_id}",
            checksum=sha256_text(summary),
            topics=["incidents", "monitoring"],
            risk_areas=["governance", "robustness"],
            tags=["incident"],
            metadata={"severity": "medium"},
            version=1,
        )

