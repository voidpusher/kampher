"""Run one agent cycle synchronously — dev/debug entrypoint.

python -m app.workers.run_once collect
python -m app.workers.run_once refresh    # collect + embed only new posts
python -m app.workers.run_once monitor 60 # fail if a configured stream is stale
python -m app.workers.run_once recovery    # verify backup/recovery invariants
python -m app.workers.run_once embed      # local, no LLM needed
python -m app.workers.run_once enrich
python -m app.workers.run_once cluster
python -m app.workers.run_once trends
python -m app.workers.run_once reports
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from app.core.logging import configure_logging, get_logger
from app.db.session import worker_session

log = get_logger("run_once")

if TYPE_CHECKING:
    import uuid


def main(step: str, batch_size: int | None = None) -> None:
    configure_logging()

    if step in {"collect", "refresh"}:
        from app.collectors.registry import enabled_collectors
        from app.services.ingestion import IngestionService

        new_post_ids: list[uuid.UUID] = []
        failed_streams: list[str] = []
        for collector in enabled_collectors():
            for stream in collector.streams():
                with worker_session() as session:
                    try:
                        new = IngestionService(session).collect_stream(collector.source, stream)
                    except Exception:  # noqa: BLE001 - keep other live sources flowing
                        failed_streams.append(f"{collector.source.value}/{stream}")
                        log.exception(
                            "stream refresh failed",
                            source=collector.source.value,
                            stream=stream,
                        )
                        continue
                new_post_ids.extend(new)
                log.info("collected", source=collector.source.value, stream=stream, new=len(new))

        if step == "refresh" and new_post_ids:
            from app.services.embedding import EmbeddingService
            from app.vector.store import get_vector_store

            get_vector_store().ensure_collections()
            embedded = 0
            with worker_session() as session:
                for start in range(0, len(new_post_ids), 64):
                    embedded += EmbeddingService(session).embed_posts(
                        new_post_ids[start : start + 64]
                    )
            log.info("incremental refresh complete", new=len(new_post_ids), embedded=embedded)
        elif step == "refresh":
            log.info("incremental refresh complete", new=0, embedded=0)

        if failed_streams:
            log.error(
                "collection completed with failed streams",
                failed=len(failed_streams),
                streams=failed_streams,
            )
            raise SystemExit(1)

    elif step == "monitor":
        from datetime import UTC, datetime

        from sqlalchemy import select

        from app.collectors.registry import enabled_collectors
        from app.models import SourceCursor
        from app.services.ingestion_monitor import (
            ExpectedStream,
            evaluate_stream_health,
            is_healthy,
        )

        stale_after_minutes = batch_size or 60
        expected = [
            ExpectedStream(collector.source, stream, stale_after_minutes)
            for collector in enabled_collectors()
            for stream in collector.streams()
        ]
        with worker_session() as session:
            cursors = list(session.scalars(select(SourceCursor)))
        checks = evaluate_stream_health(expected, cursors, now=datetime.now(UTC))
        unhealthy = {key: value for key, value in checks.items() if value != "ok"}
        if not is_healthy(checks):
            log.error("ingestion health check failed", streams=unhealthy)
            raise SystemExit(1)
        log.info("ingestion health check passed", streams=len(checks))

    elif step == "recovery":
        from app.services.recovery import (
            evaluate_recovery_readiness,
            read_recovery_metrics,
            recovery_is_ready,
        )

        with worker_session() as session:
            metrics = read_recovery_metrics(session)
        checks = evaluate_recovery_readiness(metrics)
        if not recovery_is_ready(checks):
            log.error("recovery readiness check failed", checks=checks)
            raise SystemExit(1)
        log.info(
            "recovery readiness check passed",
            checks=checks,
            posts=metrics.post_count,
            sources=metrics.source_count,
            migration=metrics.migration_version,
        )

    elif step == "enrich":
        from app.repositories.ingestion import IngestionRepository
        from app.services.enrichment import EnrichmentService

        with worker_session() as session:
            pending = IngestionRepository(session).pending_post_ids(limit=batch_size or 25)
        enriched = gated = failed = 0
        for post_id in pending:
            try:
                with worker_session() as session:
                    outcome = EnrichmentService(session).enrich_post(post_id)
            except Exception as exc:  # noqa: BLE001 - isolate provider failures
                failed += 1
                log.error(
                    "enrichment item failed",
                    post_id=str(post_id),
                    error=type(exc).__name__,
                )
                continue
            enriched += outcome == "enriched"
            gated += outcome == "gated"
            log.info("enriched", post_id=str(post_id), outcome=outcome)
        log.info(
            "enrichment batch complete",
            requested=len(pending),
            enriched=enriched,
            gated=gated,
            failed=failed,
        )

    elif step == "embed":
        # Embed collected posts for semantic search. Runs without any LLM —
        # embeddings are local. Enrichment normally triggers this per-post;
        # this path serves search-only mode and backfills.
        from sqlalchemy import select

        from app.models import Post
        from app.services.embedding import EmbeddingService
        from app.vector.store import get_vector_store

        get_vector_store().ensure_collections()
        with worker_session() as session:
            post_ids = list(session.scalars(select(Post.id)))
            total = 0
            for start in range(0, len(post_ids), 64):
                total += EmbeddingService(session).embed_posts(post_ids[start : start + 64])
        log.info("embedded", posts=total)

    elif step == "cluster":
        from app.services.clustering import ClusteringService
        from app.services.opportunity_engine import OpportunityEngine
        from app.vector.store import get_vector_store

        get_vector_store().ensure_collections()
        with worker_session() as session:
            log.info("clustered", **ClusteringService(session).cluster_pending())
        with worker_session() as session:
            log.info("generated", **OpportunityEngine(session).run())

    elif step == "trends":
        from app.services.trend import TrendService

        with worker_session() as session:
            log.info("snapshots", count=TrendService(session).snapshot_clusters())

    elif step == "reports":
        from app.services.report import ReportService

        with worker_session() as session:
            log.info("reports", count=ReportService(session).generate_missing())

    else:
        raise SystemExit(
            f"unknown step: {step!r} "
            "(collect|refresh|monitor|recovery|embed|enrich|cluster|trends|reports)"
        )


if __name__ == "__main__":
    if len(sys.argv) not in {2, 3}:
        raise SystemExit(__doc__)
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) == 3 else None)
