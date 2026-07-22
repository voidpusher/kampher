"""Trend explorer endpoints — spiking pain clusters."""

from __future__ import annotations

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.api.deps import SessionDep
from app.models import PainCluster, TrendSnapshot
from app.models.enums import TrendSubject
from app.schemas.api import TrendOut

router = APIRouter(prefix="/trends", tags=["trends"])


@router.get("", response_model=list[TrendOut])
async def list_trends(
    session: SessionDep,
    limit: int = Query(default=25, ge=1, le=100),
    min_mentions: int = Query(default=3, ge=0),
) -> list[TrendOut]:
    # Latest snapshot per cluster, ranked by velocity.
    latest = (
        select(
            TrendSnapshot.subject_id,
            func.max(TrendSnapshot.window_start).label("latest_window"),
        )
        .where(TrendSnapshot.subject_type == TrendSubject.PAIN_CLUSTER)
        .group_by(TrendSnapshot.subject_id)
        .subquery()
    )
    rows = await session.execute(
        select(TrendSnapshot, PainCluster)
        .join(
            latest,
            (TrendSnapshot.subject_id == latest.c.subject_id)
            & (TrendSnapshot.window_start == latest.c.latest_window),
        )
        .join(PainCluster, PainCluster.id == TrendSnapshot.subject_id)
        .where(TrendSnapshot.mention_count >= min_mentions)
        .order_by(TrendSnapshot.velocity.desc())
        .limit(limit)
    )
    return [
        TrendOut(
            cluster_id=cluster.id,
            label=cluster.label,
            canonical_statement=cluster.canonical_statement,
            support_count=cluster.support_count,
            avg_severity=cluster.avg_severity,
            velocity=snapshot.velocity,
            acceleration=snapshot.acceleration,
            mention_count=snapshot.mention_count,
            window_start=snapshot.window_start,
        )
        for snapshot, cluster in rows
    ]
