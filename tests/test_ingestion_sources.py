import pytest

from safety_kb.sources.alignment_forum import AlignmentForumSource
from safety_kb.sources.arxiv_papers import ArxivSource
from safety_kb.sources.governance_docs import GovernanceSource
from safety_kb.sources.incidents_aiid import AIIncidentSource


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "source_cls",
    [AlignmentForumSource, ArxivSource, AIIncidentSource, GovernanceSource],
)
async def test_sources_return_documents(source_cls):
    source = source_cls()
    records = await source.discover(limit=1)
    assert records, "discover() should return at least one record"
    document = await source.fetch_document(records[0])
    assert document.id
    assert document.source == source.name
    assert document.text

