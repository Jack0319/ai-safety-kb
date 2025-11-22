"""Sync sources based on catalog entries and local files."""

from __future__ import annotations

import argparse
import asyncio
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Sequence

import httpx
from PyPDF2 import PdfReader

from .catalog import render_catalog_markdown
from .config import Settings, get_settings
from .models import Document, Source
from .storage import SQLAlchemyStore
from .utils.checksums import sha256_file, sha256_text
from .utils.chunking import build_chunks
from .utils.text_cleaning import clean_text

CATALOG_LINK_RE = re.compile(r"\[(?:[^\]]*)\]\(([^)]+)\)")
DEFAULT_SOURCES_DIR = Path("sources/files")
ALLOWED_SUFFIXES = {".txt", ".md", ".html", ".htm", ".pdf"}


@dataclass
class CatalogEntry:
    name: str
    kind: str
    ingestion_mode: str
    url: str

    @property
    def slug(self) -> str:
        return slugify(self.name)


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", name.strip().lower()).strip("-")
    return slug or "source"


def parse_catalog_entries(markdown: str) -> List[CatalogEntry]:
    entries: List[CatalogEntry] = []
    for line in markdown.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        parts = [part.strip() for part in line.split("|")[1:-1]]
        if len(parts) < 7:
            continue
        if parts[0].startswith("---"):
            continue
        link_cell = parts[6]
        match = CATALOG_LINK_RE.search(link_cell)
        if not match:
            continue
        entries.append(
            CatalogEntry(
                name=parts[0],
                kind=parts[1],
                ingestion_mode=parts[2],
                url=match.group(1),
            )
        )
    return entries


async def fetch_url_text(url: str) -> str:
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.text


async def ingest_catalog_links(
    entries: Sequence[CatalogEntry],
    store: SQLAlchemyStore,
) -> None:
    for entry in entries:
        source = Source(
            id=f"source_{entry.slug}",
            name=entry.name,
            kind=entry.kind,
            canonical_url=entry.url,
            ingestion_mode=entry.ingestion_mode,
        )
        await store.upsert_source(source)
        if entry.kind.lower() != "website":
            continue
        try:
            raw_html = await fetch_url_text(entry.url)
        except Exception as exc:  # pragma: no cover - network failure
            await store.record_ingestion_status(source.id, "failed", str(exc))
            continue

        text = clean_text(raw_html)
        if not text:
            await store.record_ingestion_status(source.id, "failed", "Empty response")
            continue

        checksum = sha256_text(text)
        document = Document(
            id=f"{source.id}_{checksum[:12]}",
            external_id=entry.url,
            source=source.id,
            source_id=source.id,
            title=entry.name,
            url=entry.url,
            added_at=datetime.now(timezone.utc),
            abstract=text[:400],
            text=text,
            raw_uri=entry.url,
            checksum=checksum,
            version=1,
            metadata={"source_type": "catalog_link"},
        )
        chunks = build_chunks(document)
        await store.upsert_document(document, chunks)
        await store.record_ingestion_status(source.id, "success")


def discover_local_files(sources_dir: Path) -> List[Path]:
    if not sources_dir.exists():
        return []
    return [
        path
        for path in sources_dir.iterdir()
        if path.is_file() and path.suffix.lower() in ALLOWED_SUFFIXES
    ]


def read_local_file_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        reader = PdfReader(str(path))
        text = "".join(filter(None, (page.extract_text() for page in reader.pages)))
    else:
        text = path.read_text(encoding="utf-8", errors="ignore")
    return clean_text(text)


async def ingest_local_files(
    files: Sequence[Path],
    store: SQLAlchemyStore,
) -> None:
    for path in files:
        relative_uri = path.as_posix()
        name = path.stem
        slug = slugify(name)
        source = Source(
            id=f"source_file_{slug}",
            name=name,
            kind="file",
            canonical_url=f"./{relative_uri}",
            ingestion_mode="snapshot",
        )
        await store.upsert_source(source)
        try:
            text = read_local_file_text(path)
        except Exception as exc:  # pragma: no cover - decoding errors, corrupt files
            await store.record_ingestion_status(source.id, "failed", str(exc))
            continue
        if not text:
            await store.record_ingestion_status(source.id, "failed", "Empty file content")
            continue
        checksum = sha256_file(path)
        document = Document(
            id=f"{source.id}_{checksum[:12]}",
            external_id=path.name,
            source=source.id,
            source_id=source.id,
            title=name,
            url=None,
            added_at=datetime.now(timezone.utc),
            abstract=text[:400],
            text=text,
            raw_uri=relative_uri,
            checksum=checksum,
            version=1,
            metadata={"local_path": relative_uri},
        )
        chunks = build_chunks(document)
        await store.upsert_document(document, chunks)
        await store.record_ingestion_status(source.id, "success")


async def sync_catalog(
    catalog_path: Path | str = "sources_catalog.md",
    sources_dir: Path | str = DEFAULT_SOURCES_DIR,
    settings: Settings | None = None,
) -> Path:
    settings = settings or get_settings()
    store = SQLAlchemyStore(settings=settings)
    catalog_path = Path(catalog_path)
    markdown = catalog_path.read_text(encoding="utf-8") if catalog_path.exists() else ""
    entries = parse_catalog_entries(markdown)
    await ingest_catalog_links(entries, store)
    files = discover_local_files(Path(sources_dir))
    await ingest_local_files(files, store)
    rendered = await render_catalog_markdown(store)
    catalog_path.write_text(rendered, encoding="utf-8")
    return catalog_path


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Sync catalog entries and local files into the knowledge base."
    )
    parser.add_argument(
        "--catalog",
        default="sources_catalog.md",
        help="Path to the catalog markdown file.",
    )
    parser.add_argument(
        "--sources-dir",
        default=str(DEFAULT_SOURCES_DIR),
        help="Directory containing local files to ingest.",
    )
    return parser


def main() -> None:
    parser = _build_arg_parser()
    args = parser.parse_args()
    asyncio.run(sync_catalog(catalog_path=args.catalog, sources_dir=args.sources_dir))


if __name__ == "__main__":  # pragma: no cover - CLI helper
    main()

