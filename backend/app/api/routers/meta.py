"""Platform metadata: sources, industries."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter
from sqlalchemy import func, select

from app.api.deps import SessionDep
from app.collectors.registry import all_collectors
from app.models import Industry, Post
from app.schemas.api import (
    IndustryOut,
    InsightCount,
    InsightDay,
    InsightsOverview,
    SourceStatus,
)

router = APIRouter(tags=["meta"])


@router.get("/sources", response_model=list[SourceStatus])
async def sources() -> list[SourceStatus]:
    statuses = []
    for source, collector_cls in all_collectors().items():
        collector = collector_cls()
        enabled = collector.enabled()
        statuses.append(
            SourceStatus(
                source=source,
                enabled=enabled,
                streams=collector.streams() if enabled else [],
            )
        )
    return statuses


@router.get("/industries", response_model=list[IndustryOut])
async def industries(session: SessionDep) -> list[IndustryOut]:
    rows = await session.scalars(select(Industry).order_by(Industry.name))
    return [IndustryOut.model_validate(i) for i in rows]


@router.get("/insights/overview", response_model=InsightsOverview)
async def insights_overview(session: SessionDep) -> InsightsOverview:
    """Corpus-level activity that remains useful without LLM enrichment."""
    now = datetime.now(UTC)
    activity_start = now - timedelta(days=13)

    total_posts = int(await session.scalar(select(func.count(Post.id))) or 0)
    posts_last_7_days = int(
        await session.scalar(
            select(func.count(Post.id)).where(Post.posted_at >= now - timedelta(days=7))
        )
        or 0
    )
    latest_collected_at = await session.scalar(select(func.max(Post.collected_at)))

    source_rows = (
        await session.execute(
            select(Post.source, func.count(Post.id))
            .group_by(Post.source)
            .order_by(func.count(Post.id).desc())
        )
    ).all()
    community_rows = (
        await session.execute(
            select(Post.community, func.count(Post.id))
            .where(Post.community.is_not(None))
            .group_by(Post.community)
            .order_by(func.count(Post.id).desc())
            .limit(8)
        )
    ).all()
    daily_rows = (
        await session.execute(
            select(func.date(Post.posted_at), func.count(Post.id))
            .where(Post.posted_at >= activity_start)
            .group_by(func.date(Post.posted_at))
            .order_by(func.date(Post.posted_at))
        )
    ).all()
    daily_by_date = {day: int(count) for day, count in daily_rows}

    return InsightsOverview(
        total_posts=total_posts,
        posts_last_7_days=posts_last_7_days,
        latest_collected_at=latest_collected_at,
        source_counts=[
            InsightCount(label=source.value, count=int(count)) for source, count in source_rows
        ],
        top_communities=[
            InsightCount(label=community, count=int(count))
            for community, count in community_rows
            if community
        ],
        daily_activity=[
            InsightDay(
                date=(activity_start + timedelta(days=offset)).date(),
                count=daily_by_date.get((activity_start + timedelta(days=offset)).date(), 0),
            )
            for offset in range(14)
        ],
    )
