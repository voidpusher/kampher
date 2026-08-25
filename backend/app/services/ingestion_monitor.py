"""Pure ingestion-freshness evaluation shared by API and scheduled workers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.models import SourceCursor
from app.models.enums import Source


@dataclass(frozen=True, slots=True)
class ExpectedStream:
    source: Source
    stream: str
    stale_after_minutes: int


def evaluate_stream_health(
    expected: list[ExpectedStream],
    cursors: list[SourceCursor],
    *,
    now: datetime | None = None,
) -> dict[str, str]:
    """Return stable, non-sensitive statuses for every expected source stream."""
    reference_time = now or datetime.now(UTC)
    observed = {(cursor.source, cursor.stream): cursor for cursor in cursors}
    checks: dict[str, str] = {}

    for item in expected:
        key = f"{item.source.value}/{item.stream}"
        cursor = observed.get((item.source, item.stream))
        if cursor is None or cursor.last_run_at is None:
            checks[key] = "missing"
            continue
        if cursor.last_error:
            checks[key] = "error"
            continue

        last_run_at = cursor.last_run_at
        if last_run_at.tzinfo is None:
            last_run_at = last_run_at.replace(tzinfo=UTC)
        age_minutes = max((reference_time - last_run_at).total_seconds() / 60.0, 0.0)
        checks[key] = "stale" if age_minutes > item.stale_after_minutes else "ok"

    return checks


def is_healthy(checks: dict[str, str]) -> bool:
    return bool(checks) and all(status == "ok" for status in checks.values())
