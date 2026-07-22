"""Opportunity engine — stages 12-15 orchestrated over eligible pain clusters.

For each cluster with enough support and no opportunity yet:
generate (12) → trend-score (13, statistical) → business-score (14) →
market-estimate (15) → deterministic composite → persist with full reasoning.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.llm.client import get_llm_client
from app.ai.opportunity import (
    BusinessScores,
    ClusterEvidence,
    ExplainedScore,
    MarketEstimate,
    generate_opportunity,
    score_opportunity,
    scores_to_components,
)
from app.ai.scoring import composite_score, overall_confidence, trend_score
from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.text import slugify
from app.graph.service import GraphService
from app.models import Opportunity, PainCluster, Post, Problem
from app.models.enums import (
    EdgeRelation,
    NodeKind,
    OpportunityStatus,
    ScoreKind,
    TrendSubject,
)
from app.repositories.intelligence import IntelligenceRepository

log = get_logger("service.opportunity")

MIN_CLUSTER_SUPPORT = 3  # posts required before a cluster is "real"
ACTIVATION_SCORE = 55.0  # composite needed to surface in the feed
TREND_WINDOW_DAYS = 28


class OpportunityEngine:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repo = IntelligenceRepository(session)
        self.graph = GraphService(session)
        self.llm = get_llm_client()
        self.settings = get_settings()

    def run(self, max_clusters: int = 5) -> dict[str, int]:
        clusters = self.repo.clusters_ready_for_opportunity(
            min_support=MIN_CLUSTER_SUPPORT, limit=max_clusters
        )
        generated = rejected = 0
        for cluster in clusters:
            if self._process_cluster(cluster):
                generated += 1
            else:
                rejected += 1
        log.info("opportunity pass", generated=generated, rejected=rejected)
        return {"generated": generated, "rejected": rejected}

    def _process_cluster(self, cluster: PainCluster) -> bool:
        evidence = self._build_evidence(cluster)

        opportunity_spec, _ = asyncio.run(generate_opportunity(self.llm, evidence))
        if not opportunity_spec.viable:
            log.info(
                "cluster rejected as opportunity",
                cluster_id=str(cluster.id),
                reason=opportunity_spec.rejection_reason,
            )
            # Persist the rejection so the cluster isn't re-evaluated every pass.
            self._persist_rejection(cluster, opportunity_spec.rejection_reason)
            return False

        business, market, _ = asyncio.run(
            score_opportunity(
                self.llm,
                evidence,
                opportunity_spec.title,
                opportunity_spec.thesis,
            )
        )

        counts = self.repo.daily_problem_counts(cluster.id, TREND_WINDOW_DAYS)
        trend_value, velocity, acceleration = trend_score(counts)
        # Short series → low confidence in the trend, mechanically.
        trend_conf = min(sum(1 for c in counts if c > 0) / 7.0, 1.0)

        score_components = scores_to_components(business, market, trend_value, trend_conf)
        composite = composite_score(score_components)
        confidence = overall_confidence(score_components)

        opportunity = self.repo.create_opportunity(
            slug=self._unique_slug(opportunity_spec.title),
            title=opportunity_spec.title,
            thesis=opportunity_spec.thesis,
            description=opportunity_spec.description,
            target_customer=opportunity_spec.target_customer,
            suggested_solution=opportunity_spec.suggested_solution,
            pain_cluster_id=cluster.id,
            industry_id=cluster.industry_id,
            status=(
                OpportunityStatus.ACTIVE
                if composite >= ACTIVATION_SCORE
                else OpportunityStatus.CANDIDATE
            ),
            composite_score=composite,
            generated_by_model=self.settings.llm_model,
            meta={
                "tam_band": market.tam_band,
                "comparables": market.comparables,
                "sizing_logic": market.sizing_logic,
                "known_competitors": business.known_competitors,
                "velocity": velocity,
                "acceleration": acceleration,
            },
        )
        self._persist_scores(
            opportunity.id,
            evidence,
            business,
            market,
            trend_value,
            trend_conf,
            velocity,
            acceleration,
            composite,
            confidence,
            score_components,
        )
        self.repo.save_trend_snapshot(
            TrendSubject.PAIN_CLUSTER,
            cluster.id,
            window_start=cluster.last_seen_at or cluster.created_at,
            mention_count=sum(counts),
            velocity=velocity,
            acceleration=acceleration,
            avg_severity=cluster.avg_severity,
        )
        self._connect_graph(opportunity, cluster, business.known_competitors)
        return True

    # ── helpers ─────────────────────────────────────────────────────────

    def _build_evidence(self, cluster: PainCluster) -> ClusterEvidence:
        problems = self.repo.cluster_problems(cluster.id)
        posts_by_id = self._posts_for(problems)
        industry_slug = None
        if cluster.industry_id is not None:
            industry_slug = next(
                (
                    slug
                    for slug, iid in self.repo.industry_slugs().items()
                    if iid == cluster.industry_id
                ),
                None,
            )
        evidence_posts = []
        solutions: set[str] = set()
        for index, problem in enumerate(problems):
            post = posts_by_id.get(problem.post_id)
            evidence_posts.append(
                {
                    "index": index,
                    "post_id": str(problem.post_id),
                    "source": post.source.value if post else "unknown",
                    "community": post.community if post else None,
                    "statement": problem.statement,
                    "quote": problem.evidence_quote,
                }
            )
            if problem.current_workaround:
                solutions.add(problem.current_workaround)
        return ClusterEvidence(
            cluster_id=str(cluster.id),
            canonical_statement=cluster.canonical_statement,
            support_count=cluster.support_count,
            avg_severity=cluster.avg_severity,
            industry=industry_slug,
            posts=evidence_posts,
            daily_mentions=self.repo.daily_problem_counts(cluster.id, TREND_WINDOW_DAYS),
            known_solutions=sorted(solutions),
        )

    def _posts_for(self, problems: list[Problem]) -> dict[uuid.UUID, Post]:
        ids = [p.post_id for p in problems]
        rows = self.session.scalars(select(Post).where(Post.id.in_(ids)))
        return {p.id: p for p in rows}

    def _persist_scores(
        self,
        opportunity_id: uuid.UUID,
        evidence: ClusterEvidence,
        business: BusinessScores,
        market: MarketEstimate,
        trend_value: float,
        trend_conf: float,
        velocity: float,
        acceleration: float,
        composite: float,
        confidence: float,
        score_components: dict[ScoreKind, tuple[float, float]],
    ) -> None:
        def evidence_refs(score: ExplainedScore) -> dict[str, Any]:
            posts = []
            for index in score.evidence_indexes:
                if 0 <= index < len(evidence.posts):
                    p = evidence.posts[index]
                    posts.append({"post_id": p["post_id"], "quote": p.get("quote")})
            return {"posts": posts}

        explained: dict[ScoreKind, ExplainedScore] = {
            ScoreKind.PAIN: business.pain,
            ScoreKind.COMPETITION: business.competition,
            ScoreKind.NOVELTY: business.novelty,
            ScoreKind.REVENUE_POTENTIAL: business.revenue_potential,
            ScoreKind.VIRALITY_POTENTIAL: business.virality_potential,
            ScoreKind.MARKET_SIZE: market.market_size,
        }
        for kind, score in explained.items():
            self.repo.save_score(
                opportunity_id,
                kind,
                score.value,
                score.confidence,
                score.reasoning,
                evidence_refs(score),
            )
        self.repo.save_score(
            opportunity_id,
            ScoreKind.TREND,
            trend_value,
            trend_conf,
            f"Statistical trend over the last {TREND_WINDOW_DAYS} days: "
            f"velocity {velocity:+.2f} mentions/day, acceleration {acceleration:+.2f}. "
            f"Score is a logistic squash of growth relative to the baseline period.",
            {"velocity": velocity, "acceleration": acceleration},
        )
        self.repo.save_score(
            opportunity_id,
            ScoreKind.OPPORTUNITY,
            composite,
            confidence,
            "Deterministic confidence-weighted blend of the component scores "
            "(weights documented in app/ai/scoring.py). Not a model output.",
            {"components": {k.value: v[0] for k, v in score_components.items()}},
        )
        self.repo.save_score(
            opportunity_id,
            ScoreKind.CONFIDENCE,
            confidence * 100,
            confidence,
            "Weighted mean of component-score confidences.",
            {},
        )

    def _persist_rejection(self, cluster: PainCluster, reason: str) -> None:
        self.repo.create_opportunity(
            slug=self._unique_slug(f"rejected {cluster.label[:40]}"),
            title=cluster.label[:120],
            thesis="Cluster evaluated and rejected as a standalone opportunity.",
            description=reason or "Not viable.",
            pain_cluster_id=cluster.id,
            industry_id=cluster.industry_id,
            status=OpportunityStatus.ARCHIVED,
            composite_score=0.0,
            generated_by_model=self.settings.llm_model,
            meta={"rejection_reason": reason},
        )

    def _unique_slug(self, title: str) -> str:
        base = slugify(title)
        slug = base
        suffix = 2
        while self.repo.slug_exists(slug):
            slug = f"{base}-{suffix}"
            suffix += 1
        return slug

    def _connect_graph(
        self, opportunity: Opportunity, cluster: PainCluster, competitors: list[str]
    ) -> None:
        trend_node = (NodeKind.TREND, str(opportunity.id), opportunity.title)
        pain_node = (NodeKind.PAIN_POINT, str(cluster.id), cluster.label)
        self.graph.connect(trend_node, EdgeRelation.BELONGS_TO, pain_node)
        if opportunity.industry_id is not None:
            self.graph.connect(
                trend_node,
                EdgeRelation.TRENDING_IN,
                (NodeKind.INDUSTRY, str(opportunity.industry_id), str(opportunity.industry_id)),
            )
        for competitor in competitors:
            self.graph.connect(
                (NodeKind.COMPANY, slugify(competitor), competitor),
                EdgeRelation.COMPETES_WITH,
                trend_node,
            )
