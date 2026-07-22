"""Run one agent cycle synchronously — dev/debug entrypoint.

python -m app.workers.run_once collect
python -m app.workers.run_once refresh    # collect + embed only new posts
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


def main(step: str) -> None:
    configure_logging()

    if step in {"collect", "refresh"}:
        from app.collectors.registry import enabled_collectors
        from app.services.ingestion import IngestionService

        new_post_ids: list[uuid.UUID] = []
        for collector in enabled_collectors():
            for stream in collector.streams():
                try:
                    with worker_session() as session:
                        new = IngestionService(session).collect_stream(collector.source, stream)
                except Exception:  # noqa: BLE001 - keep other live sources flowing
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

    elif step == "enrich":
        from app.repositories.ingestion import IngestionRepository
        from app.services.enrichment import EnrichmentService

        with worker_session() as session:
            pending = IngestionRepository(session).pending_post_ids(limit=25)
        for post_id in pending:
            with worker_session() as session:
                outcome = EnrichmentService(session).enrich_post(post_id)
            log.info("enriched", post_id=str(post_id), outcome=outcome)

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
            f"unknown step: {step!r} (collect|refresh|embed|enrich|cluster|trends|reports)"
        )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
