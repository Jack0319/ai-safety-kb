from datetime import datetime, timezone

import pytest
import pytest_asyncio

from safety_kb.config import Settings
from safety_kb.models import Document, Source
from safety_kb.storage import SQLAlchemyStore

UNIT_TEST_SOURCE_ID = "source_unit_test"


@pytest.fixture()
def test_settings(tmp_path):
    db_path = tmp_path / "kb.db"
    return Settings(
        database_url=f"sqlite+aiosqlite:///{db_path}",
        embedding_provider="fake",
        embedding_dim=32,
        chunk_size=64,
        chunk_overlap=16,
        max_candidate_chunks=50,
    )


@pytest_asyncio.fixture()
async def store(test_settings):
    kb_store = SQLAlchemyStore(settings=test_settings)
    await kb_store.init_db()
    await kb_store.upsert_source(
        Source(
            id=UNIT_TEST_SOURCE_ID,
            name="Unit Test Corpus",
            kind="repo",
            canonical_url="https://example.com/corpus",
            ingestion_mode="manual",
        )
    )
    return kb_store


@pytest.fixture()
def demo_document():
    return Document(
        id="doc_demo",
        external_id="demo",
        source="unit_test",
        source_id=UNIT_TEST_SOURCE_ID,
        title="Testing Oversight",
        url="https://example.com/demo",
        authors=["Tester"],
        published_at=datetime.now(timezone.utc),
        added_at=datetime.now(timezone.utc),
        abstract="Demo",
        text="Alignment oversight helps detect deception in AI systems.",
        raw_uri="https://example.com/demo.pdf",
        checksum="demo_checksum",
        topics=["alignment"],
        risk_areas=["alignment"],
        tags=["test"],
        metadata={"scope": "demo"},
        version=1,
    )

