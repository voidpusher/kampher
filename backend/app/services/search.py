"""Search service: keyword (Postgres FTS), semantic (Qdrant), hybrid (RRF).

Hybrid uses Reciprocal Rank Fusion — rank-based fusion is robust to the fact
that BM25/ts_rank scores and cosine similarities live on incomparable scales.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from typing import Literal

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embeddings.base import get_embedder
from app.models import Post
from app.vector.store import Collection, get_vector_store

SearchMode = Literal["keyword", "semantic", "hybrid"]

_RRF_K = 60  # standard damping constant from the RRF paper


@dataclass(slots=True)
class SearchHit:
    post_id: uuid.UUID
    score: float
    matched_by: str


def rrf_fuse(rankings: list[list[uuid.UUID]], k: int = _RRF_K) -> list[tuple[uuid.UUID, float]]:
    """Fuse ranked id lists: score(d) = Σ 1/(k + rank_i(d))."""
    scores: dict[uuid.UUID, float] = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores.items(), key=lambda item: item[1], reverse=True)


class SearchService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.store = get_vector_store()

    async def search_posts(
        self,
        query: str,
        mode: SearchMode = "hybrid",
        limit: int = 20,
        source: str | None = None,
        community: str | None = None,
        industry_slug: str | None = None,
    ) -> list[SearchHit]:
        if not query.strip():
            ids = await self._keyword("", limit, source, community)
            return [SearchHit(pid, 1.0 / (i + 1), "community") for i, pid in enumerate(ids)]
        if mode == "keyword":
            ids = await self._keyword(query, limit, source, community)
            return [SearchHit(pid, 1.0 / (i + 1), "keyword") for i, pid in enumerate(ids)]
        if mode == "semantic":
            ids = await self._semantic(query, limit, source, community, industry_slug)
            return [SearchHit(pid, 1.0 / (i + 1), "semantic") for i, pid in enumerate(ids)]

        keyword_ids, semantic_ids = await asyncio.gather(
            self._keyword(query, limit * 2, source, community),
            self._semantic(query, limit * 2, source, community, industry_slug),
        )
        fused = rrf_fuse([keyword_ids, semantic_ids])[:limit]
        semantic_set = set(semantic_ids)
        keyword_set = set(keyword_ids)
        return [
            SearchHit(
                pid,
                score,
                "both"
                if pid in semantic_set and pid in keyword_set
                else "semantic"
                if pid in semantic_set
                else "keyword",
            )
            for pid, score in fused
        ]

    async def _keyword(
        self, query: str, limit: int, source: str | None, community: str | None
    ) -> list[uuid.UUID]:
        stmt: Select[tuple[uuid.UUID]] = select(Post.id)
        if query.strip():
            ts_query = func.websearch_to_tsquery("english", query)
            stmt = stmt.where(Post.search_vector.op("@@")(ts_query)).order_by(
                func.ts_rank_cd(Post.search_vector, ts_query).desc()
            )
        else:
            stmt = stmt.order_by(Post.posted_at.desc())
        if source:
            stmt = stmt.where(Post.source == source)
        if community:
            stmt = stmt.where(Post.community == community)
        return list(await self.session.scalars(stmt.limit(limit)))

    async def _semantic(
        self,
        query: str,
        limit: int,
        source: str | None,
        community: str | None,
        industry_slug: str | None,
    ) -> list[uuid.UUID]:
        # Embedding + Qdrant clients are sync; keep the event loop free.
        def _run() -> list[uuid.UUID]:
            vector = get_embedder().embed_query(query)
            hits = self.store.search(
                Collection.POSTS,
                vector,
                limit=limit,
                source=source,
                community=community,
                industry_slug=industry_slug,
            )
            return [hit[0] for hit in hits]

        return await asyncio.to_thread(_run)
