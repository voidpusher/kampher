"""Incremental pain clustering — half of the Opportunity Agent.

Each unclustered problem is embedded and compared against existing cluster
centroids in Qdrant: close enough → join (centroid drifts toward the new
member via a weighted running mean); otherwise it seeds a new cluster. O(1)
per problem, no periodic full re-clustering required at ingest scale.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.embeddings.base import get_embedder
from app.core.logging import get_logger
from app.models import PostIndustry
from app.repositories.intelligence import IntelligenceRepository
from app.vector.store import Collection, get_vector_store

log = get_logger("service.clustering")

# Cosine similarity above which two problem statements are "the same pain".
# Tuned permissive-side: merging near-duplicates is cheaper than fragmenting
# real clusters below the opportunity-support threshold.
SIMILARITY_THRESHOLD = 0.80


class ClusteringService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repo = IntelligenceRepository(session)
        self.embedder = get_embedder()
        self.store = get_vector_store()

    def cluster_pending(self, batch_size: int = 200) -> dict[str, int]:
        problems = self.repo.unclustered_problems(limit=batch_size)
        if not problems:
            return {"assigned": 0, "created": 0}

        vectors = self.embedder.embed([p.statement for p in problems])
        assigned = created = 0

        for problem, vector in zip(problems, vectors, strict=True):
            nearest = self.store.nearest(Collection.PAIN_CLUSTERS, vector)
            if nearest is not None and nearest[1] >= SIMILARITY_THRESHOLD:
                cluster = self.repo.get_cluster(nearest[0])
                if cluster is not None:
                    self.repo.assign_to_cluster(problem, cluster)
                    self._drift_centroid(cluster.id, vector, cluster.support_count)
                    assigned += 1
                    continue
            cluster = self.repo.create_cluster(problem, self._problem_industry(problem.post_id))
            self.repo.assign_to_cluster(problem, cluster)
            self._write_centroid(cluster.id, vector, cluster.canonical_statement)
            created += 1

        log.info("clustering pass", assigned=assigned, created=created)
        return {"assigned": assigned, "created": created}

    def _write_centroid(self, cluster_id: uuid.UUID, vector: list[float], statement: str) -> None:
        self.store.upsert(
            Collection.PAIN_CLUSTERS,
            [
                (cluster_id, vector, {"statement": statement[:300]}),
            ],
        )

    def _drift_centroid(
        self, cluster_id: uuid.UUID, new_vector: list[float], new_count: int
    ) -> None:
        """centroid ← (centroid·(n-1) + v) / n — exact running mean."""
        current = self.store.retrieve_vector(Collection.PAIN_CLUSTERS, cluster_id)
        if current is None:
            self._write_centroid(cluster_id, new_vector, "")
            return
        n = max(new_count, 1)
        blended = [(c * (n - 1) + v) / n for c, v in zip(current, new_vector, strict=True)]
        self.store.upsert(Collection.PAIN_CLUSTERS, [(cluster_id, blended, {})])

    def _problem_industry(self, post_id: uuid.UUID) -> uuid.UUID | None:
        return self.session.scalar(
            select(PostIndustry.industry_id)
            .where(PostIndustry.post_id == post_id)
            .order_by(PostIndustry.confidence.desc())
            .limit(1)
        )
