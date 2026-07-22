"""Report service — the Report Agent's logic.

Writes full reports for active opportunities that don't have one yet,
grounded in the opportunity's cluster evidence and stored scores.
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.llm.client import get_llm_client
from app.ai.report import generate_report
from app.core.config import get_settings
from app.core.logging import get_logger
from app.models import Opportunity, OpportunityScore
from app.repositories.intelligence import IntelligenceRepository
from app.services.opportunity_engine import OpportunityEngine

log = get_logger("service.report")


class ReportService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repo = IntelligenceRepository(session)
        self.llm = get_llm_client()
        self.settings = get_settings()

    def generate_missing(self, limit: int = 3) -> int:
        opportunities = self.repo.opportunities_without_report(limit=limit)
        for opportunity in opportunities:
            self._generate_for(opportunity)
        if opportunities:
            log.info("reports generated", count=len(opportunities))
        return len(opportunities)

    def _generate_for(self, opportunity: Opportunity) -> None:
        cluster = (
            self.repo.get_cluster(opportunity.pain_cluster_id)
            if opportunity.pain_cluster_id
            else None
        )
        if cluster is None:
            log.warning("opportunity has no cluster", opportunity_id=str(opportunity.id))
            return

        # Reuse the engine's evidence builder — one canonical evidence view.
        evidence = OpportunityEngine(self.session)._build_evidence(cluster)
        scores = self.session.scalars(
            select(OpportunityScore).where(OpportunityScore.opportunity_id == opportunity.id)
        )
        score_summary = "; ".join(
            f"{s.kind.value}={s.value:.0f} (conf {s.confidence:.2f})" for s in scores
        )

        report, usage = asyncio.run(
            generate_report(
                self.llm,
                evidence,
                opportunity.title,
                opportunity.thesis,
                score_summary,
            )
        )
        self.repo.save_report(
            opportunity_id=opportunity.id,
            content_md=report.content_md,
            sections=report.sections.model_dump(mode="json"),
            model=usage.model,
        )
