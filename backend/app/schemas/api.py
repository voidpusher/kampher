"""Public API response/request contracts (Pydantic DTOs).

ORM objects never cross the API boundary — every response is one of these.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import OpportunityStatus, ScoreKind, Source


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ── posts ────────────────────────────────────────────────────────────────


class PostOut(ORMModel):
    id: uuid.UUID
    source: Source
    url: str
    title: str | None
    body: str
    community: str | None
    posted_at: datetime
    metrics: dict[str, Any]
    language: str | None
    has_pain_signal: bool | None


class PostRef(BaseModel):
    id: uuid.UUID
    source: Source
    title: str | None
    url: str
    community: str | None = None


# ── opportunities ───────────────────────────────────────────────────────


class ScoreOut(ORMModel):
    kind: ScoreKind
    value: float
    confidence: float
    reasoning: str
    evidence: dict[str, Any]


class OpportunitySummary(ORMModel):
    id: uuid.UUID
    slug: str
    title: str
    thesis: str
    status: OpportunityStatus
    composite_score: float
    industry_slug: str | None = None
    created_at: datetime


class OpportunityDetail(OpportunitySummary):
    description: str
    target_customer: str | None
    suggested_solution: str | None
    meta: dict[str, Any]
    scores: list[ScoreOut]
    evidence_posts: list[PostRef]


class OpportunityPage(BaseModel):
    items: list[OpportunitySummary]
    next_cursor: str | None = None


# ── search ───────────────────────────────────────────────────────────────


class SearchResult(BaseModel):
    post: PostOut
    score: float
    matched_by: str


class SearchResponse(BaseModel):
    query: str
    mode: str
    results: list[SearchResult]


# ── chat ─────────────────────────────────────────────────────────────────


class ChatRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)


class ChatResponse(BaseModel):
    answer: str
    cited_posts: list[dict[str, Any]]
    cited_opportunities: list[dict[str, Any]]


# ── trends / reports / meta ─────────────────────────────────────────────


class TrendOut(BaseModel):
    cluster_id: uuid.UUID
    label: str
    canonical_statement: str
    support_count: int
    avg_severity: float
    velocity: float
    acceleration: float
    mention_count: int
    window_start: datetime


class ReportOut(ORMModel):
    id: uuid.UUID
    opportunity_id: uuid.UUID
    content_md: str
    sections: dict[str, Any]
    model: str | None
    created_at: datetime


class IndustryOut(ORMModel):
    id: uuid.UUID
    slug: str
    name: str


class SourceStatus(BaseModel):
    source: Source
    enabled: bool
    streams: list[str]


class InsightCount(BaseModel):
    label: str
    count: int


class InsightDay(BaseModel):
    date: date
    count: int


class InsightsOverview(BaseModel):
    total_posts: int
    posts_last_7_days: int
    latest_collected_at: datetime | None
    source_counts: list[InsightCount]
    top_communities: list[InsightCount]
    daily_activity: list[InsightDay]


class TechPollOptionOut(ORMModel):
    label: str
    percentage: float
    rank: int


class TechSurveyOut(ORMModel):
    slug: str
    publisher: str
    title: str
    year: int
    sample_size: int
    geography: str
    field_start: date | None
    field_end: date | None
    source_url: str
    methodology_url: str
    license: str | None
    reliability_score: float
    bias_note: str


class TechPollOut(ORMModel):
    id: uuid.UUID
    key: str
    category: str
    question: str
    audience: str
    response_count: int | None
    note: str | None
    survey: TechSurveyOut
    options: list[TechPollOptionOut]


class TechPollOverview(BaseModel):
    total_surveys: int
    total_respondents: int
    categories: list[str]
    polls: list[TechPollOut]


class GraphNodeOut(BaseModel):
    id: uuid.UUID
    kind: str
    key: str
    label: str


class GraphNeighborOut(GraphNodeOut):
    relation: str
    weight: float
    outgoing: bool


class HealthOut(BaseModel):
    status: str
    checks: dict[str, str]
