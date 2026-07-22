"""Embedding service — the Embedding Agent's logic.

Vectorizes enriched posts and their extracted problems into Qdrant. Payloads
carry the filterable fields so hybrid search never round-trips to Postgres
for filtering.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.embeddings.base import get_embedder
from app.core.logging import get_logger
from app.core.text import truncate
from app.models import Post, PostIndustry, Problem
from app.vector.store import Collection, get_vector_store

log = get_logger("service.embedding")

_EMBED_CHARS = 2000  # embedding models truncate anyway; keep input predictable


class EmbeddingService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.embedder = get_embedder()
        self.store = get_vector_store()

    def embed_posts(self, post_ids: list[uuid.UUID]) -> int:
        posts = list(self.session.scalars(select(Post).where(Post.id.in_(post_ids))))
        if not posts:
            return 0

        industry_by_post = self._primary_industries([p.id for p in posts])
        texts = [truncate(f"{p.title or ''}\n{p.body}".strip(), _EMBED_CHARS) for p in posts]
        vectors = self.embedder.embed(texts)

        self.store.upsert(
            Collection.POSTS,
            [
                (
                    post.id,
                    vector,
                    {
                        "source": post.source.value,
                        "community": post.community,
                        "industry_slug": industry_by_post.get(post.id),
                        "posted_at_ts": post.posted_at.timestamp(),
                        "title": truncate(post.title or "", 200),
                        "has_pain_signal": bool(post.has_pain_signal),
                    },
                )
                for post, vector in zip(posts, vectors, strict=True)
            ],
        )
        return len(posts)

    def embed_problems(self, problem_ids: list[uuid.UUID]) -> int:
        problems = list(self.session.scalars(select(Problem).where(Problem.id.in_(problem_ids))))
        if not problems:
            return 0
        vectors = self.embedder.embed([p.statement for p in problems])
        self.store.upsert(
            Collection.PROBLEMS,
            [
                (
                    problem.id,
                    vector,
                    {
                        "post_id": str(problem.post_id),
                        "severity": problem.severity,
                        "statement": truncate(problem.statement, 300),
                    },
                )
                for problem, vector in zip(problems, vectors, strict=True)
            ],
        )
        return len(problems)

    def embed_opportunities(self, opportunity_ids: list[uuid.UUID]) -> int:
        from app.models import Opportunity

        opportunities = list(
            self.session.scalars(select(Opportunity).where(Opportunity.id.in_(opportunity_ids)))
        )
        if not opportunities:
            return 0
        texts = [f"{o.title}\n{o.thesis}\n{o.description}" for o in opportunities]
        vectors = self.embedder.embed([truncate(t, _EMBED_CHARS) for t in texts])
        self.store.upsert(
            Collection.OPPORTUNITIES,
            [
                (
                    opp.id,
                    vector,
                    {
                        "slug": opp.slug,
                        "title": opp.title,
                        "status": opp.status.value,
                        "composite_score": opp.composite_score,
                    },
                )
                for opp, vector in zip(opportunities, vectors, strict=True)
            ],
        )
        return len(opportunities)

    def _primary_industries(self, post_ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
        from app.models import Industry

        rows = self.session.execute(
            select(PostIndustry.post_id, Industry.slug)
            .join(Industry, Industry.id == PostIndustry.industry_id)
            .where(PostIndustry.post_id.in_(post_ids))
            .order_by(PostIndustry.confidence.desc())
        ).all()
        result: dict[uuid.UUID, str] = {}
        for post_id, slug in rows:
            result.setdefault(post_id, slug)
        return result
