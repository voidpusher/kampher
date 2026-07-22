"""Trend service — the Trend Agent's logic (stage 13, statistical half).

Recomputes daily trend snapshots for every recently-active pain cluster.
The LLM never touches this path: trends are pure time-series math over
extraction counts, which keeps them cheap, reproducible, and re-runnable.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.ai.scoring import trend_score
from app.core.logging import get_logger
from app.models.enums import TrendSubject
from app.repositories.intelligence import IntelligenceRepository

log = get_logger("service.trend")

WINDOW_DAYS = 28


class TrendService:
    def __init__(self, session: Session) -> None:
        self.repo = IntelligenceRepository(session)

    def snapshot_clusters(self) -> int:
        today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        cluster_ids = self.repo.active_cluster_ids(since_days=WINDOW_DAYS)
        for cluster_id in cluster_ids:
            counts = self.repo.daily_problem_counts(cluster_id, WINDOW_DAYS)
            _, velocity, acceleration = trend_score(counts)
            cluster = self.repo.get_cluster(cluster_id)
            self.repo.save_trend_snapshot(
                TrendSubject.PAIN_CLUSTER,
                cluster_id,
                window_start=today,
                mention_count=sum(counts),
                velocity=velocity,
                acceleration=acceleration,
                avg_severity=cluster.avg_severity if cluster else None,
            )
        log.info("trend snapshots written", clusters=len(cluster_ids))
        return len(cluster_ids)
