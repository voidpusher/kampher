"""Alert Agent tasks.

v1 alerting: detect pain clusters whose latest snapshot shows a spike
(velocity and acceleration both above threshold), emit a structured alert
event, and re-score the linked opportunity's status so spiking candidates
get promoted into the feed. Delivery channels (email/webhook) plug in here.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.logging import bind_request_context, get_logger
from app.db.session import worker_session
from app.models import Opportunity, PainCluster, TrendSnapshot
from app.models.enums import OpportunityStatus, TrendSubject
from app.workers.celery_app import app

log = get_logger("tasks.alerts")

SPIKE_VELOCITY = 1.0  # > 1 new mention/day sustained
SPIKE_ACCELERATION = 0.25  # and growth is accelerating


@app.task(name="kampher.alerts.scan")
def scan() -> dict[str, int]:
    bind_request_context()
    since = datetime.now(UTC) - timedelta(days=2)
    alerts = promotions = 0

    with worker_session() as session:
        snapshots = session.scalars(
            select(TrendSnapshot).where(
                TrendSnapshot.subject_type == TrendSubject.PAIN_CLUSTER,
                TrendSnapshot.window_start >= since,
                TrendSnapshot.velocity >= SPIKE_VELOCITY,
                TrendSnapshot.acceleration >= SPIKE_ACCELERATION,
            )
        )
        for snapshot in snapshots:
            cluster = session.get(PainCluster, snapshot.subject_id)
            if cluster is None:
                continue
            log.warning(
                "pain spike detected",
                cluster_id=str(cluster.id),
                label=cluster.label,
                velocity=snapshot.velocity,
                acceleration=snapshot.acceleration,
                mentions=snapshot.mention_count,
            )
            alerts += 1

            # A spiking candidate earns its place in the feed.
            opportunity = session.scalar(
                select(Opportunity).where(
                    Opportunity.pain_cluster_id == cluster.id,
                    Opportunity.status == OpportunityStatus.CANDIDATE,
                )
            )
            if opportunity is not None:
                opportunity.status = OpportunityStatus.ACTIVE
                promotions += 1

    return {"alerts": alerts, "promoted": promotions}
