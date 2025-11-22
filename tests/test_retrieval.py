import pytest

from safety_kb.indexing import ingest_documents
from safety_kb.retrieval import get_document, list_topics, search


@pytest.mark.asyncio
async def test_search_returns_results(store, test_settings, demo_document):
    await ingest_documents([demo_document], store=store, settings=test_settings)
    results = await search(
        query="detecting deception",
        k=3,
        filters={"topics": ["alignment"]},
        store=store,
        settings=test_settings,
    )
    assert results
    assert results[0].doc_id == demo_document.id


@pytest.mark.asyncio
async def test_get_document(store, test_settings, demo_document):
    await ingest_documents([demo_document], store=store, settings=test_settings)
    document = await get_document(demo_document.id, store=store, settings=test_settings)
    assert document is not None
    assert document.title == demo_document.title


@pytest.mark.asyncio
async def test_list_topics(store, test_settings, demo_document):
    await ingest_documents([demo_document], store=store, settings=test_settings)
    topics = await list_topics(store=store, settings=test_settings)
    assert "alignment" in topics

