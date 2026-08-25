"""Read-only database checks that make backup recovery measurable."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models import Industry, Post, SourceCursor


@dataclass(frozen=True, slots=True)
class RecoveryMetrics:
    migration_version: str | None
    post_count: int
    source_count: int
    industry_count: int
    failed_stream_count: int
    latest_collected_at: datetime | None


def read_recovery_metrics(session: Session) -> RecoveryMetrics:
    return RecoveryMetrics(
        migration_version=session.scalar(text("SELECT version_num FROM alembic_version LIMIT 1")),
        post_count=int(session.scalar(select(func.count(Post.id))) or 0),
        source_count=int(session.scalar(select(func.count(func.distinct(Post.source)))) or 0),
        industry_count=int(session.scalar(select(func.count(Industry.id))) or 0),
        failed_stream_count=int(
            session.scalar(
                select(func.count(SourceCursor.id)).where(SourceCursor.last_error.is_not(None))
            )
            or 0
        ),
        latest_collected_at=session.scalar(select(func.max(Post.collected_at))),
    )


def evaluate_recovery_readiness(
    metrics: RecoveryMetrics,
    *,
    now: datetime | None = None,
    maximum_collection_age_hours: int = 24,
) -> dict[str, str]:
    reference_time = now or datetime.now(UTC)
    checks = {
        "schema_migration": "ok" if metrics.migration_version else "missing",
        "corpus": "ok" if metrics.post_count > 0 else "empty",
        "source_coverage": "ok" if metrics.source_count >= 3 else "insufficient",
        "taxonomy": "ok" if metrics.industry_count > 0 else "empty",
        "stream_failures": "ok" if metrics.failed_stream_count == 0 else "error",
    }

    collected_at = metrics.latest_collected_at
    if collected_at is None:
        checks["collection_freshness"] = "missing"
    else:
        if collected_at.tzinfo is None:
            collected_at = collected_at.replace(tzinfo=UTC)
        age_hours = max((reference_time - collected_at).total_seconds() / 3600.0, 0.0)
        checks["collection_freshness"] = (
            "stale" if age_hours > maximum_collection_age_hours else "ok"
        )

    return checks


def recovery_is_ready(checks: dict[str, str]) -> bool:
    return bool(checks) and all(status == "ok" for status in checks.values())
