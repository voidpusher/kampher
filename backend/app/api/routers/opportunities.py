"""Opportunity feed + detail endpoints."""

from __future__ import annotations

import base64
import uuid

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.api.deps import SessionDep
from app.core.exceptions import NotFoundError, ValidationFailedError
from app.models import Industry, Opportunity, Post, Problem
from app.models.enums import OpportunityStatus
from app.schemas.api import (
    OpportunityDetail,
    OpportunityPage,
    OpportunitySummary,
    PostRef,
    ScoreOut,
)

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


def _encode_cursor(score: float, oid: uuid.UUID) -> str:
    return base64.urlsafe_b64encode(f"{score}:{oid}".encode()).decode()


def _decode_cursor(cursor: str) -> tuple[float, uuid.UUID]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
        score_text, _, oid_text = raw.partition(":")
        return float(score_text), uuid.UUID(oid_text)
    except (ValueError, TypeError) as exc:
        raise ValidationFailedError("malformed pagination cursor") from exc


@router.get("", response_model=OpportunityPage)
async def list_opportunities(
    session: SessionDep,
    industry: str | None = None,
    min_score: float = Query(default=0, ge=0, le=100),
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = None,
) -> OpportunityPage:
    stmt = (
        select(Opportunity, Industry.slug)
        .outerjoin(Industry, Industry.id == Opportunity.industry_id)
        .where(
            Opportunity.status == OpportunityStatus.ACTIVE,
            Opportunity.composite_score >= min_score,
        )
        # Keyset pagination: stable under concurrent inserts, no OFFSET scans.
        .order_by(Opportunity.composite_score.desc(), Opportunity.id.desc())
        .limit(limit + 1)
    )
    if industry:
        stmt = stmt.where(Industry.slug == industry)
    if cursor:
        after_score, after_id = _decode_cursor(cursor)
        stmt = stmt.where(
            (Opportunity.composite_score < after_score)
            | ((Opportunity.composite_score == after_score) & (Opportunity.id < after_id))
        )

    rows = (await session.execute(stmt)).all()
    has_more = len(rows) > limit
    rows = rows[:limit]

    items = [
        OpportunitySummary(
            **OpportunitySummary.model_validate(opportunity).model_dump(exclude={"industry_slug"}),
            industry_slug=industry_slug,
        )
        for opportunity, industry_slug in rows
    ]
    next_cursor = (
        _encode_cursor(rows[-1][0].composite_score, rows[-1][0].id) if has_more and rows else None
    )
    return OpportunityPage(items=items, next_cursor=next_cursor)


@router.get("/{slug}", response_model=OpportunityDetail)
async def get_opportunity(slug: str, session: SessionDep) -> OpportunityDetail:
    opportunity = await session.scalar(select(Opportunity).where(Opportunity.slug == slug))
    if opportunity is None:
        raise NotFoundError(f"opportunity {slug!r} not found")

    industry_slug = None
    if opportunity.industry_id:
        industry_slug = await session.scalar(
            select(Industry.slug).where(Industry.id == opportunity.industry_id)
        )

    scores = [ScoreOut.model_validate(s) for s in await _scores(session, opportunity.id)]
    evidence = await _evidence_posts(session, opportunity)

    return OpportunityDetail(
        **OpportunitySummary.model_validate(opportunity).model_dump(exclude={"industry_slug"}),
        industry_slug=industry_slug,
        description=opportunity.description,
        target_customer=opportunity.target_customer,
        suggested_solution=opportunity.suggested_solution,
        meta=opportunity.meta,
        scores=scores,
        evidence_posts=evidence,
    )


async def _scores(session: SessionDep, opportunity_id: uuid.UUID):  # type: ignore[no-untyped-def]
    from app.models import OpportunityScore

    return list(
        await session.scalars(
            select(OpportunityScore).where(OpportunityScore.opportunity_id == opportunity_id)
        )
    )


async def _evidence_posts(session: SessionDep, opportunity: Opportunity) -> list[PostRef]:
    if opportunity.pain_cluster_id is None:
        return []
    rows = await session.execute(
        select(Post)
        .join(Problem, Problem.post_id == Post.id)
        .where(Problem.pain_cluster_id == opportunity.pain_cluster_id)
        .order_by(Problem.severity.desc())
        .limit(15)
    )
    return [PostRef.model_validate(post, from_attributes=True) for (post,) in rows]
