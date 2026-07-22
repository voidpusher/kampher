"""Cluster-level intelligence: stages 12, 14, 15.

These run against a pain cluster (not a single post) with the cluster's top
evidence in context, on the deep model tier. Stage 13 (trend) is statistical
and lives in ``app.ai.scoring``; its output joins these in the score table.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field

from app.ai.llm.base import BaseLLMClient, LLMUsage, ModelTier
from app.models.enums import ScoreKind

OPPORTUNITY_SYSTEM = (
    "You are Kampher's opportunity analyst: a pragmatic venture researcher who turns "
    "clustered evidence of user pain into candid startup opportunity assessments.\n"
    "Rules:\n"
    "- Ground every claim in the provided evidence posts; cite them by index.\n"
    "- Be adversarial toward your own ideas: name the reasons this would fail.\n"
    "- Scores are 0-100. Calibrate: 50 is unremarkable, 80+ is rare and exceptional.\n"
    "- Confidence reflects evidence quality and your domain certainty, not enthusiasm.\n"
    "- Never invent competitors, market figures, or quotes."
)


@dataclass(slots=True)
class ClusterEvidence:
    """What the deep model sees about a pain cluster."""

    cluster_id: str
    canonical_statement: str
    support_count: int
    avg_severity: float
    industry: str | None
    # (post_index, source, community, quote/statement) — top-N by severity.
    posts: list[dict[str, Any]]
    # From the trend agent: mention counts over the last N days.
    daily_mentions: list[int]
    # Known solutions extracted from the cluster's posts (stage 10 outputs).
    known_solutions: list[str]

    def to_prompt(self) -> str:
        post_lines = "\n".join(
            f"[{p['index']}] ({p['source']}/{p.get('community') or '-'}) {p['statement']}"
            + (f' — "{p["quote"]}"' if p.get("quote") else "")
            for p in self.posts
        )
        return (
            f"## Pain cluster\n"
            f"canonical problem: {self.canonical_statement}\n"
            f"industry: {self.industry or 'unknown'}\n"
            f"supporting posts: {self.support_count} "
            f"(avg severity {self.avg_severity:.2f})\n"
            f"daily mentions, oldest→newest: {self.daily_mentions}\n"
            f"solutions users mention today: {', '.join(self.known_solutions) or 'none found'}\n\n"
            f"## Evidence posts\n{post_lines}"
        )


# ── Stage 12: opportunity generation ─────────────────────────────────────


class GeneratedOpportunity(BaseModel):
    viable: bool = Field(
        description="False if this cluster does not support a real business opportunity "
        "(too niche, already solved well, not monetizable)."
    )
    title: str = Field(description="Product-style name for the opportunity, <=8 words.")
    thesis: str = Field(description="One sentence: why this, why now.")
    description: str = Field(
        description="2-3 paragraphs: the problem, who has it, what to build, wedge vs. "
        "incumbents. Cite evidence posts by [index]."
    )
    target_customer: str
    suggested_solution: str = Field(description="Concrete first product, not a vision.")
    rejection_reason: str = Field(description="If viable is false, why. Else empty.")


async def generate_opportunity(
    llm: BaseLLMClient, evidence: ClusterEvidence
) -> tuple[GeneratedOpportunity, LLMUsage]:
    result = await llm.extract(
        system=OPPORTUNITY_SYSTEM,
        user=(
            f"{evidence.to_prompt()}\n\n## Task\n"
            "Assess whether this pain cluster supports a startup opportunity, and if so, "
            "define it."
        ),
        schema=GeneratedOpportunity,
        tier=ModelTier.DEEP,
        max_tokens=3000,
    )
    return result.data, result.usage


# ── Stages 14 + 15: business scoring & market estimation ────────────────


class ExplainedScore(BaseModel):
    value: float = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    reasoning: str = Field(description="2-4 sentences. Reference evidence posts by [index].")
    evidence_indexes: list[int] = Field(
        description="Indexes of the evidence posts this score rests on."
    )


class BusinessScores(BaseModel):
    """Stage 14 — every component score, each with its own explanation."""

    pain: ExplainedScore = Field(description="Severity x frequency of the underlying pain.")
    competition: ExplainedScore = Field(
        description="How crowded/entrenched the space is. 100 = brutally competitive."
    )
    novelty: ExplainedScore = Field(
        description="How under-explored this angle is relative to known solutions."
    )
    revenue_potential: ExplainedScore = Field(
        description="Willingness-to-pay signals: budget language, business impact, urgency."
    )
    virality_potential: ExplainedScore = Field(
        description="Would users talk about this? Engagement signals in evidence."
    )
    known_competitors: list[str] = Field(
        description="Competitors identifiable FROM THE EVIDENCE or common knowledge; "
        "never invented names."
    )


class MarketEstimate(BaseModel):
    """Stage 15 — order-of-magnitude market sizing, honestly uncertain."""

    market_size: ExplainedScore = Field(
        description="Relative market attractiveness 0-100 given the TAM band."
    )
    tam_band: str = Field(
        description="Order-of-magnitude TAM: '<$10M', '$10M-$100M', '$100M-$1B', '>$1B'."
    )
    comparables: list[str] = Field(description="Real companies/markets used as sizing anchors.")
    sizing_logic: str = Field(description="The napkin math, stated explicitly.")


async def score_opportunity(
    llm: BaseLLMClient,
    evidence: ClusterEvidence,
    opportunity_title: str,
    opportunity_thesis: str,
) -> tuple[BusinessScores, MarketEstimate, list[LLMUsage]]:
    header = (
        f"{evidence.to_prompt()}\n\n## Opportunity under evaluation\n"
        f"title: {opportunity_title}\nthesis: {opportunity_thesis}\n"
    )
    business = await llm.extract(
        system=OPPORTUNITY_SYSTEM,
        user=f"{header}\n## Task\nScore this opportunity on every business dimension.",
        schema=BusinessScores,
        tier=ModelTier.DEEP,
        max_tokens=3000,
    )
    market = await llm.extract(
        system=OPPORTUNITY_SYSTEM,
        user=(
            f"{header}\nKnown competitors: "
            f"{', '.join(business.data.known_competitors) or 'none identified'}\n\n"
            "## Task\nEstimate the market for this opportunity."
        ),
        schema=MarketEstimate,
        tier=ModelTier.DEEP,
        max_tokens=1500,
    )
    return business.data, market.data, [business.usage, market.usage]


def scores_to_components(
    business: BusinessScores,
    market: MarketEstimate,
    trend_value: float,
    trend_confidence: float,
) -> dict[ScoreKind, tuple[float, float]]:
    """Assemble the (value, confidence) map consumed by the composite blend."""
    return {
        ScoreKind.PAIN: (business.pain.value, business.pain.confidence),
        ScoreKind.COMPETITION: (business.competition.value, business.competition.confidence),
        ScoreKind.NOVELTY: (business.novelty.value, business.novelty.confidence),
        ScoreKind.REVENUE_POTENTIAL: (
            business.revenue_potential.value,
            business.revenue_potential.confidence,
        ),
        ScoreKind.VIRALITY_POTENTIAL: (
            business.virality_potential.value,
            business.virality_potential.confidence,
        ),
        ScoreKind.MARKET_SIZE: (market.market_size.value, market.market_size.confidence),
        ScoreKind.TREND: (trend_value, trend_confidence),
    }
