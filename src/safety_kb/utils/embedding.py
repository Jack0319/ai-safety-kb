"""Embedding provider interfaces."""

from __future__ import annotations

import asyncio
import hashlib
import math
import random
from typing import Dict, Iterable, List, Optional

import httpx

from ..config import Settings, get_settings

try:  # Optional heavy dependency
    from sentence_transformers import SentenceTransformer
except Exception:  # pragma: no cover - optional dependency
    SentenceTransformer = None  # type: ignore[assignment]


class EmbeddingProvider:
    """Base class for embedding providers."""

    def __init__(self, settings: Settings):
        self.settings = settings

    async def embed(self, texts: Iterable[str]) -> List[List[float]]:
        raise NotImplementedError


class FakeEmbeddingProvider(EmbeddingProvider):
    """Deterministic pseudo-embeddings useful for tests and dev."""

    def _vector(self, text: str) -> List[float]:
        seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest(), 16) % (2**32)
        rng = random.Random(seed)
        values = [rng.random() for _ in range(self.settings.embedding_dim)]
        norm = math.sqrt(sum(v * v for v in values)) or 1.0
        return [v / norm for v in values]

    async def embed(self, texts: Iterable[str]) -> List[List[float]]:
        return [self._vector(text) for text in texts]


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """Thin async wrapper around the OpenAI embeddings endpoint."""

    async def embed(self, texts: Iterable[str]) -> List[List[float]]:
        if not self.settings.embedding_api_key:
            raise RuntimeError("OpenAI embeddings require SAFETY_KB_EMBEDDING_API_KEY")
        url = self.settings.embedding_api_base or "https://api.openai.com/v1/embeddings"
        headers = {
            "Authorization": f"Bearer {self.settings.embedding_api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                url,
                json={"model": self.settings.embedding_model_name, "input": list(texts)},
                headers=headers,
            )
        response.raise_for_status()
        payload = response.json()
        return [item["embedding"] for item in payload["data"]]


class SentenceTransformerEmbeddingProvider(EmbeddingProvider):
    """Local embedding provider using sentence-transformers."""

    def __init__(self, settings: Settings):
        if SentenceTransformer is None:  # pragma: no cover - optional dependency
            raise RuntimeError("sentence-transformers is not installed")
        super().__init__(settings)
        self.model = SentenceTransformer(settings.embedding_model_name)

    async def embed(self, texts: Iterable[str]) -> List[List[float]]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: self.model.encode(list(texts), normalize_embeddings=True).tolist())


_provider_cache: Dict[tuple[str, int, str], EmbeddingProvider] = {}


def get_embedding_provider(settings: Settings | None = None) -> EmbeddingProvider:
    """Return a cached embedding provider instance keyed by configuration."""
    settings = settings or get_settings()
    cache_key = (
        settings.embedding_provider,
        settings.embedding_dim,
        settings.embedding_model_name,
    )
    if cache_key in _provider_cache:
        return _provider_cache[cache_key]

    if settings.embedding_provider == "openai":
        provider = OpenAIEmbeddingProvider(settings)
    elif settings.embedding_provider == "sentence_transformer":
        provider = SentenceTransformerEmbeddingProvider(settings)
    elif settings.embedding_provider == "custom":
        raise RuntimeError("Custom embedding provider not configured")
    else:
        provider = FakeEmbeddingProvider(settings)

    _provider_cache[cache_key] = provider
    return provider


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Compute cosine similarity between vectors."""
    if not vec_a or not vec_b:
        return 0.0
    numerator = sum(a * b for a, b in zip(vec_a, vec_b))
    denom_a = math.sqrt(sum(a * a for a in vec_a)) or 1.0
    denom_b = math.sqrt(sum(b * b for b in vec_b)) or 1.0
    return numerator / (denom_a * denom_b)

