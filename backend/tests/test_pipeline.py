"""Pipeline behavior tests with a fake LLM client — no network, no cost."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import TypeVar

from pydantic import BaseModel

from app.ai.llm.base import BaseLLMClient, LLMResult, LLMUsage, ModelTier
from app.ai.pipeline.base import DocumentContext, PipelineStatus
from app.ai.pipeline.runner import PipelineRunner

T = TypeVar("T", bound=BaseModel)

UNDERSTANDING_PAYLOAD = {
    "topics": {"topics": [{"slug": "payments", "confidence": 0.9}]},
    "industries": {"industries": [{"slug": "saas", "confidence": 0.85}]},
    "entities": {"entities": []},
    "pain": {
        "has_pain": True,
        "intensity": 0.8,
        "evidence_quote": "I keep writing spreadsheet hacks",
    },
    "emotion": {"primary": "frustration", "secondary": None, "intensity": 0.7},
    "intent": {"intent": "requesting", "confidence": 0.8},
}

EXTRACTION_PAYLOAD = {
    "problem": {
        "has_problem": True,
        "statement": "SaaS founders cannot bill usage-based plans because tooling "
        "assumes flat subscriptions",
        "audience": "SaaS founders",
        "severity": 0.75,
    },
    "solution": {
        "mentioned_solutions": ["Stripe Billing"],
        "workaround": "spreadsheet hacks",
        "satisfaction_with_existing": 0.2,
    },
    "feature_requests": {"requests": []},
}

NO_PAIN_UNDERSTANDING = {
    **UNDERSTANDING_PAYLOAD,
    "pain": {"has_pain": False, "intensity": 0.0, "evidence_quote": ""},
    "intent": {"intent": "none", "confidence": 0.9},
    "emotion": {"primary": "neutral", "secondary": None, "intensity": 0.1},
}


class FakeLLM(BaseLLMClient):
    """Answers batch extractions from canned payloads keyed by schema fields."""

    def __init__(self, payloads: list[dict]) -> None:
        self.payloads = list(payloads)
        self.calls = 0

    async def extract(
        self,
        *,
        system: str,
        user: str,
        schema: type[T],
        tier: ModelTier = ModelTier.FAST,
        max_tokens: int = 2048,
    ) -> LLMResult[T]:
        self.calls += 1
        expected_fields = set(schema.model_fields)
        for payload in self.payloads:
            slice_payload = {k: v for k, v in payload.items() if k in expected_fields}
            if set(slice_payload) == expected_fields:
                return LLMResult(
                    data=schema.model_validate(slice_payload),
                    usage=LLMUsage(model="fake", input_tokens=10, output_tokens=10, latency_ms=1),
                )
        raise AssertionError(f"no fake payload matches schema fields {expected_fields}")


def make_ctx(body: str, title: str | None = "Help with billing") -> DocumentContext:
    from app.models.enums import Source

    return DocumentContext(
        post_id="00000000-0000-0000-0000-000000000001",
        source=Source.REDDIT,
        title=title,
        body=body,
        community="r/SaaS",
        posted_at=datetime.now(UTC),
        topic_slugs=["payments", "authentication"],
        industry_slugs=["saas", "fintech"],
    )


def test_non_english_document_is_gated_before_any_llm_call() -> None:
    llm = FakeLLM([])
    runner = PipelineRunner(llm)
    ctx = make_ctx(
        "Estoy buscando una herramienta para facturación recurrente en mi empresa, "
        "porque las opciones actuales son demasiado caras y complicadas de usar.",
        title="Ayuda con facturación",
    )
    result = asyncio.run(runner.run(ctx))
    assert result.status is PipelineStatus.GATED
    assert "language" in (result.gate_reason or "")
    assert llm.calls == 0


def test_obvious_spam_is_gated_without_llm() -> None:
    llm = FakeLLM([])
    runner = PipelineRunner(llm)
    ctx = make_ctx(
        "CLICK HERE!!! LIMITED TIME OFFER SIGN UP TODAY https://a.example "
        "https://b.example https://c.example EARN $9999 DM ME NOW GIVEAWAY",
        title=None,
    )
    result = asyncio.run(runner.run(ctx))
    assert result.status is PipelineStatus.GATED
    assert "spam" in (result.gate_reason or "")
    assert llm.calls == 0


def test_painful_document_runs_both_batches() -> None:
    llm = FakeLLM([UNDERSTANDING_PAYLOAD, EXTRACTION_PAYLOAD])
    runner = PipelineRunner(llm)
    ctx = make_ctx(
        "I am looking for a billing tool that supports usage-based pricing. "
        "I keep writing spreadsheet hacks and it is getting painful to maintain."
    )
    result = asyncio.run(runner.run(ctx))
    assert result.status is PipelineStatus.ENRICHED
    assert llm.calls == 2  # one understanding batch + one extraction batch
    problem = result.output("problem")
    assert problem is not None and problem["has_problem"] is True
    assert result.output("topics") == UNDERSTANDING_PAYLOAD["topics"]


def test_informational_document_skips_extraction_batch() -> None:
    llm = FakeLLM([NO_PAIN_UNDERSTANDING, EXTRACTION_PAYLOAD])
    runner = PipelineRunner(llm)
    ctx = make_ctx(
        "We published a comparison of invoice archiving rules across EU countries. "
        "The overview covers retention periods and audit expectations in detail."
    )
    result = asyncio.run(runner.run(ctx))
    assert result.status is PipelineStatus.ENRICHED
    assert llm.calls == 1  # extraction batch never ran
    assert result.output("problem") is None
