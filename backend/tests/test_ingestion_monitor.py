from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from app.models.enums import Source
from app.services.ingestion_monitor import ExpectedStream, evaluate_stream_health, is_healthy


def _cursor(
    source: Source,
    stream: str,
    last_run_at: datetime,
    last_error: str | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        source=source,
        stream=stream,
        last_run_at=last_run_at,
        last_error=last_error,
    )


def test_stream_health_reports_fresh_stale_failed_and_missing() -> None:
    now = datetime(2026, 8, 25, 12, tzinfo=UTC)
    expected = [
        ExpectedStream(Source.HACKERNEWS, "frontpage", 60),
        ExpectedStream(Source.DEVTO, "devops", 60),
        ExpectedStream(Source.LOBSTERS, "newest", 60),
        ExpectedStream(Source.STACKOVERFLOW, "deployment", 180),
    ]
    cursors = [
        _cursor(Source.HACKERNEWS, "frontpage", now - timedelta(minutes=15)),
        _cursor(Source.DEVTO, "devops", now - timedelta(minutes=90)),
        _cursor(Source.LOBSTERS, "newest", now - timedelta(minutes=5), "HTTP 503"),
    ]

    checks = evaluate_stream_health(expected, cursors, now=now)  # type: ignore[arg-type]

    assert checks == {
        "hackernews/frontpage": "ok",
        "devto/devops": "stale",
        "lobsters/newest": "error",
        "stackoverflow/deployment": "missing",
    }
    assert is_healthy(checks) is False


def test_stream_health_accepts_naive_database_timestamps() -> None:
    now = datetime(2026, 8, 25, 12, tzinfo=UTC)
    expected = [ExpectedStream(Source.HACKERNEWS, "frontpage", 60)]
    cursors = [_cursor(Source.HACKERNEWS, "frontpage", datetime(2026, 8, 25, 11, 30))]

    checks = evaluate_stream_health(expected, cursors, now=now)  # type: ignore[arg-type]

    assert checks == {"hackernews/frontpage": "ok"}
    assert is_healthy(checks) is True
