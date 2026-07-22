"""FastEmbed (ONNX) embedder — same bge-small model, ~5x lighter than torch.

Default provider: runs comfortably in a 512MB container, which torch cannot.
Query prefixing for BGE models is handled by fastembed's ``query_embed``.
"""

from __future__ import annotations

from typing import cast

from fastembed import TextEmbedding

from app.ai.embeddings.base import BaseEmbedder
from app.core.exceptions import ConfigurationError


class FastEmbedEmbedder(BaseEmbedder):
    def __init__(self, model_name: str, expected_dim: int) -> None:
        self._model = TextEmbedding(model_name=model_name)
        probe = next(iter(self._model.embed(["dimension probe"])))
        if len(probe) != expected_dim:
            raise ConfigurationError(
                f"EMBEDDING_DIM={expected_dim} but {model_name} produces {len(probe)}"
            )
        self.dim = expected_dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [vector.tolist() for vector in self._model.embed(texts, batch_size=64)]

    def embed_query(self, text: str) -> list[float]:
        return cast("list[float]", next(iter(self._model.query_embed([text]))).tolist())
