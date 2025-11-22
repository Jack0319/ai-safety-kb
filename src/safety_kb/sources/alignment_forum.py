"""Alignment Forum ingestion routines."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from ..models import Document, Source, SourceRecord
from ..utils.checksums import sha256_text
from ..utils.text_cleaning import clean_text
from .base import BaseSource


class AlignmentForumSource(BaseSource):
    """Fetches posts via the Alignment Forum API."""

    name = "alignment_forum"

    def build_source(self) -> Source:
        return Source(
            id="source_alignment_forum",
            name="Alignment Forum",
            kind="website",
            canonical_url="https://www.alignmentforum.org",
            ingestion_mode="poll",
        )

    async def discover(self, limit: int | None = None) -> List[SourceRecord]:
        # Placeholder implementation - production version would hit the AF API.
        records = [
            SourceRecord(
                id="af_demo_post",
                source=self.name,
                external_id="demo-post",
                last_fetched_at=datetime.now(timezone.utc),
                status="parsed",
            )
        ]
        return records[: limit or len(records)]

    async def fetch_document(self, record: SourceRecord) -> Document:
        text = """Alignment research demo post describing oversight techniques."""
        return Document(
            id=f"doc_{record.external_id}",
            external_id=record.external_id,
            source=self.name,
            source_id=self.registry_source.id,
            title="Demo Alignment Forum Post",
            authors=["Demo Author"],
            published_at=record.last_fetched_at,
            added_at=datetime.now(timezone.utc),
            abstract=text,
            text=clean_text(text),
            raw_uri=self.registry_source.canonical_url,
            checksum=sha256_text(text),
            topics=["alignment", "oversight"],
            risk_areas=["alignment"],
            tags=["demo"],
            metadata={"community": "AF"},
            version=1,
        )

