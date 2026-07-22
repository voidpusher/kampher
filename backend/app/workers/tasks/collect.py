"""Collector Agent tasks."""

from __future__ import annotations

from app.collectors.registry import enabled_collectors
from app.core.exceptions import RetryableError
from app.core.logging import bind_request_context, get_logger
from app.db.session import worker_session
from app.models.enums import Source
from app.services.ingestion import IngestionService
from app.workers.celery_app import app

log = get_logger("tasks.collect")


@app.task(name="kampher.collect.all_sources")
def collect_all_sources() -> dict[str, int]:
    """Fan out one task per (source, stream) so streams fail independently."""
    bind_request_context()
    scheduled = 0
    for collector in enabled_collectors():
        for stream in collector.streams():
            collect_stream.delay(collector.source.value, stream)
            scheduled += 1
    log.info("collection fanned out", streams=scheduled)
    return {"streams_scheduled": scheduled}


@app.task(
    name="kampher.collect.stream",
    bind=True,
    autoretry_for=(RetryableError,),
    retry_backoff=30,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=5,
)
def collect_stream(self: object, source: str, stream: str) -> dict[str, int]:
    bind_request_context(source=source, stream=stream)
    with worker_session() as session:
        new_ids = IngestionService(session).collect_stream(Source(source), stream)

    # Hand fresh documents straight to the enrichment queue.
    from app.workers.tasks.enrich import enrich_post

    for post_id in new_ids:
        enrich_post.delay(str(post_id))
    return {"new_posts": len(new_ids)}
