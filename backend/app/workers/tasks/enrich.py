"""Cleaner + Enrichment Agent tasks."""

from __future__ import annotations

import uuid

from sqlalchemy import select

from app.core.exceptions import RetryableError
from app.core.logging import bind_request_context, get_logger
from app.db.session import worker_session
from app.models import Post, Problem
from app.models.enums import EnrichmentStatus
from app.repositories.ingestion import IngestionRepository
from app.services.enrichment import EnrichmentService
from app.workers.celery_app import app

log = get_logger("tasks.enrich")


@app.task(name="kampher.enrich.pending_backlog")
def enrich_pending_backlog(batch: int = 200) -> dict[str, int]:
    """Safety net: pick up posts that missed the direct enqueue path."""
    bind_request_context()
    with worker_session() as session:
        post_ids = IngestionRepository(session).pending_post_ids(limit=batch)
    for post_id in post_ids:
        enrich_post.delay(str(post_id))
    return {"scheduled": len(post_ids)}


@app.task(
    name="kampher.enrich.post",
    bind=True,
    autoretry_for=(RetryableError,),
    retry_backoff=15,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=4,
)
def enrich_post(self: object, post_id: str) -> dict[str, str]:
    bind_request_context(post_id=post_id)
    pid = uuid.UUID(post_id)
    try:
        with worker_session() as session:
            outcome = EnrichmentService(session).enrich_post(pid)
            problem_ids = [
                str(row)
                for row in session.scalars(select(Problem.id).where(Problem.post_id == pid))
            ]
    except RetryableError:
        raise
    except Exception:
        # Permanent failure: mark it so the backlog sweep doesn't loop on it.
        with worker_session() as session:
            post = session.get(Post, pid)
            if post is not None:
                post.enrichment_status = EnrichmentStatus.FAILED
        log.exception("enrichment failed permanently", post_id=post_id)
        raise

    if outcome == "enriched":
        from app.workers.tasks.embed import embed_post, embed_problems

        embed_post.delay(post_id)
        if problem_ids:
            embed_problems.delay(problem_ids)
    return {"outcome": outcome}
