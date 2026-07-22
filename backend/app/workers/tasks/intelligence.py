"""Trend + Opportunity Agent tasks."""

from __future__ import annotations

from sqlalchemy import select

from app.core.exceptions import RetryableError
from app.core.logging import bind_request_context, get_logger
from app.db.session import worker_session
from app.models import Opportunity
from app.services.clustering import ClusteringService
from app.services.opportunity_engine import OpportunityEngine
from app.services.trend import TrendService
from app.workers.celery_app import app

log = get_logger("tasks.intelligence")


@app.task(
    name="kampher.intelligence.cluster_and_generate",
    bind=True,
    autoretry_for=(RetryableError,),
    retry_backoff=60,
    retry_backoff_max=900,
    retry_jitter=True,
    max_retries=3,
)
def cluster_and_generate(self: object) -> dict[str, int]:
    """The Opportunity Agent's main loop: cluster new pain, then generate."""
    bind_request_context()
    with worker_session() as session:
        cluster_stats = ClusteringService(session).cluster_pending()

    with worker_session() as session:
        before = set(session.scalars(select(Opportunity.id)))
        engine_stats = OpportunityEngine(session).run()
        new_ids = [str(oid) for oid in session.scalars(select(Opportunity.id)) if oid not in before]

    from app.workers.tasks.embed import embed_opportunity

    for opportunity_id in new_ids:
        embed_opportunity.delay(opportunity_id)

    return {**cluster_stats, **engine_stats}


@app.task(name="kampher.intelligence.trend_snapshots")
def trend_snapshots() -> dict[str, int]:
    bind_request_context()
    with worker_session() as session:
        count = TrendService(session).snapshot_clusters()
    return {"snapshots": count}
