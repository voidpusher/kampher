"""Embedding provider interface + factory.

Default is a local sentence-transformers model: at hundreds of millions of
documents, embedding through a paid API is an architecture bug. An API
provider can be added behind the same interface via ``EMBEDDING_PROVIDER``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from functools import lru_cache

from app.core.config import get_settings
from app.core.exceptions import ConfigurationError


class BaseEmbedder(ABC):
    dim: int

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed documents for indexing."""

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Embed a search query (some models use asymmetric query prefixes)."""


@lru_cache
def get_embedder() -> BaseEmbedder:
    settings = get_settings()
    if settings.embedding_provider == "fastembed":
        from app.ai.embeddings.fastembed_provider import FastEmbedEmbedder

        return FastEmbedEmbedder(settings.embedding_model, settings.embedding_dim)
    if settings.embedding_provider == "local":
        # torch-based sentence-transformers; heavier but supports any HF model.
        from app.ai.embeddings.local import LocalEmbedder

        return LocalEmbedder(settings.embedding_model, settings.embedding_dim)
    raise ConfigurationError(f"unknown embedding provider: {settings.embedding_provider!r}")
