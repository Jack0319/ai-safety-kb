import asyncio
from pathlib import Path

import pytest

from safety_kb.catalog_sync import parse_catalog_entries, sync_catalog
from safety_kb.storage import SQLAlchemyStore

CATALOG_MD = """# Knowledge Base Sources

| Source | Kind | Status | Docs | Last Ingested | Link |
| --- | --- | --- | --- | --- | --- |
| Example Site | website | • | 0 | | [Example](https://example.com) |
"""


@pytest.mark.asyncio
async def test_parse_catalog_entries_basic():
    entries = parse_catalog_entries(CATALOG_MD)
    assert len(entries) == 1
    entry = entries[0]
    assert entry.name == "Example Site"
    assert entry.kind == "website"
    assert entry.url == "https://example.com"


@pytest.mark.asyncio
async def test_sync_catalog_with_local_file(tmp_path, monkeypatch, store, test_settings):
    catalog_path = tmp_path / "sources_catalog.md"
    catalog_path.write_text(CATALOG_MD, encoding="utf-8")

    sources_dir = tmp_path / "sources" / "files"
    sources_dir.mkdir(parents=True)
    local_file = sources_dir / "demo.txt"
    local_file.write_text("Local document content.", encoding="utf-8")
    pdf_file = sources_dir / "paper.pdf"
    pdf_file.write_bytes(b"%PDF-1.4\n%\xE2\xE3\xCF\xD3")  # minimal stub; text via patch

    async def fake_fetch(url: str) -> str:
        return "<html><body>Website content</body></html>"

    from safety_kb import catalog_sync

    monkeypatch.setattr(catalog_sync, "fetch_url_text", fake_fetch)

    original_read = catalog_sync.read_local_file_text

    def fake_read(path: Path) -> str:
        if path == pdf_file:
            return "PDF content extracted."
        return original_read(path)

    monkeypatch.setattr(catalog_sync, "read_local_file_text", fake_read)

    await sync_catalog(
        catalog_path=catalog_path,
        sources_dir=sources_dir,
        settings=test_settings,
    )

    markdown = catalog_path.read_text(encoding="utf-8")
    assert "Example Site" in markdown
    assert "demo" in markdown
    assert "paper" in markdown

    sources = await store.list_sources()
    names = {src.name for src in sources}
    assert "Example Site" in names
    assert "demo" in names
    assert "paper" in names

    # introduce a duplicate catalog row and resync to ensure deduplication
    markdown += "| Sleeper Agents | file | • | 0 |  | [link](./sources/files/Sleeper%20Agents.pdf) |\n"
    catalog_path.write_text(markdown, encoding="utf-8")
    await sync_catalog(
        catalog_path=catalog_path,
        sources_dir=sources_dir,
        settings=test_settings,
    )
    markdown = catalog_path.read_text(encoding="utf-8")
    assert markdown.count("Sleeper Agents") == 1

