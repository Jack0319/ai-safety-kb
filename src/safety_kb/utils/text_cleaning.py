"""Basic text cleanup utilities for ingestion."""

from __future__ import annotations

import re
from html import unescape

WHITESPACE_RE = re.compile(r"\s+")
HTML_TAG_RE = re.compile(r"<[^>]+>")


def normalize_whitespace(value: str) -> str:
    """Collapse whitespace while preserving paragraph breaks."""
    return WHITESPACE_RE.sub(" ", value).strip()


def strip_html(value: str) -> str:
    """Remove crude HTML tags."""
    return HTML_TAG_RE.sub(" ", value)


def clean_text(value: str) -> str:
    """Full cleaning pipeline used prior to chunking."""
    text = unescape(value or "")
    text = strip_html(text)
    text = normalize_whitespace(text)
    return text

