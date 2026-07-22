"""Enrichment service — runs the AI pipeline on one post and persists
everything it produced: stage outputs, taxonomy links, entities, problems,
feature requests, and knowledge-graph edges.

The pipeline itself is pure (no DB); this service is the boundary where its
results become relational data.
"""

from __future__ import annotations

import asyncio
import uuid

from sqlalchemy.orm import Session

from app.ai.llm.client import get_llm_client
from app.ai.pipeline.base import DocumentContext, PipelineResult, PipelineStatus
from app.ai.pipeline.runner import PipelineRunner
from app.core.config import get_settings
from app.core.logging import get_logger
from app.graph.service import GraphService
from app.models import FeatureRequest, Post, PostIndustry, PostTopic, Problem
from app.models.enums import (
    EdgeRelation,
    EnrichmentStatus,
    EntityType,
    NodeKind,
)
from app.repositories.entities import EntityRepository
from app.repositories.ingestion import IngestionRepository
from app.repositories.intelligence import IntelligenceRepository

log = get_logger("service.enrichment")

_HOSTILE_SENTIMENT = -0.4


class EnrichmentService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.settings = get_settings()
        self.ingestion = IngestionRepository(session)
        self.intelligence = IntelligenceRepository(session)
        self.entities = EntityRepository(session)
        self.graph = GraphService(session)

    def enrich_post(self, post_id: uuid.UUID) -> str:
        post = self.ingestion.get_post(post_id)
        if post is None:
            log.warning("post vanished before enrichment", post_id=str(post_id))
            return "missing"

        topic_map = self.intelligence.topic_slugs()
        industry_map = self.intelligence.industry_slugs()

        ctx = DocumentContext(
            post_id=str(post.id),
            source=post.source,
            title=post.title,
            body=post.body,
            community=post.community,
            posted_at=post.posted_at,
            metrics=post.metrics,
            topic_slugs=sorted(topic_map),
            industry_slugs=sorted(industry_map),
        )

        runner = PipelineRunner(get_llm_client())
        result = asyncio.run(runner.run(ctx))

        self._persist_stage_outputs(post, result)

        if result.status is PipelineStatus.GATED:
            self._apply_gate(post, result)
            return "gated"

        self._apply_enrichment(post, result, topic_map, industry_map)
        post.enrichment_status = EnrichmentStatus.ENRICHED
        post.pipeline_version = self.settings.pipeline_version
        return "enriched"

    # ── persistence helpers ─────────────────────────────────────────────

    def _persist_stage_outputs(self, post: Post, result: PipelineResult) -> None:
        for stage_result in result.results:
            usage = stage_result.usage
            self.ingestion.save_enrichment(
                post_id=post.id,
                stage=stage_result.stage,
                pipeline_version=self.settings.pipeline_version,
                output=stage_result.output,
                model=usage.model if usage else None,
                input_tokens=usage.input_tokens if usage else None,
                output_tokens=usage.output_tokens if usage else None,
                latency_ms=usage.latency_ms if usage else None,
            )

    def _apply_gate(self, post: Post, result: PipelineResult) -> None:
        language = result.output("language") or {}
        spam = result.output("spam") or {}
        post.language = language.get("language")
        if "is_spam" in spam:
            post.is_spam = bool(spam["is_spam"])
        post.enrichment_status = EnrichmentStatus.GATED
        post.pipeline_version = self.settings.pipeline_version

    def _apply_enrichment(
        self,
        post: Post,
        result: PipelineResult,
        topic_map: dict[str, uuid.UUID],
        industry_map: dict[str, uuid.UUID],
    ) -> None:
        post.language = (result.output("language") or {}).get("language")
        post.is_spam = False

        primary_industry_id = self._apply_taxonomy(post, result, topic_map, industry_map)
        self._apply_entities(post, result)

        pain = result.output("pain") or {}
        post.has_pain_signal = bool(pain.get("has_pain"))

        self._apply_problem(post, result, primary_industry_id)
        self._apply_feature_requests(post, result)

    def _apply_taxonomy(
        self,
        post: Post,
        result: PipelineResult,
        topic_map: dict[str, uuid.UUID],
        industry_map: dict[str, uuid.UUID],
    ) -> uuid.UUID | None:
        for topic in (result.output("topics") or {}).get("topics", []):
            topic_id = topic_map.get(topic["slug"])
            if topic_id:
                self.session.merge(
                    PostTopic(
                        post_id=post.id,
                        topic_id=topic_id,
                        confidence=topic["confidence"],
                    )
                )

        primary_industry_id: uuid.UUID | None = None
        for industry in (result.output("industries") or {}).get("industries", []):
            industry_id = industry_map.get(industry["slug"])
            if industry_id:
                if primary_industry_id is None:
                    primary_industry_id = industry_id
                self.session.merge(
                    PostIndustry(
                        post_id=post.id,
                        industry_id=industry_id,
                        confidence=industry["confidence"],
                    )
                )
        return primary_industry_id

    def _apply_entities(self, post: Post, result: PipelineResult) -> None:
        for entity in (result.output("entities") or {}).get("entities", []):
            entity_type = EntityType(entity["kind"])
            entity_id = self.entities.resolve(entity_type, entity["name"])
            self.entities.add_mention(
                post_id=post.id,
                entity_type=entity_type,
                entity_id=entity_id,
                surface_text=entity["surface_text"],
                sentiment=entity.get("sentiment"),
                context_quote=entity.get("context_quote"),
            )
            if entity_id is None:
                continue
            node_kind = {
                EntityType.COMPANY: NodeKind.COMPANY,
                EntityType.PRODUCT: NodeKind.PRODUCT,
                EntityType.TECHNOLOGY: NodeKind.TECHNOLOGY,
            }.get(entity_type)
            if node_kind is None:
                continue
            author_key = str(post.author_id or post.id)
            relation = (
                EdgeRelation.COMPLAINS_ABOUT
                if (entity.get("sentiment") or 0) < _HOSTILE_SENTIMENT
                else EdgeRelation.MENTIONS
            )
            self.graph.connect(
                (NodeKind.AUTHOR, author_key, author_key),
                relation,
                (node_kind, str(entity_id), entity["name"]),
            )

    def _apply_problem(
        self, post: Post, result: PipelineResult, industry_id: uuid.UUID | None
    ) -> None:
        problem_out = result.output("problem") or {}
        if not problem_out.get("has_problem"):
            return
        pain = result.output("pain") or {}
        solution = result.output("solution") or {}
        problem = Problem(
            post_id=post.id,
            statement=problem_out["statement"],
            severity=float(problem_out.get("severity") or pain.get("intensity") or 0.0),
            audience=problem_out.get("audience") or None,
            current_workaround=solution.get("workaround") or None,
            evidence_quote=pain.get("evidence_quote") or None,
        )
        self.session.add(problem)
        self.session.flush()

        problem_node = (NodeKind.PROBLEM, str(problem.id), problem.statement[:120])
        if industry_id is not None:
            self.graph.connect(
                problem_node,
                EdgeRelation.BELONGS_TO,
                (NodeKind.INDUSTRY, str(industry_id), str(industry_id)),
            )
        for solution_name in solution.get("mentioned_solutions", []):
            self.graph.connect(
                (NodeKind.PRODUCT, self._slug(solution_name), solution_name),
                EdgeRelation.SOLVES,
                problem_node,
            )

    def _apply_feature_requests(self, post: Post, result: PipelineResult) -> None:
        for request in (result.output("feature_requests") or {}).get("requests", []):
            product_id = (
                self.entities.resolve(EntityType.PRODUCT, request["product"])
                if request.get("product")
                else None
            )
            self.session.add(
                FeatureRequest(
                    post_id=post.id,
                    product_id=product_id,
                    description=request["description"],
                    urgency=float(request.get("urgency", 0.5)),
                    evidence_quote=request.get("evidence_quote") or None,
                )
            )

    @staticmethod
    def _slug(name: str) -> str:
        from app.core.text import slugify

        return slugify(name)
