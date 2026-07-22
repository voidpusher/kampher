"""Celery application: queues, routing, and the beat schedule.

Each agent owns a named queue, so scaling an agent = adding worker replicas
for that queue. acks_late + reject_on_worker_lost means a killed worker
re-delivers instead of silently dropping work.
"""

from __future__ import annotations

from contextlib import suppress

from celery import Celery
from celery.schedules import crontab
from celery.signals import setup_logging, worker_process_init

from app.core.config import get_settings
from app.core.logging import configure_logging

settings = get_settings()

app = Celery(
    "kampher",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.workers.tasks.collect",
        "app.workers.tasks.enrich",
        "app.workers.tasks.embed",
        "app.workers.tasks.intelligence",
        "app.workers.tasks.reports",
        "app.workers.tasks.alerts",
    ],
)

app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,  # long LLM tasks: no hoarding
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    task_default_queue="collect",
    task_routes={
        "kampher.collect.*": {"queue": "collect"},
        "kampher.clean.*": {"queue": "clean"},
        "kampher.enrich.*": {"queue": "enrich"},
        "kampher.embed.*": {"queue": "embed"},
        "kampher.intelligence.*": {"queue": "intelligence"},
        "kampher.reports.*": {"queue": "reports"},
        "kampher.alerts.*": {"queue": "alerts"},
    },
    beat_schedule={
        # Collector Agent: sweep every enabled source.
        "collect-all-sources": {
            "task": "kampher.collect.all_sources",
            "schedule": crontab(minute="*/15"),
        },
        # Cleaner/Enrichment Agent: drain the pending backlog.
        "enrich-pending": {
            "task": "kampher.enrich.pending_backlog",
            "schedule": crontab(minute="*/5"),
        },
        # Opportunity Agent: cluster new problems, then generate.
        "cluster-and-generate": {
            "task": "kampher.intelligence.cluster_and_generate",
            "schedule": crontab(minute="*/30"),
        },
        # Trend Agent: daily snapshots.
        "trend-snapshots": {
            "task": "kampher.intelligence.trend_snapshots",
            "schedule": crontab(hour="1", minute="0"),
        },
        # Report Agent: fill in missing reports for active opportunities.
        "generate-reports": {
            "task": "kampher.reports.generate_missing",
            "schedule": crontab(hour="*/6", minute="10"),
        },
        # Alert Agent: spike detection over fresh snapshots.
        "scan-alerts": {
            "task": "kampher.alerts.scan",
            "schedule": crontab(hour="2", minute="0"),
        },
    },
)


@setup_logging.connect
def _configure_logging(**_: object) -> None:
    configure_logging()


@worker_process_init.connect
def _bootstrap_worker(**_: object) -> None:
    """Ensure Qdrant collections exist before any task touches them."""
    from app.vector.store import get_vector_store

    # Qdrant may lag at startup; the individual tasks retain their retry policy.
    with suppress(Exception):
        get_vector_store().ensure_collections()
