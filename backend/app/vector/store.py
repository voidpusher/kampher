"""Qdrant vector store.

One named collection per embeddable object type. Payloads always carry the
Postgres id plus the filterable fields (source, industry, created_at), so
hybrid-search filters execute inside Qdrant instead of post-filtering in
Python.
"""

from __future__ import annotations

import atexit
import uuid
from enum import StrEnum
from functools import lru_cache
from typing import TYPE_CHECKING, Any, cast

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PayloadSchemaType,
    PointStruct,
    Range,
    VectorParams,
)

from app.core.config import get_settings
from app.core.logging import get_logger

if TYPE_CHECKING:
    from datetime import datetime


class Collection(StrEnum):
    POSTS = "posts"
    PROBLEMS = "problems"
    PAIN_CLUSTERS = "pain_clusters"
    FEATURE_REQUESTS = "feature_requests"
    OPPORTUNITIES = "opportunities"


class VectorStore:
    def __init__(self) -> None:
        settings = get_settings()
        if settings.qdrant_path:
            # Embedded mode: vectors live in a local directory, no server.
            self.client = QdrantClient(path=settings.qdrant_path)
            # Close before interpreter teardown — the client's __del__ raises
            # noisy ImportErrors if it runs during shutdown.
            atexit.register(self.client.close)
        else:
            api_key = settings.qdrant_api_key
            self.client = QdrantClient(
                url=settings.qdrant_url,
                api_key=api_key.get_secret_value() if api_key else None,
            )
        self.dim = settings.embedding_dim
        self.log = get_logger("vector")

    def ensure_collections(self) -> None:
        """Idempotent bootstrap; called from worker startup and health checks."""
        existing = {c.name for c in self.client.get_collections().collections}
        for collection in Collection:
            if collection.value not in existing:
                self.client.create_collection(
                    collection_name=collection.value,
                    vectors_config=VectorParams(size=self.dim, distance=Distance.COSINE),
                )
                self.log.info("created qdrant collection", collection=collection.value)

        # Qdrant Cloud requires payload indexes for filtered vector searches.
        # Creating them is idempotent, so existing deployments are upgraded too.
        for field_name, field_schema in (
            ("source", PayloadSchemaType.KEYWORD),
            ("industry_slug", PayloadSchemaType.KEYWORD),
            ("posted_at_ts", PayloadSchemaType.FLOAT),
        ):
            self.client.create_payload_index(
                collection_name=Collection.POSTS.value,
                field_name=field_name,
                field_schema=field_schema,
                wait=True,
            )

    def upsert(
        self,
        collection: Collection,
        points: list[tuple[uuid.UUID, list[float], dict[str, Any]]],
    ) -> None:
        if not points:
            return
        self.client.upsert(
            collection_name=collection.value,
            points=[
                PointStruct(id=str(pid), vector=vector, payload=payload)
                for pid, vector, payload in points
            ],
        )

    def search(
        self,
        collection: Collection,
        vector: list[float],
        limit: int = 20,
        source: str | None = None,
        industry_slug: str | None = None,
        posted_after: datetime | None = None,
        score_threshold: float | None = None,
    ) -> list[tuple[uuid.UUID, float, dict[str, Any]]]:
        conditions: list[FieldCondition] = []
        if source:
            conditions.append(FieldCondition(key="source", match=MatchValue(value=source)))
        if industry_slug:
            conditions.append(
                FieldCondition(key="industry_slug", match=MatchValue(value=industry_slug))
            )
        if posted_after:
            conditions.append(
                FieldCondition(key="posted_at_ts", range=Range(gte=posted_after.timestamp()))
            )

        hits = self.client.query_points(
            collection_name=collection.value,
            query=vector,
            limit=limit,
            query_filter=Filter(must=list(conditions)) if conditions else None,
            score_threshold=score_threshold,
            with_payload=True,
        ).points
        return [(uuid.UUID(str(h.id)), h.score, h.payload or {}) for h in hits]

    def nearest(
        self, collection: Collection, vector: list[float]
    ) -> tuple[uuid.UUID, float] | None:
        """Single nearest neighbor — the primitive incremental clustering uses."""
        hits = self.search(collection, vector, limit=1)
        return (hits[0][0], hits[0][1]) if hits else None

    def retrieve_vector(self, collection: Collection, point_id: uuid.UUID) -> list[float] | None:
        points = self.client.retrieve(
            collection_name=collection.value, ids=[str(point_id)], with_vectors=True
        )
        if not points or points[0].vector is None:
            return None
        vector = points[0].vector
        if not isinstance(vector, list) or (vector and isinstance(vector[0], list)):
            return None
        return cast("list[float]", vector)


@lru_cache
def get_vector_store() -> VectorStore:
    return VectorStore()
