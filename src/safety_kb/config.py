"""Runtime configuration helpers for the knowledge base."""

from functools import lru_cache
from typing import Optional

from pydantic import HttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for ingestion and retrieval."""

    database_url: str = "sqlite+aiosqlite:///./safety_kb.db"
    embedding_provider: str = "fake"  # fake|openai|sentence_transformer|custom
    embedding_dim: int = 1536
    embedding_model_name: str = "text-embedding-3-large"
    embedding_api_base: Optional[HttpUrl] = None
    embedding_api_key: Optional[str] = None
    chunk_size: int = 512
    chunk_overlap: int = 80
    fetch_batch_size: int = 50
    max_candidate_chunks: int = 400
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=(".env", "env.example"),
        env_prefix="SAFETY_KB_",
        extra="allow",
    )

    @field_validator("embedding_provider")
    @classmethod
    def validate_provider(cls, value: str) -> str:
        allowed = {"fake", "openai", "sentence_transformer", "custom"}
        if value not in allowed:
            raise ValueError(f"Unsupported embedding_provider '{value}'. Allowed: {allowed}")
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached Settings instance."""
    return Settings()

