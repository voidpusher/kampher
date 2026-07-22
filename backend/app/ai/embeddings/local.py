"""Local sentence-transformers embedder (default: bge-small-en-v1.5)."""

from __future__ import annotations

from sentence_transformers import SentenceTransformer

from app.ai.embeddings.base import BaseEmbedder
from app.core.exceptions import ConfigurationError

# BGE models are asymmetric: queries need this prefix, documents do not.
_BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


class LocalEmbedder(BaseEmbedder):
    def __init__(self, model_name: str, expected_dim: int) -> None:
        self._model = SentenceTransformer(model_name)
        actual = self._model.get_sentence_embedding_dimension()
        if actual != expected_dim:
            raise ConfigurationError(
                f"EMBEDDING_DIM={expected_dim} but {model_name} produces {actual}"
            )
        self.dim = actual
        self._is_bge = "bge" in model_name.lower()

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = self._model.encode(
            texts, normalize_embeddings=True, batch_size=64, show_progress_bar=False
        )
        return [v.tolist() for v in vectors]

    def embed_query(self, text: str) -> list[float]:
        query = f"{_BGE_QUERY_PREFIX}{text}" if self._is_bge else text
        return self.embed([query])[0]
