import pytest

from safety_kb.catalog import render_catalog_markdown
from safety_kb.storage import SQLAlchemyStore

UNIT_TEST_SOURCE_ID = "source_unit_test"


@pytest.mark.asyncio
async def test_source_registry_updates(store: SQLAlchemyStore):
    sources = await store.list_sources()
    assert any(src.id == UNIT_TEST_SOURCE_ID for src in sources)

    await store.record_ingestion_status(UNIT_TEST_SOURCE_ID, "success")
    updated = await store.get_source(UNIT_TEST_SOURCE_ID)
    assert updated is not None
    assert updated.last_ingestion_status == "success"


@pytest.mark.asyncio
async def test_catalog_render(tmp_path, store: SQLAlchemyStore):
    markdown = await render_catalog_markdown(store)
    assert "Unit Test Corpus" in markdown
    output_path = tmp_path / "sources.md"
    output_path.write_text(markdown, encoding="utf-8")
    assert output_path.exists()

