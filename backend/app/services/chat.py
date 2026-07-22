"""AI chat search: plan → retrieve → answer with citations.

The model first turns the user's question into a retrieval plan (search
queries + filters), we execute hybrid search + opportunity lookup, then the
model answers strictly from what was retrieved, citing post/opportunity ids.
"""

from __future__ import annotations

import asyncio
import re
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field
from sqlalchemy import select

from app.ai.embeddings.base import get_embedder
from app.ai.llm.base import ModelTier
from app.ai.llm.client import get_llm_client
from app.core.logging import get_logger
from app.core.text import truncate
from app.models import Opportunity, Post
from app.models.enums import OpportunityStatus
from app.services.search import SearchService
from app.vector.store import Collection, get_vector_store

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

_PLANNER_SYSTEM = (
    "You turn a user's question about market opportunities, user pain, and product "
    "gaps into a retrieval plan for Kampher's index of internet conversations and "
    "generated opportunities. Set industry_slug only when the user explicitly names "
    "an industry; do not infer one from a topic such as authentication or deployment. "
    "Otherwise set industry_slug to null."
)

_ANSWER_SYSTEM = """You are Kampher, a product-opportunity researcher for builders.
The user is looking for real problems people discuss online so they can decide what
to build. Do not behave like a general search engine and do not summarize links one
by one.

Using ONLY the retrieved context, combine related conversations into 3-5 distinct
problem opportunities. Use this exact decision-oriented structure:

## Problems worth solving
### 1. <specific problem stated as an unmet need>
- **Who has it:** <specific user or team>
- **Observed pain:** <what is failing, slow, costly, confusing, or manual>
- **Current workaround / gap:** <what they do now and why it is inadequate, if known>
- **What to build:** <a focused product direction, clearly labeled as an inference>
- **Signal strength:** High, Medium, or Early, with a short evidence-based reason

End with:
## Best starting point
Choose one problem and explain why it is the strongest candidate to validate first.

Cite evidence inline as [P<n>] for posts and [O<n>] for opportunities. Every factual
claim must have a citation. Separate observed evidence from your product inference.
Never invent frequency, market size, users, workarounds, or trends. When evidence is
thin, call it an early signal and say what the builder should validate next. If the
context does not explicitly describe a workaround, write "Not established in the
retrieved evidence" instead of guessing."""

_SYNTHESIS_TIMEOUT_SECONDS = 8
_QUERY_STOPWORDS = frozenset(
    {
        "a",
        "about",
        "an",
        "are",
        "build",
        "can",
        "complaining",
        "developers",
        "discussing",
        "do",
        "does",
        "for",
        "how",
        "i",
        "in",
        "increasing",
        "is",
        "market",
        "me",
        "month",
        "my",
        "of",
        "on",
        "people",
        "problem",
        "problems",
        "product",
        "rapidly",
        "should",
        "startup",
        "that",
        "the",
        "this",
        "to",
        "users",
        "what",
        "which",
        "why",
        "with",
    }
)
log = get_logger("services.chat")


class RetrievalPlan(BaseModel):
    search_queries: list[str] = Field(
        description="1-3 semantic search queries covering the question's angles.",
        min_length=1,
        max_length=3,
    )
    include_opportunities: bool = Field(
        description="Whether generated opportunities are relevant to this question."
    )
    industry_slug: str | None = Field(
        default=None, description="Industry filter if the question names one."
    )


class ChatAnswer(BaseModel):
    answer: str = Field(description="The answer in markdown, with [P<n>]/[O<n>] citations.")
    cited_post_ids: list[str]
    cited_opportunity_ids: list[str]


class ChatService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.search = SearchService(session)
        self.llm = get_llm_client()

    async def ask(self, question: str) -> dict[str, Any]:
        # The user's question is already an excellent semantic query. An LLM planner
        # added a full model round-trip, duplicated outage risk, and frequently inferred
        # filters that reduced recall. Keep retrieval deterministic and spend the one
        # bounded model call on synthesis instead.
        plan = self._build_plan(question)

        # Keep vector searches sequential: running both embedding workloads at once
        # exceeds the memory available on the free API instance.
        posts = await self._retrieve_posts(plan)
        opportunities = (
            await self._retrieve_opportunities(plan) if plan.include_opportunities else []
        )

        context_lines: list[str] = []
        for index, post in enumerate(posts, start=1):
            context_lines.append(
                f"[P{index}] id={post.id} ({post.source.value}/{post.community or '-'}) "
                f"{truncate((post.title or '') + ' — ' + post.body, 400)}"
            )
        for index, opp in enumerate(opportunities, start=1):
            context_lines.append(
                f"[O{index}] id={opp.id} score={opp.composite_score:.0f} {opp.title}: {opp.thesis}"
            )

        if not context_lines:
            return self._no_evidence_response()

        try:
            answer_result = await asyncio.wait_for(
                self.llm.extract(
                    system=_ANSWER_SYSTEM,
                    user=(
                        "## Retrieved context\n"
                        + "\n".join(context_lines)
                        + f"\n\n## Question\n{question}"
                    ),
                    schema=ChatAnswer,
                    tier=ModelTier.FAST,
                    max_tokens=1000,
                ),
                timeout=_SYNTHESIS_TIMEOUT_SECONDS,
            )
        except Exception as exc:  # The evidence fallback is the availability boundary.
            log.warning(
                "chat synthesis unavailable; returning retrieved evidence",
                error=type(exc).__name__,
            )
            return self._evidence_fallback(question, posts, opportunities)

        answer = answer_result.data
        cited_posts, cited_opportunities = self._resolve_citations(
            answer.answer,
            posts,
            opportunities,
            answer.cited_post_ids,
            answer.cited_opportunity_ids,
        )
        return {
            "answer": answer.answer,
            "cited_posts": [self._post_ref(post) for post in cited_posts],
            "cited_opportunities": [
                {"id": str(opp.id), "slug": opp.slug, "title": opp.title}
                for opp in cited_opportunities
            ],
        }

    @staticmethod
    def _resolve_citations(
        markdown: str,
        posts: list[Post],
        opportunities: list[Opportunity],
        post_ids: list[str],
        opportunity_ids: list[str],
    ) -> tuple[list[Post], list[Opportunity]]:
        """Resolve both UUIDs and the human-readable markers emitted in markdown."""
        post_id_set = set(post_ids)
        opportunity_id_set = set(opportunity_ids)
        post_indexes = {int(value) for value in re.findall(r"\[P(\d+)\]", markdown)}
        opportunity_indexes = {int(value) for value in re.findall(r"\[O(\d+)\]", markdown)}
        cited_posts = [
            post
            for index, post in enumerate(posts, start=1)
            if index in post_indexes or str(post.id) in post_id_set
        ]
        cited_opportunities = [
            opportunity
            for index, opportunity in enumerate(opportunities, start=1)
            if index in opportunity_indexes or str(opportunity.id) in opportunity_id_set
        ]
        return cited_posts, cited_opportunities

    @staticmethod
    def _build_plan(question: str) -> RetrievalPlan:
        lowered = question.casefold()
        opportunity_terms = ("opportunity", "opportunities", "scored idea", "report")
        return RetrievalPlan(
            search_queries=[ChatService._focus_query(question)],
            # Synthesizing build directions from posts is the fast default. Query the
            # second vector collection only when generated opportunities are requested.
            include_opportunities=any(term in lowered for term in opportunity_terms),
            industry_slug=None,
        )

    @staticmethod
    def _focus_query(question: str) -> str:
        tokens = re.findall(r"[a-z0-9+#.-]+", question.casefold())
        focused = [token for token in tokens if token not in _QUERY_STOPWORDS]
        return " ".join(focused) if focused else question.strip()

    def _evidence_fallback(
        self, question: str, posts: list[Post], opportunities: list[Opportunity]
    ) -> dict[str, Any]:
        lines = [
            "## Problems worth solving",
            "",
        ]
        for index, post in enumerate(posts[:6], start=1):
            title = post.title or truncate(post.body, 90) or "Untitled conversation"
            observed_pain = truncate(post.body, 220) if post.body else title
            community = post.community or post.source.value
            lines.extend(
                [
                    f"### {index}. {title}",
                    f"- **Who has it:** People discussing this in {community}. [P{index}]",
                    f"- **Observed pain:** {observed_pain} [P{index}]",
                    "- **What to build:** Investigate a focused tool that removes this "
                    "failure or manual step. This is a product inference; validate the "
                    "workflow with people reporting it.",
                    "- **Signal strength:** Early — one directly relevant conversation "
                    "was retrieved, but recurrence still needs validation.",
                    "",
                ]
            )

        if opportunities:
            lines.extend(["## Existing opportunity signals", ""])
        for index, opportunity in enumerate(opportunities[:3], start=1):
            lines.append(
                f"- **{opportunity.title}:** {truncate(opportunity.thesis, 180)} [O{index}]"
            )
        lines.extend(
            [
                "",
                "## Best starting point",
                (
                    f"Start with **{posts[0].title or 'the first problem signal'}** because "
                    f"it is the highest-ranked evidence for _{question}_. Interview the "
                    "person describing it, confirm how often it occurs, and learn what "
                    "they use now before choosing a solution. [P1]"
                ),
                "",
                "This is an evidence-first fallback while AI synthesis is busy. Build "
                "directions are hypotheses, not claims from the cited authors.",
            ]
        )
        return {
            "answer": "\n".join(lines),
            "cited_posts": [self._post_ref(post) for post in posts[:6]],
            "cited_opportunities": [
                {"id": str(opp.id), "slug": opp.slug, "title": opp.title}
                for opp in opportunities[:3]
            ],
        }

    @staticmethod
    def _no_evidence_response() -> dict[str, Any]:
        return {
            "answer": (
                "Kampher could not find relevant evidence in the indexed corpus for that "
                "question. Try naming a technology, workflow, or customer problem more directly."
            ),
            "cited_posts": [],
            "cited_opportunities": [],
        }

    async def _retrieve_posts(self, plan: RetrievalPlan) -> list[Post]:
        seen: set[uuid.UUID] = set()
        ordered_ids: list[uuid.UUID] = []
        for query in plan.search_queries:
            hits = await self.search.search_posts(
                query, mode="hybrid", limit=6, industry_slug=plan.industry_slug
            )
            # The planner may infer a plausible industry that has no tagged posts yet.
            # Preserve recall by retrying without that optional filter.
            if not hits and plan.industry_slug:
                hits = await self.search.search_posts(query, mode="hybrid", limit=6)
            for hit in hits:
                if hit.post_id not in seen:
                    seen.add(hit.post_id)
                    ordered_ids.append(hit.post_id)
        if not ordered_ids:
            return []
        rows = await self.session.scalars(select(Post).where(Post.id.in_(ordered_ids)))
        by_id = {p.id: p for p in rows}
        return [by_id[pid] for pid in ordered_ids if pid in by_id][:12]

    async def _retrieve_opportunities(self, plan: RetrievalPlan) -> list[Opportunity]:
        def _semantic_ids() -> list[uuid.UUID]:
            vector = get_embedder().embed_query(" ".join(plan.search_queries))
            hits = get_vector_store().search(Collection.OPPORTUNITIES, vector, limit=5)
            return [hit[0] for hit in hits]

        ids = await asyncio.to_thread(_semantic_ids)
        stmt = select(Opportunity).where(Opportunity.status == OpportunityStatus.ACTIVE)
        stmt = (
            stmt.where(Opportunity.id.in_(ids))
            if ids
            else stmt.order_by(Opportunity.composite_score.desc()).limit(5)
        )
        return list(await self.session.scalars(stmt))

    @staticmethod
    def _post_ref(post: Post) -> dict[str, Any]:
        return {
            "id": str(post.id),
            "source": post.source.value,
            "title": post.title,
            "url": post.url,
        }
