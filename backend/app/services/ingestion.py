"""Ingestion service — the Collector + Cleaner agents' logic.

Collect one (source, stream), dedup on (source, external_id) and on content
hash, persist, and hand new post ids to the caller (the worker enqueues them
for enrichment). Cursor advances even on partial failure so a poison
document can't wedge a stream.
"""

from __future__ import annotations

import asyncio
import uuid

from sqlalchemy.orm import Session

from app.collectors.registry import get_collector
from app.core.logging import get_logger
from app.models.enums import Source
from app.repositories.ingestion import IngestionRepository

log = get_logger("service.ingestion")


class IngestionService:
    def __init__(self, session: Session) -> None:
        self.repo = IngestionRepository(session)

    def collect_stream(self, source: Source, stream: str) -> list[uuid.UUID]:
        collector = get_collector(source)
        cursor = self.repo.get_cursor(source, stream)

        try:
            result = asyncio.run(collector.collect(stream, cursor))
        except Exception as exc:
            self.repo.save_cursor(source, stream, cursor, error=str(exc)[:500])
            raise

        new_ids: list[uuid.UUID] = []
        duplicates = 0
        for doc in result.documents:
            if self.repo.is_duplicate_content(doc.content_hash()):
                duplicates += 1
                continue
            author_id = self.repo.upsert_author(doc)
            post_id = self.repo.insert_post(doc, author_id)
            if post_id is None:
                duplicates += 1
                continue
            new_ids.append(post_id)

        self.repo.save_cursor(source, stream, result.cursor, error=None)
        log.info(
            "stream collected",
            source=source.value,
            stream=stream,
            fetched=len(result.documents),
            new=len(new_ids),
            duplicates=duplicates,
        )
        return new_ids
