from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

from app.services.chat import ChatService, RetrievalPlan


class EmptySearch:
    def __init__(self) -> None:
        self.industry_filters: list[str | None] = []

    async def search_posts(self, query: str, **kwargs: Any) -> list[Any]:
        self.industry_filters.append(kwargs.get("industry_slug"))
        return []


async def test_retrieval_retries_without_empty_inferred_industry() -> None:
    service = object.__new__(ChatService)
    service.search = EmptySearch()  # type: ignore[assignment]
    service.session = object()  # type: ignore[assignment]
    plan = RetrievalPlan(
        search_queries=["authentication complaints"],
        include_opportunities=False,
        industry_slug="cybersecurity",
    )

    assert await service._retrieve_posts(plan) == []
    assert service.search.industry_filters == ["cybersecurity", None]


async def test_retrieval_without_industry_searches_once() -> None:
    service = object.__new__(ChatService)
    service.search = EmptySearch()  # type: ignore[assignment]
    service.session = object()  # type: ignore[assignment]
    plan = RetrievalPlan(
        search_queries=["authentication complaints"],
        include_opportunities=False,
        industry_slug=None,
    )

    assert await service._retrieve_posts(plan) == []
    assert service.search.industry_filters == [None]


def test_chat_plan_uses_question_without_llm_round_trip() -> None:
    plan = ChatService._build_plan("What authentication product should I build?")

    assert plan.search_queries == ["authentication"]
    assert plan.include_opportunities is False
    assert plan.industry_slug is None


def test_chat_plan_preserves_question_when_no_specific_terms_remain() -> None:
    question = "Which problems are rapidly increasing this month?"

    assert ChatService._build_plan(question).search_queries == [question]


async def test_chat_returns_cited_evidence_when_synthesis_fails() -> None:
    post = SimpleNamespace(
        id=uuid.uuid4(),
        source=SimpleNamespace(value="stackoverflow"),
        title="Authentication callback fails intermittently",
        body="Developers describe a recurring OAuth callback problem.",
        community="oauth-2.0",
        url="https://example.com/post",
    )
    service = object.__new__(ChatService)
    service.llm = SimpleNamespace(extract=AsyncMock(side_effect=RuntimeError("model busy")))
    service._retrieve_posts = AsyncMock(return_value=[post])  # type: ignore[method-assign]
    service._retrieve_opportunities = AsyncMock(return_value=[])  # type: ignore[method-assign]

    result = await service.ask("What authentication product should I build?")

    assert "## Problems worth solving" in result["answer"]
    assert "**Who has it:**" in result["answer"]
    assert "**Observed pain:**" in result["answer"]
    assert "**What to build:**" in result["answer"]
    assert "## Best starting point" in result["answer"]
    assert "[P1]" in result["answer"]
    assert result["cited_posts"][0]["id"] == str(post.id)


def test_chat_skips_second_vector_search_for_normal_builder_question() -> None:
    plan = ChatService._build_plan("What problems exist around authentication?")

    assert plan.include_opportunities is False


def test_chat_searches_generated_opportunities_when_explicitly_requested() -> None:
    plan = ChatService._build_plan("Show me scored opportunities in authentication")

    assert plan.include_opportunities is True


def test_chat_resolves_citation_cards_from_markdown_markers() -> None:
    posts = [SimpleNamespace(id=uuid.uuid4()), SimpleNamespace(id=uuid.uuid4())]
    opportunities = [SimpleNamespace(id=uuid.uuid4())]

    cited_posts, cited_opportunities = ChatService._resolve_citations(
        "The strongest evidence is here [P2], with an opportunity [O1].",
        posts,  # type: ignore[arg-type]
        opportunities,  # type: ignore[arg-type]
        post_ids=[],
        opportunity_ids=[],
    )

    assert cited_posts == [posts[1]]
    assert cited_opportunities == opportunities
