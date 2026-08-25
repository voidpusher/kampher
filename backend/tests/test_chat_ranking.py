from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from app.services.chat import ChatService


def _post(
    *,
    source: str,
    posted_at: datetime,
    title: str = "Deployment fails during release",
    body: str = (
        "Our deployment fails during the release step and the manual rollback "
        "workaround is slow for the engineering team."
    ),
    has_pain_signal: bool = True,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        title=title,
        body=body,
        community="deployment",
        source=SimpleNamespace(value=source),
        metrics={"comments": 4, "score": 5},
        has_pain_signal=has_pain_signal,
        posted_at=posted_at,
    )


def test_evidence_score_prefers_recent_equivalent_problem() -> None:
    now = datetime(2026, 8, 25, tzinfo=UTC)
    recent = _post(source="hackernews", posted_at=now - timedelta(days=3))
    historical = _post(source="hackernews", posted_at=now - timedelta(days=900))

    assert ChatService._evidence_score(recent, "deployment", now) > ChatService._evidence_score(
        historical, "deployment", now
    )


def test_ranking_boosts_problem_corroborated_by_another_source() -> None:
    now = datetime(2026, 8, 25, tzinfo=UTC)
    corroborated = _post(source="hackernews", posted_at=now - timedelta(days=10))
    corroborating = _post(source="devto", posted_at=now - timedelta(days=12))
    isolated = _post(
        source="stackoverflow",
        posted_at=now - timedelta(days=10),
        title="Deployment configuration documentation is confusing",
        body=(
            "The configuration documentation is confusing and makes environment "
            "variables difficult to understand for new developers."
        ),
    )

    ranked = ChatService._rank_evidence([isolated, corroborated, corroborating], "deployment", now)

    assert ranked.index(corroborated) < ranked.index(isolated)
    assert ranked.index(corroborating) < ranked.index(isolated)
