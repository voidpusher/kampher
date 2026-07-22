"""Embedding Agent tasks."""

from __future__ import annotations

import uuid

from app.core.exceptions import RetryableError
from app.core.logging import bind_request_context
from app.db.session import worker_session
from app.services.embedding import EmbeddingService
from app.workers.celery_app import app

_RETRY = dict(
    autoretry_for=(RetryableError, ConnectionError),
    retry_backoff=10,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=5,
)


@app.task(name="kampher.embed.post", bind=True, **_RETRY)
def embed_post(self: object, post_id: str) -> dict[str, int]:
    bind_request_context(post_id=post_id)
    with worker_session() as session:
        count = EmbeddingService(session).embed_posts([uuid.UUID(post_id)])
    return {"embedded": count}


@app.task(name="kampher.embed.problems", bind=True, **_RETRY)
def embed_problems(self: object, problem_ids: list[str]) -> dict[str, int]:
    bind_request_context()
    with worker_session() as session:
        count = EmbeddingService(session).embed_problems([uuid.UUID(pid) for pid in problem_ids])
    return {"embedded": count}


@app.task(name="kampher.embed.opportunity", bind=True, **_RETRY)
def embed_opportunity(self: object, opportunity_id: str) -> dict[str, int]:
    bind_request_context(opportunity_id=opportunity_id)
    with worker_session() as session:
        count = EmbeddingService(session).embed_opportunities([uuid.UUID(opportunity_id)])
    return {"embedded": count}
