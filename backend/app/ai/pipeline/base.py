"""Pipeline stage contract.

The pipeline is pure: stages read a ``DocumentContext`` and return
``StageResult``s — no database access inside stages. The worker layer
persists results. That keeps every stage unit-testable with plain objects.

Two stage families:
- ``LocalStage``   — deterministic, free (language, spam heuristics, signal gate).
- ``LLMStage``     — declares a Pydantic ``output_schema`` + an ``instruction``
                     prompt fragment, and is assigned to a *batch*. The runner
                     merges all runnable stages of a batch into ONE model call
                     (composed JSON schema), then hands each stage its slice.
                     Stages stay independently re-runnable via ``run_standalone``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any, ClassVar

from pydantic import BaseModel

from app.ai.llm.base import BaseLLMClient, LLMUsage, ModelTier
from app.models.enums import Source


@dataclass(slots=True)
class DocumentContext:
    """Everything a stage may look at. Immutable input + accumulated outputs."""

    post_id: str
    source: Source
    title: str | None
    body: str
    community: str | None
    posted_at: datetime
    metrics: dict[str, Any] = field(default_factory=dict)
    # Taxonomy the classification stages are constrained to.
    topic_slugs: list[str] = field(default_factory=list)
    industry_slugs: list[str] = field(default_factory=list)
    # stage name -> output dict, filled as the pipeline advances.
    outputs: dict[str, dict[str, Any]] = field(default_factory=dict)

    @property
    def text(self) -> str:
        return f"{self.title}\n\n{self.body}".strip() if self.title else self.body

    def get(self, stage_name: str) -> dict[str, Any] | None:
        return self.outputs.get(stage_name)


@dataclass(slots=True)
class StageResult:
    stage: str
    output: dict[str, Any]
    usage: LLMUsage | None = None
    # A gate stage sets this to stop the pipeline (doc is spam / wrong language).
    gate_rejected: bool = False
    gate_reason: str | None = None


class PipelineStatus(StrEnum):
    ENRICHED = "enriched"
    GATED = "gated"


@dataclass(slots=True)
class PipelineResult:
    status: PipelineStatus
    gate_reason: str | None
    results: list[StageResult]

    def output(self, stage_name: str) -> dict[str, Any] | None:
        for r in self.results:
            if r.stage == stage_name:
                return r.output
        return None


class Stage(ABC):
    name: ClassVar[str]

    def should_run(self, ctx: DocumentContext) -> bool:
        return True


class LocalStage(Stage):
    @abstractmethod
    async def run(self, ctx: DocumentContext) -> StageResult: ...


class Batch(StrEnum):
    # Stages 3-8: always run for clean documents.
    UNDERSTANDING = "understanding"
    # Stages 9-11: only run when understanding found pain/intent signal.
    EXTRACTION = "extraction"


class LLMStage(Stage):
    output_schema: ClassVar[type[BaseModel]]
    instruction: ClassVar[str]
    batch: ClassVar[Batch]
    tier: ClassVar[ModelTier] = ModelTier.FAST

    def prompt_context(self, ctx: DocumentContext) -> str:
        """Extra per-stage prompt material (e.g. the allowed taxonomy)."""
        return ""

    def postprocess(self, ctx: DocumentContext, data: BaseModel) -> dict[str, Any]:
        """Turn the validated model slice into the persisted output dict."""
        return data.model_dump(mode="json")

    async def run_standalone(self, ctx: DocumentContext, llm: BaseLLMClient) -> StageResult:
        """Re-run just this stage (backfills, evals) outside the batch path."""
        from app.ai.pipeline.prompts import ANALYST_SYSTEM, document_block

        result = await llm.extract(
            system=ANALYST_SYSTEM,
            user=(
                f"{document_block(ctx)}\n\n## Task\n{self.instruction}\n{self.prompt_context(ctx)}"
            ),
            schema=self.output_schema,
            tier=self.tier,
        )
        return StageResult(
            stage=self.name,
            output=self.postprocess(ctx, result.data),
            usage=result.usage,
        )
