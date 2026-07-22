"""Report generation (Report Agent's brain).

Produces the structured sections AND a rendered markdown document in one
deep-tier call, grounded in the opportunity's evidence and existing scores.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.ai.llm.base import BaseLLMClient, LLMUsage, ModelTier
from app.ai.opportunity import OPPORTUNITY_SYSTEM, ClusterEvidence


class CompetitorNote(BaseModel):
    name: str
    positioning: str = Field(description="What they do and where they are weak, 1-2 sentences.")


class PainPointNote(BaseModel):
    description: str
    evidence_indexes: list[int]


class StartupIdea(BaseModel):
    name: str
    pitch: str = Field(description="One-sentence pitch.")
    wedge: str = Field(description="Why this wins against the status quo.")


class ReportSections(BaseModel):
    summary: str = Field(description="Executive summary, 3-5 sentences.")
    market_overview: str
    pain_points: list[PainPointNote]
    competitors: list[CompetitorNote] = Field(
        description="Only competitors from evidence or common knowledge; never invented."
    )
    pricing_landscape: str = Field(
        description="What users pay today and price sensitivity signals in the evidence."
    )
    missing_features: list[str]
    startup_ideas: list[StartupIdea] = Field(max_length=3)
    recommendations: str = Field(description="Concrete next steps for a founder, numbered.")


class GeneratedReport(BaseModel):
    sections: ReportSections
    content_md: str = Field(
        description="The full report as polished markdown: title, section headings, "
        "evidence citations as [index] footnotes."
    )


async def generate_report(
    llm: BaseLLMClient,
    evidence: ClusterEvidence,
    opportunity_title: str,
    opportunity_thesis: str,
    score_summary: str,
) -> tuple[GeneratedReport, LLMUsage]:
    result = await llm.extract(
        system=OPPORTUNITY_SYSTEM,
        user=(
            f"{evidence.to_prompt()}\n\n## Opportunity\n"
            f"title: {opportunity_title}\nthesis: {opportunity_thesis}\n"
            f"scores: {score_summary}\n\n"
            "## Task\nWrite the full opportunity report."
        ),
        schema=GeneratedReport,
        tier=ModelTier.DEEP,
        max_tokens=6000,
    )
    return result.data, result.usage
