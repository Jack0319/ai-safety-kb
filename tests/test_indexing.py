import pytest

from safety_kb.indexing import ingest_documents
from safety_kb.retrieval import get_chunks_for_document


@pytest.mark.asyncio
async def test_ingest_documents(store, test_settings, demo_document):
    count = await ingest_documents([demo_document], store=store, settings=test_settings)
    assert count == 1
    chunks = await get_chunks_for_document(
        demo_document.id, store=store, settings=test_settings
    )
    assert chunks
    assert chunks[0].doc_id == demo_document.id

