"""Write-side repository used by the Collector/Cleaner agents (sync sessions)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.collectors.schema import RawDocument
from app.models import Author, Enrichment, Post, SourceCursor
from app.models.enums import EnrichmentStatus, Source


class IngestionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    # ── cursors ─────────────────────────────────────────────────────────

    def get_cursor(self, source: Source, stream: str) -> dict[str, Any]:
        row = self.session.scalar(
            select(SourceCursor).where(SourceCursor.source == source, SourceCursor.stream == stream)
        )
        return dict(row.cursor) if row else {}

    def save_cursor(
        self,
        source: Source,
        stream: str,
        cursor: dict[str, Any],
        error: str | None = None,
    ) -> None:
        stmt = (
            pg_insert(SourceCursor)
            .values(
                id=uuid.uuid4(),
                source=source,
                stream=stream,
                cursor=cursor,
                last_run_at=datetime.now(UTC),
                last_error=error,
            )
            .on_conflict_do_update(
                index_elements=[SourceCursor.source, SourceCursor.stream],
                set_={
                    "cursor": cursor,
                    "last_run_at": datetime.now(UTC),
                    "last_error": error,
                },
            )
        )
        self.session.execute(stmt)

    # ── documents ───────────────────────────────────────────────────────

    def upsert_author(self, doc: RawDocument) -> uuid.UUID | None:
        if doc.author is None:
            return None
        stmt = (
            pg_insert(Author)
            .values(
                id=uuid.uuid4(),
                source=doc.source,
                external_id=doc.author.external_id,
                username=doc.author.username,
                display_name=doc.author.display_name,
                profile_url=doc.author.profile_url,
            )
            .on_conflict_do_update(
                index_elements=[Author.source, Author.external_id],
                set_={"username": doc.author.username},
            )
            .returning(Author.id)
        )
        return self.session.execute(stmt).scalar_one()

    def is_duplicate_content(self, content_hash: str) -> bool:
        return (
            self.session.scalar(select(Post.id).where(Post.content_hash == content_hash).limit(1))
            is not None
        )

    def insert_post(self, doc: RawDocument, author_id: uuid.UUID | None) -> uuid.UUID | None:
        """Insert if unseen; returns the new post id, or None if already stored."""
        stmt = (
            pg_insert(Post)
            .values(
                id=uuid.uuid4(),
                source=doc.source,
                external_id=doc.external_id,
                url=doc.url,
                title=doc.title,
                body=doc.body,
                community=doc.community,
                thread_external_id=doc.thread_external_id,
                author_id=author_id,
                posted_at=doc.posted_at,
                collected_at=datetime.now(UTC),
                content_hash=doc.content_hash(),
                metrics=doc.metrics,
                raw=doc.raw,
                enrichment_status=EnrichmentStatus.PENDING,
            )
            .on_conflict_do_nothing(index_elements=[Post.source, Post.external_id])
            .returning(Post.id)
        )
        return self.session.execute(stmt).scalar_one_or_none()

    # ── enrichment bookkeeping ──────────────────────────────────────────

    def pending_post_ids(self, limit: int = 200) -> list[uuid.UUID]:
        rows = self.session.scalars(
            select(Post.id)
            .where(Post.enrichment_status == EnrichmentStatus.PENDING)
            .order_by(Post.collected_at)
            .limit(limit)
        )
        return list(rows)

    def get_post(self, post_id: uuid.UUID) -> Post | None:
        return self.session.get(Post, post_id)

    def save_enrichment(
        self,
        post_id: uuid.UUID,
        stage: str,
        pipeline_version: int,
        output: dict[str, Any],
        model: str | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        latency_ms: int | None = None,
    ) -> None:
        stmt = (
            pg_insert(Enrichment)
            .values(
                id=uuid.uuid4(),
                post_id=post_id,
                stage=stage,
                pipeline_version=pipeline_version,
                output=output,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=latency_ms,
            )
            .on_conflict_do_update(
                index_elements=[
                    Enrichment.post_id,
                    Enrichment.stage,
                    Enrichment.pipeline_version,
                ],
                set_={"output": output, "model": model},
            )
        )
        self.session.execute(stmt)
