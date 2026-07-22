"""Report Agent tasks."""

from __future__ import annotations

from app.core.exceptions import RetryableError
from app.core.logging import bind_request_context
from app.db.session import worker_session
from app.services.report import ReportService
from app.workers.celery_app import app


@app.task(
    name="kampher.reports.generate_missing",
    bind=True,
    autoretry_for=(RetryableError,),
    retry_backoff=60,
    retry_backoff_max=900,
    retry_jitter=True,
    max_retries=3,
)
def generate_missing(self: object) -> dict[str, int]:
    bind_request_context()
    with worker_session() as session:
        count = ReportService(session).generate_missing()
    return {"reports": count}
