"""Structured-output schemas for the document-level pipeline stages.

Field descriptions are not documentation sugar — they are compiled into the
JSON schema the model is forced to fill, so they are the per-field prompt.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.enums import Emotion, EntityType, Intent


class TopicLabel(BaseModel):
    slug: str = Field(description="Topic slug, exactly as given in the allowed list.")
    confidence: float = Field(ge=0, le=1)


class TopicClassification(BaseModel):
    """Stage 3 — topic classification (taxonomy-constrained)."""

    topics: list[TopicLabel] = Field(
        description="1-3 best-fitting topics from the allowed list, most relevant first.",
        max_length=3,
    )


class IndustryLabel(BaseModel):
    slug: str = Field(description="Industry slug, exactly as given in the allowed list.")
    confidence: float = Field(ge=0, le=1)


class IndustryClassification(BaseModel):
    """Stage 4 — industry classification (taxonomy-constrained)."""

    industries: list[IndustryLabel] = Field(
        description="1-2 best-fitting industries from the allowed list.",
        max_length=2,
    )


class ExtractedEntity(BaseModel):
    kind: EntityType
    name: str = Field(description="Canonical name, e.g. 'Stripe' not 'stripe's'.")
    surface_text: str = Field(description="Exact text as it appears in the document.")
    sentiment: float = Field(
        ge=-1,
        le=1,
        description="Author's sentiment toward this entity: -1 hostile, 0 neutral, 1 positive.",
    )
    context_quote: str = Field(
        description="Shortest verbatim quote (<=150 chars) showing the mention in context."
    )


class EntityExtraction(BaseModel):
    """Stage 5 — entity extraction."""

    entities: list[ExtractedEntity] = Field(
        description="Companies, products, technologies and (unnamed-ok) people mentioned. "
        "Empty list if none.",
    )


class PainAssessment(BaseModel):
    """Stage 6 — pain detection."""

    has_pain: bool = Field(description="Does the author express a real unmet need or pain?")
    intensity: float = Field(
        ge=0,
        le=1,
        description="0 = no pain, 0.3 = mild annoyance, 0.6 = recurring friction with "
        "workarounds, 0.9+ = desperate / blocking / costing money.",
    )
    evidence_quote: str = Field(
        description="Verbatim quote showing the pain. Empty string if has_pain is false."
    )


class EmotionAssessment(BaseModel):
    """Stage 7 — emotion detection."""

    primary: Emotion
    secondary: Emotion | None = None
    intensity: float = Field(ge=0, le=1)


class IntentAssessment(BaseModel):
    """Stage 8 — intent detection."""

    intent: Intent = Field(
        description="Author's dominant intent: buying (looking to purchase/adopt), "
        "complaining, comparing options, requesting a feature, recommending, "
        "leaving a product, or none."
    )
    confidence: float = Field(ge=0, le=1)


class ProblemExtraction(BaseModel):
    """Stage 9 — problem extraction."""

    has_problem: bool
    statement: str = Field(
        description="Canonical one-sentence problem statement in the form "
        "'<audience> cannot/struggles to <job> because <blocker>'. "
        "Empty string if has_problem is false."
    )
    audience: str = Field(description="Who has this problem, e.g. 'indie SaaS founders'.")
    severity: float = Field(ge=0, le=1, description="How badly this blocks the audience.")


class SolutionExtraction(BaseModel):
    """Stage 10 — solution/workaround extraction."""

    mentioned_solutions: list[str] = Field(
        description="Products/approaches the author currently uses or considered. Empty if none."
    )
    workaround: str = Field(
        description="The manual workaround the author uses today, if described. Else empty."
    )
    satisfaction_with_existing: float = Field(
        ge=0,
        le=1,
        description="How satisfied the author is with existing options. 0 if none exist.",
    )


class ExtractedFeatureRequest(BaseModel):
    product: str = Field(description="Product the feature is requested for; empty if generic.")
    description: str = Field(description="The requested capability, one sentence.")
    urgency: float = Field(ge=0, le=1)
    evidence_quote: str = Field(description="Verbatim quote of the ask, <=200 chars.")


class FeatureRequestExtraction(BaseModel):
    """Stage 11 — feature request extraction."""

    requests: list[ExtractedFeatureRequest] = Field(
        description="Explicit feature/capability asks. Empty list if none."
    )


class SpamAssessment(BaseModel):
    """Stage 2 escalation — LLM ruling when heuristics are uncertain."""

    is_spam: bool = Field(
        description="True for promotion, affiliate bait, engagement farming, bot output, "
        "or content-free posts. Genuine questions/complaints are never spam."
    )
    reason: str
