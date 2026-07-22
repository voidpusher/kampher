"""Stages 3-8 — the "understanding" batch.

Topic, industry, entities, pain, emotion, intent. All six run for every
clean document and share ONE model call (the runner composes their schemas).
"""

from __future__ import annotations

from typing import ClassVar

from app.ai.pipeline.base import Batch, DocumentContext, LLMStage
from app.ai.pipeline.schemas import (
    EmotionAssessment,
    EntityExtraction,
    IndustryClassification,
    IntentAssessment,
    PainAssessment,
    TopicClassification,
)


class TopicStage(LLMStage):
    name: ClassVar[str] = "topics"
    batch = Batch.UNDERSTANDING
    output_schema = TopicClassification
    instruction = "Classify the document into 1-3 topics from the allowed topic list."

    def prompt_context(self, ctx: DocumentContext) -> str:
        return f"\nAllowed topic slugs: {', '.join(ctx.topic_slugs)}"


class IndustryStage(LLMStage):
    name: ClassVar[str] = "industries"
    batch = Batch.UNDERSTANDING
    output_schema = IndustryClassification
    instruction = "Classify the document into 1-2 industries from the allowed industry list."

    def prompt_context(self, ctx: DocumentContext) -> str:
        return f"\nAllowed industry slugs: {', '.join(ctx.industry_slugs)}"


class EntityStage(LLMStage):
    name: ClassVar[str] = "entities"
    batch = Batch.UNDERSTANDING
    output_schema = EntityExtraction
    instruction = (
        "Extract every company, product, technology, and person mentioned, with the "
        "author's sentiment toward each."
    )


class PainStage(LLMStage):
    name: ClassVar[str] = "pain"
    batch = Batch.UNDERSTANDING
    output_schema = PainAssessment
    instruction = "Assess whether the author expresses genuine pain or an unmet need."


class EmotionStage(LLMStage):
    name: ClassVar[str] = "emotion"
    batch = Batch.UNDERSTANDING
    output_schema = EmotionAssessment
    instruction = "Identify the author's dominant emotion(s)."


class IntentStage(LLMStage):
    name: ClassVar[str] = "intent"
    batch = Batch.UNDERSTANDING
    output_schema = IntentAssessment
    instruction = "Determine the author's dominant intent."
