"""Write-side repository for the intelligence agents (sync sessions)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models import (
    Industry,
    Opportunity,
    OpportunityReport,
    OpportunityScore,
    PainCluster,
    Problem,
    Topic,
    TrendSnapshot,
)
from app.models.enums import OpportunityStatus, ScoreKind, TrendSubject


class IntelligenceRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    # ── taxonomy lookups (cached per repository lifetime) ───────────────

    def topic_slugs(self) -> dict[str, uuid.UUID]:
        return {t.slug: t.id for t in self.session.scalars(select(Topic))}

    def industry_slugs(self) -> dict[str, uuid.UUID]:
        return {i.slug: i.id for i in self.session.scalars(select(Industry))}

    # ── problems & clusters ─────────────────────────────────────────────

    def unclustered_problems(self, limit: int = 500) -> list[Problem]:
        return list(
            self.session.scalars(
                select(Problem)
                .where(Problem.pain_cluster_id.is_(None))
                .order_by(Problem.created_at)
                .limit(limit)
            )
        )

    def get_cluster(self, cluster_id: uuid.UUID) -> PainCluster | None:
        return self.session.get(PainCluster, cluster_id)

    def create_cluster(self, problem: Problem, industry_id: uuid.UUID | None) -> PainCluster:
        cluster = PainCluster(
            label=problem.statement[:120],
            canonical_statement=problem.statement,
            industry_id=industry_id,
            support_count=0,
            avg_severity=0.0,
            first_seen_at=problem.created_at,
            last_seen_at=problem.created_at,
        )
        self.session.add(cluster)
        self.session.flush()
        return cluster

    def assign_to_cluster(self, problem: Problem, cluster: PainCluster) -> None:
        problem.pain_cluster_id = cluster.id
        # Running mean keeps assignment O(1) — no rescan of members.
        new_count = cluster.support_count + 1
        cluster.avg_severity = (
            cluster.avg_severity * cluster.support_count + problem.severity
        ) / new_count
        cluster.support_count = new_count
        cluster.last_seen_at = max(cluster.last_seen_at or problem.created_at, problem.created_at)

    def clusters_ready_for_opportunity(
        self, min_support: int, limit: int = 20
    ) -> list[PainCluster]:
        """Clusters with enough evidence and no opportunity generated yet."""
        subquery = select(Opportunity.pain_cluster_id).where(
            Opportunity.pain_cluster_id.is_not(None)
        )
        return list(
            self.session.scalars(
                select(PainCluster)
                .where(
                    PainCluster.support_count >= min_support,
                    PainCluster.id.not_in(subquery),
                )
                .order_by(PainCluster.support_count.desc())
                .limit(limit)
            )
        )

    def cluster_problems(self, cluster_id: uuid.UUID, limit: int = 15) -> list[Problem]:
        return list(
            self.session.scalars(
                select(Problem)
                .where(Problem.pain_cluster_id == cluster_id)
                .order_by(Problem.severity.desc())
                .limit(limit)
            )
        )

    # ── opportunities ───────────────────────────────────────────────────

    def create_opportunity(self, **fields: Any) -> Opportunity:
        opportunity = Opportunity(**fields)
        self.session.add(opportunity)
        self.session.flush()
        return opportunity

    def slug_exists(self, slug: str) -> bool:
        return (
            self.session.scalar(select(Opportunity.id).where(Opportunity.slug == slug)) is not None
        )

    def save_score(
        self,
        opportunity_id: uuid.UUID,
        kind: ScoreKind,
        value: float,
        confidence: float,
        reasoning: str,
        evidence: dict[str, Any],
    ) -> None:
        stmt = (
            pg_insert(OpportunityScore)
            .values(
                id=uuid.uuid4(),
                opportunity_id=opportunity_id,
                kind=kind,
                value=value,
                confidence=confidence,
                reasoning=reasoning,
                evidence=evidence,
            )
            .on_conflict_do_update(
                index_elements=[OpportunityScore.opportunity_id, OpportunityScore.kind],
                set_={
                    "value": value,
                    "confidence": confidence,
                    "reasoning": reasoning,
                    "evidence": evidence,
                },
            )
        )
        self.session.execute(stmt)

    def opportunities_without_report(self, limit: int = 5) -> list[Opportunity]:
        subquery = select(OpportunityReport.opportunity_id)
        return list(
            self.session.scalars(
                select(Opportunity)
                .where(
                    Opportunity.status == OpportunityStatus.ACTIVE,
                    Opportunity.id.not_in(subquery),
                )
                .order_by(Opportunity.composite_score.desc())
                .limit(limit)
            )
        )

    def save_report(
        self,
        opportunity_id: uuid.UUID,
        content_md: str,
        sections: dict[str, Any],
        model: str,
    ) -> OpportunityReport:
        report = OpportunityReport(
            opportunity_id=opportunity_id,
            content_md=content_md,
            sections=sections,
            model=model,
        )
        self.session.add(report)
        self.session.flush()
        return report

    # ── trends ──────────────────────────────────────────────────────────

    def daily_problem_counts(self, cluster_id: uuid.UUID, days: int) -> list[int]:
        """Mentions/day for a cluster over the trailing window, zero-filled."""
        since = datetime.now(UTC) - timedelta(days=days)
        rows = self.session.execute(
            select(
                func.date_trunc("day", Problem.created_at).label("day"),
                func.count().label("n"),
            )
            .where(Problem.pain_cluster_id == cluster_id, Problem.created_at >= since)
            .group_by("day")
        ).all()
        by_day = {row.day.date(): row.n for row in rows}
        today = datetime.now(UTC).date()
        return [by_day.get(today - timedelta(days=offset), 0) for offset in range(days - 1, -1, -1)]

    def save_trend_snapshot(
        self,
        subject_type: TrendSubject,
        subject_id: uuid.UUID,
        window_start: datetime,
        mention_count: int,
        velocity: float,
        acceleration: float,
        avg_severity: float | None = None,
    ) -> None:
        stmt = (
            pg_insert(TrendSnapshot)
            .values(
                id=uuid.uuid4(),
                subject_type=subject_type,
                subject_id=subject_id,
                window_start=window_start,
                mention_count=mention_count,
                velocity=velocity,
                acceleration=acceleration,
                avg_severity=avg_severity,
            )
            .on_conflict_do_update(
                index_elements=[
                    TrendSnapshot.subject_type,
                    TrendSnapshot.subject_id,
                    TrendSnapshot.window_start,
                ],
                set_={
                    "mention_count": mention_count,
                    "velocity": velocity,
                    "acceleration": acceleration,
                    "avg_severity": avg_severity,
                },
            )
        )
        self.session.execute(stmt)

    def active_cluster_ids(self, since_days: int = 30) -> list[uuid.UUID]:
        since = datetime.now(UTC) - timedelta(days=since_days)
        return list(
            self.session.scalars(select(PainCluster.id).where(PainCluster.last_seen_at >= since))
        )
