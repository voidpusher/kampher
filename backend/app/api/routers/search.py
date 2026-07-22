"""Search endpoints: keyword | semantic | hybrid."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from app.api.deps import SearchDep, SessionDep
from app.core.rate_limit import enforce_search_rate_limit
from app.models import Post
from app.schemas.api import PostOut, SearchResponse, SearchResult

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=SearchResponse, dependencies=[Depends(enforce_search_rate_limit)])
async def search(
    session: SessionDep,
    service: SearchDep,
    q: str = Query(default="", max_length=500),
    mode: Literal["keyword", "semantic", "hybrid"] = "hybrid",
    source: str | None = None,
    community: str | None = None,
    industry: str | None = None,
    limit: int = Query(default=20, ge=1, le=50),
) -> SearchResponse:
    hits = await service.search_posts(
        q,
        mode=mode,
        limit=limit,
        source=source,
        community=community,
        industry_slug=industry,
    )
    posts = {
        p.id: p
        for p in await session.scalars(select(Post).where(Post.id.in_([h.post_id for h in hits])))
    }
    return SearchResponse(
        query=q,
        mode=mode,
        results=[
            SearchResult(
                post=PostOut.model_validate(posts[hit.post_id]),
                score=hit.score,
                matched_by=hit.matched_by,
            )
            for hit in hits
            if hit.post_id in posts
        ],
    )
