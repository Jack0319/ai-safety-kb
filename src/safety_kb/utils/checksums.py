"""Checksum helpers for ingestion pipelines."""

from __future__ import annotations

import hashlib


def sha256_text(value: str) -> str:
    """Return the SHA-256 checksum of the provided string."""
    data = value.encode("utf-8")
    return hashlib.sha256(data).hexdigest()

