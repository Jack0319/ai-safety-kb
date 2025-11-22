"""Utilities for generating a human-readable source catalog."""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Iterable, List

from .config import Settings, get_settings
from .models import Source
from .storage import SQLAlchemyStore

STATUS_EMOJI = {
    "success": "✅",
    "failed": "❌",
    "pending": "⏳",
    None: "•",
}


async def render_catalog_markdown(store: SQLAlchemyStore) -> str:
    """Return a markdown table describing all registered sources."""
    sources = await store.list_sources()
    if not sources:
        return "# Knowledge Base Sources\n\n_No sources registered yet._\n"

    lines: List[str] = [
        "# Knowledge Base Sources",
        "",
        "| Source | Kind | Mode | Status | Docs | Last Ingested | Link |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for source in sources:
        emoji = STATUS_EMOJI.get(source.last_ingestion_status, "•")
        last_ingested = (
            source.last_ingested_at.isoformat()
            if isinstance(source.last_ingested_at, datetime)
            else ""
        )
        lines.append(
            f"| {source.name} | {source.kind} | {source.ingestion_mode} | "
            f"{emoji} {source.last_ingestion_status or ''} | {source.doc_count} | "
            f"{last_ingested} | [link]({source.canonical_url}) |"
        )
    lines.append("")
    return "\n".join(lines)


async def generate_catalog_file(
    output_path: str = "sources_catalog.md", settings: Settings | None = None
) -> Path:
    """Generate the catalog markdown file."""
    settings = settings or get_settings()
    store = SQLAlchemyStore(settings=settings)
    markdown = await render_catalog_markdown(store)
    path = Path(output_path)
    path.write_text(markdown, encoding="utf-8")
    return path


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate the source catalog markdown.")
    parser.add_argument(
        "--output",
        default="sources_catalog.md",
        help="Path to write the catalog markdown (default: sources_catalog.md)",
    )
    return parser


def main() -> None:
    parser = _build_arg_parser()
    args = parser.parse_args()
    asyncio.run(generate_catalog_file(output_path=args.output))


if __name__ == "__main__":  # pragma: no cover - CLI helper
    main()

