"""Pipeline runner.

Executes local gate stages first, then merges each batch of runnable LLM
stages into a single composed structured-output call. One clean document with
pain costs exactly two model calls (understanding + extraction); an
informational document costs one; spam and foreign-language documents cost zero.
"""

from __future__ import annotations

from pydantic import BaseModel, create_model

from app.ai.llm.base import BaseLLMClient, ModelTier
from app.ai.pipeline.base import (
    Batch,
    DocumentContext,
    LLMStage,
    LocalStage,
    PipelineResult,
    PipelineStatus,
    StageResult,
)
from app.ai.pipeline.prompts import ANALYST_SYSTEM, document_block
from app.ai.pipeline.stages.extraction import (
    FeatureRequestStage,
    ProblemStage,
    SolutionStage,
)
from app.ai.pipeline.stages.language import LanguageStage
from app.ai.pipeline.stages.spam import SpamStage
from app.ai.pipeline.stages.understanding import (
    EmotionStage,
    EntityStage,
    IndustryStage,
    IntentStage,
    PainStage,
    TopicStage,
)
from app.core.logging import get_logger


class PipelineRunner:
    def __init__(self, llm: BaseLLMClient) -> None:
        self.llm = llm
        self.log = get_logger("pipeline")
        self.gates: list[LocalStage] = [LanguageStage(), SpamStage(llm)]
        self.llm_stages: list[LLMStage] = [
            TopicStage(),
            IndustryStage(),
            EntityStage(),
            PainStage(),
            EmotionStage(),
            IntentStage(),
            ProblemStage(),
            SolutionStage(),
            FeatureRequestStage(),
        ]

    async def run(self, ctx: DocumentContext) -> PipelineResult:
        results: list[StageResult] = []

        for gate in self.gates:
            result = await gate.run(ctx)
            results.append(result)
            ctx.outputs[result.stage] = result.output
            if result.gate_rejected:
                self.log.info(
                    "document gated",
                    post_id=ctx.post_id,
                    stage=result.stage,
                    reason=result.gate_reason,
                )
                return PipelineResult(
                    status=PipelineStatus.GATED,
                    gate_reason=result.gate_reason,
                    results=results,
                )

        # Batches run in order because extraction gating reads understanding output.
        for batch in (Batch.UNDERSTANDING, Batch.EXTRACTION):
            stages = [s for s in self.llm_stages if s.batch is batch and s.should_run(ctx)]
            if not stages:
                continue
            results.extend(await self._run_batch(ctx, stages))

        return PipelineResult(status=PipelineStatus.ENRICHED, gate_reason=None, results=results)

    async def _run_batch(self, ctx: DocumentContext, stages: list[LLMStage]) -> list[StageResult]:
        composed: type[BaseModel] = create_model(  # type: ignore[call-overload]
            "BatchExtraction",
            **{s.name: (s.output_schema, ...) for s in stages},
        )
        tasks = "\n".join(f"### {s.name}\n{s.instruction}{s.prompt_context(ctx)}" for s in stages)
        result = await self.llm.extract(
            system=ANALYST_SYSTEM,
            user=f"{document_block(ctx)}\n\n## Tasks\nComplete every task below.\n\n{tasks}",
            schema=composed,
            tier=ModelTier.FAST,
            max_tokens=4096,
        )

        out: list[StageResult] = []
        for i, stage in enumerate(stages):
            slice_data: BaseModel = getattr(result.data, stage.name)
            output = stage.postprocess(ctx, slice_data)
            ctx.outputs[stage.name] = output
            out.append(
                StageResult(
                    stage=stage.name,
                    output=output,
                    # Usage is attributed to the batch's first stage to avoid
                    # double-counting tokens when summing costs.
                    usage=result.usage if i == 0 else None,
                )
            )
        return out
