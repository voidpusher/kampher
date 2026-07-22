"""Opportunity report endpoints."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import SessionDep
from app.core.exceptions import NotFoundError
from app.models import Opportunity, OpportunityReport
from app.schemas.api import ReportOut

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/by-opportunity/{slug}", response_model=ReportOut)
async def report_for_opportunity(slug: str, session: SessionDep) -> ReportOut:
    report = await session.scalar(
        select(OpportunityReport)
        .join(Opportunity, Opportunity.id == OpportunityReport.opportunity_id)
        .where(Opportunity.slug == slug)
        .order_by(OpportunityReport.created_at.desc())
        .limit(1)
    )
    if report is None:
        raise NotFoundError(f"no report yet for opportunity {slug!r}")
    return ReportOut.model_validate(report)
