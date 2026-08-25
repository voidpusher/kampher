from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.services.recovery import (
    RecoveryMetrics,
    evaluate_recovery_readiness,
    recovery_is_ready,
)


def test_recovery_readiness_accepts_usable_fresh_database() -> None:
    now = datetime(2026, 8, 25, 12, tzinfo=UTC)
    metrics = RecoveryMetrics(
        migration_version="d63f7b8210ce",
        post_count=58_000,
        source_count=4,
        industry_count=12,
        failed_stream_count=0,
        latest_collected_at=now - timedelta(minutes=20),
    )

    checks = evaluate_recovery_readiness(metrics, now=now)

    assert recovery_is_ready(checks) is True
    assert set(checks.values()) == {"ok"}


def test_recovery_readiness_reports_every_broken_invariant() -> None:
    now = datetime(2026, 8, 25, 12, tzinfo=UTC)
    metrics = RecoveryMetrics(
        migration_version=None,
        post_count=0,
        source_count=1,
        industry_count=0,
        failed_stream_count=2,
        latest_collected_at=now - timedelta(hours=30),
    )

    checks = evaluate_recovery_readiness(metrics, now=now)

    assert checks == {
        "schema_migration": "missing",
        "corpus": "empty",
        "source_coverage": "insufficient",
        "taxonomy": "empty",
        "stream_failures": "error",
        "collection_freshness": "stale",
    }
    assert recovery_is_ready(checks) is False
