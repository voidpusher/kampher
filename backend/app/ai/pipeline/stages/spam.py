"""Stage 2 — spam detection (gate).

Heuristics rule on the clear cases for free; only the ambiguous middle band
escalates to the fast model. At scale this keeps the LLM spam bill near zero
while never letting heuristics alone delete borderline content.
"""

from __future__ import annotations

from typing import ClassVar

from app.ai.llm.base import BaseLLMClient, ModelTier
from app.ai.pipeline.base import DocumentContext, LocalStage, StageResult
from app.ai.pipeline.prompts import ANALYST_SYSTEM, document_block
from app.ai.pipeline.schemas import SpamAssessment
from app.ai.pipeline.signals import spam_heuristic

_CLEAN_BELOW = 0.25
_SPAM_ABOVE = 0.75


class SpamStage(LocalStage):
    name: ClassVar[str] = "spam"

    def __init__(self, llm: BaseLLMClient) -> None:
        self.llm = llm

    async def run(self, ctx: DocumentContext) -> StageResult:
        estimate, reason = spam_heuristic(ctx.text)

        if estimate < _CLEAN_BELOW:
            return StageResult(
                stage=self.name,
                output={
                    "is_spam": False,
                    "method": "heuristic",
                    "reason": reason,
                },
            )
        if estimate > _SPAM_ABOVE:
            return StageResult(
                stage=self.name,
                output={"is_spam": True, "method": "heuristic", "reason": reason},
                gate_rejected=True,
                gate_reason=f"spam: {reason}",
            )

        # Ambiguous band → one cheap model call decides.
        result = await self.llm.extract(
            system=ANALYST_SYSTEM,
            user=f"{document_block(ctx)}\n\n## Task\nDecide whether this document is spam.",
            schema=SpamAssessment,
            tier=ModelTier.FAST,
            max_tokens=256,
        )
        verdict = result.data
        return StageResult(
            stage=self.name,
            output={"is_spam": verdict.is_spam, "method": "llm", "reason": verdict.reason},
            usage=result.usage,
            gate_rejected=verdict.is_spam,
            gate_reason=f"spam: {verdict.reason}" if verdict.is_spam else None,
        )
