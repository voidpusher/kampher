"""Intelligence models: problems → pain clusters → opportunities → reports."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Enum, Float, ForeignKey, Index, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import OpportunityStatus, ScoreKind, TrendSubject


class Problem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A canonical problem statement extracted from one post (stage 9)."""

    __tablename__ = "problems"
    __table_args__ = (
        Index("ix_problems_post_id", "post_id"),
        Index("ix_problems_pain_cluster_id", "pain_cluster_id"),
    )

    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("posts.id", ondelete="CASCADE")
    )
    statement: Mapped[str] = mapped_column(Text)
    severity: Mapped[float] = mapped_column(Float)  # 0 … 1, from pain detection
    audience: Mapped[str | None] = mapped_column(Text)  # who has this problem
    current_workaround: Mapped[str | None] = mapped_column(Text)  # from stage 10
    evidence_quote: Mapped[str | None] = mapped_column(Text)
    pain_cluster_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pain_clusters.id", ondelete="SET NULL")
    )

    pain_cluster: Mapped[PainCluster | None] = relationship(back_populates="problems")


class PainCluster(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Semantically-similar problems grouped together.

    The centroid vector lives in Qdrant under this row's id; Postgres keeps
    the aggregate stats that make clusters rankable and trendable.
    """

    __tablename__ = "pain_clusters"

    label: Mapped[str] = mapped_column(Text)
    canonical_statement: Mapped[str] = mapped_column(Text)
    industry_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("industries.id", ondelete="SET NULL")
    )
    support_count: Mapped[int] = mapped_column(Integer, default=0)
    avg_severity: Mapped[float] = mapped_column(Float, default=0.0)
    first_seen_at: Mapped[datetime | None]
    last_seen_at: Mapped[datetime | None]

    problems: Mapped[list[Problem]] = relationship(back_populates="pain_cluster")
    opportunities: Mapped[list[Opportunity]] = relationship(back_populates="pain_cluster")


class FeatureRequest(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "feature_requests"
    __table_args__ = (Index("ix_feature_requests_post_id", "post_id"),)

    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("posts.id", ondelete="CASCADE")
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL")
    )
    description: Mapped[str] = mapped_column(Text)
    urgency: Mapped[float] = mapped_column(Float)  # 0 … 1
    evidence_quote: Mapped[str | None] = mapped_column(Text)


class Opportunity(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "opportunities"
    __table_args__ = (
        Index("ix_opportunities_composite_score", "composite_score"),
        Index("ix_opportunities_status", "status"),
    )

    slug: Mapped[str] = mapped_column(Text, unique=True)
    title: Mapped[str] = mapped_column(Text)
    thesis: Mapped[str] = mapped_column(Text)  # one-sentence "why now"
    description: Mapped[str] = mapped_column(Text)
    target_customer: Mapped[str | None] = mapped_column(Text)
    suggested_solution: Mapped[str | None] = mapped_column(Text)

    pain_cluster_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pain_clusters.id", ondelete="SET NULL")
    )
    industry_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("industries.id", ondelete="SET NULL")
    )
    status: Mapped[OpportunityStatus] = mapped_column(
        Enum(
            OpportunityStatus,
            name="opportunity_status",
            values_callable=lambda e: [m.value for m in e],
        ),
        default=OpportunityStatus.CANDIDATE,
    )
    # Deterministic weighted blend of component scores — never a model guess.
    composite_score: Mapped[float] = mapped_column(Float, default=0.0)
    generated_by_model: Mapped[str | None] = mapped_column(Text)
    meta: Mapped[dict[str, Any]] = mapped_column(default=dict)

    pain_cluster: Mapped[PainCluster | None] = relationship(back_populates="opportunities")
    scores: Mapped[list[OpportunityScore]] = relationship(
        back_populates="opportunity", cascade="all, delete-orphan"
    )
    reports: Mapped[list[OpportunityReport]] = relationship(back_populates="opportunity")


class OpportunityScore(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """One explained score. No black-box numbers: reasoning + evidence required."""

    __tablename__ = "opportunity_scores"
    __table_args__ = (UniqueConstraint("opportunity_id", "kind"),)

    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("opportunities.id", ondelete="CASCADE")
    )
    kind: Mapped[ScoreKind] = mapped_column(
        Enum(ScoreKind, name="score_kind", values_callable=lambda e: [m.value for m in e])
    )
    value: Mapped[float] = mapped_column(Float)  # 0 … 100
    confidence: Mapped[float] = mapped_column(Float)  # 0 … 1
    reasoning: Mapped[str] = mapped_column(Text)
    # [{post_id, quote}] — the observations the score rests on.
    evidence: Mapped[dict[str, Any]] = mapped_column(default=dict)

    opportunity: Mapped[Opportunity] = relationship(back_populates="scores")


class OpportunityReport(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "opportunity_reports"

    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("opportunities.id", ondelete="CASCADE")
    )
    content_md: Mapped[str] = mapped_column(Text)
    # Structured sections: summary, market, pain_points, competitors, pricing,
    # missing_features, ideas, recommendations — each with citations.
    sections: Mapped[dict[str, Any]] = mapped_column(default=dict)
    model: Mapped[str | None] = mapped_column(Text)

    opportunity: Mapped[Opportunity] = relationship(back_populates="reports")


class TrendSnapshot(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Daily aggregate per subject; velocity/acceleration derive from deltas."""

    __tablename__ = "trend_snapshots"
    __table_args__ = (
        UniqueConstraint("subject_type", "subject_id", "window_start"),
        Index("ix_trend_snapshots_subject", "subject_type", "subject_id"),
    )

    subject_type: Mapped[TrendSubject] = mapped_column(
        Enum(TrendSubject, name="trend_subject", values_callable=lambda e: [m.value for m in e])
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    window_start: Mapped[datetime]
    mention_count: Mapped[int] = mapped_column(Integer, default=0)
    velocity: Mapped[float] = mapped_column(Float, default=0.0)  # d(count)/dt
    acceleration: Mapped[float] = mapped_column(Float, default=0.0)  # d(velocity)/dt
    avg_severity: Mapped[float | None] = mapped_column(Float)
