"""Technology survey evidence endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Query
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import SessionDep
from app.models import TechPoll, TechSurvey
from app.schemas.api import TechPollOut, TechPollOverview

router = APIRouter(prefix="/tech-polls", tags=["tech-polls"])


@router.get("", response_model=TechPollOverview)
async def list_tech_polls(
    session: SessionDep,
    category: str | None = Query(default=None, max_length=80),
) -> TechPollOverview:
    statement = (
        select(TechPoll)
        .options(selectinload(TechPoll.survey), selectinload(TechPoll.options))
        .order_by(TechPoll.category, TechPoll.created_at)
    )
    if category:
        statement = statement.where(func.lower(TechPoll.category) == category.lower())
    polls = list((await session.scalars(statement)).all())
    all_categories = list(
        (
            await session.scalars(select(TechPoll.category).distinct().order_by(TechPoll.category))
        ).all()
    )
    survey_stats = await session.execute(
        select(func.count(TechSurvey.id), func.coalesce(func.sum(TechSurvey.sample_size), 0))
    )
    total_surveys, total_respondents = survey_stats.one()
    return TechPollOverview(
        total_surveys=total_surveys,
        total_respondents=total_respondents,
        categories=all_categories,
        polls=[TechPollOut.model_validate(poll) for poll in polls],
    )
