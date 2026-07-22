"""Stages 9-11 — the "extraction" batch.

Problem, solution/workaround, and feature-request extraction. These only run
when the understanding batch (or the cheap signal heuristic) found pain or a
requesting/complaining/leaving intent — informational content skips them.
"""

from __future__ import annotations

from typing import ClassVar

from app.ai.pipeline.base import Batch, DocumentContext, LLMStage
from app.ai.pipeline.schemas import (
    FeatureRequestExtraction,
    ProblemExtraction,
    SolutionExtraction,
)
from app.ai.pipeline.signals import has_pain_signal
from app.models.enums import Intent

_PAIN_THRESHOLD = 0.35
_SIGNAL_INTENTS = {Intent.COMPLAINING.value, Intent.REQUESTING.value, Intent.LEAVING.value}


def _worth_extracting(ctx: DocumentContext) -> bool:
    pain = ctx.get("pain") or {}
    intent = (ctx.get("intent") or {}).get("intent", "")
    return (
        float(pain.get("intensity", 0.0)) >= _PAIN_THRESHOLD
        or intent in _SIGNAL_INTENTS
        or has_pain_signal(ctx.text)
    )


class ProblemStage(LLMStage):
    name: ClassVar[str] = "problem"
    batch = Batch.EXTRACTION
    output_schema = ProblemExtraction
    instruction = (
        "Extract the canonical problem the author faces, phrased so that two people "
        "describing the same problem produce near-identical statements."
    )

    def should_run(self, ctx: DocumentContext) -> bool:
        return _worth_extracting(ctx)


class SolutionStage(LLMStage):
    name: ClassVar[str] = "solution"
    batch = Batch.EXTRACTION
    output_schema = SolutionExtraction
    instruction = "Extract solutions or workarounds the author currently uses or mentions."

    def should_run(self, ctx: DocumentContext) -> bool:
        return _worth_extracting(ctx)


class FeatureRequestStage(LLMStage):
    name: ClassVar[str] = "feature_requests"
    batch = Batch.EXTRACTION
    output_schema = FeatureRequestExtraction
    instruction = "Extract explicit feature or capability requests."

    def should_run(self, ctx: DocumentContext) -> bool:
        return _worth_extracting(ctx)
