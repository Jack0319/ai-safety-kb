"""Checksum helpers for ingestion pipelines."""

from __future__ import annotations

import hashlib
from pathlib import Path


def sha256_text(value: str) -> str:
    """Return the SHA-256 checksum of the provided string."""
    data = value.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    """Return the SHA-256 checksum of a file."""
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

