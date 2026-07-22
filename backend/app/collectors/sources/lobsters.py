"""Lobsters collector — the site's public JSON feed (no credentials).

A single stream of newest stories; cursor is the newest created_at seen.
Small volume, high signal: a tight practitioner community whose "ask" and
"programming" posts read like distilled developer pain.
"""

from __future__ import annotations

import html
import re
from datetime import datetime
from typing import Any, ClassVar

from app.collectors.base import BaseCollector
from app.collectors.registry import register
from app.collectors.schema import CollectResult, RawAuthor, RawDocument
from app.models.enums import Source

API = "https://lobste.rs/newest.json"

_TAGS = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    return html.unescape(_TAGS.sub(" ", text)).strip()


@register
class LobstersCollector(BaseCollector):
    source: ClassVar[Source] = Source.LOBSTERS
    requests_per_second = 0.2  # small site; one page per sweep is plenty

    def enabled(self) -> bool:
        return self.settings.lobsters_enabled

    def streams(self) -> list[str]:
        return ["newest"]

    async def collect(self, stream: str, cursor: dict[str, Any]) -> CollectResult:
        async with self.http_client() as client:
            payload = await self._request_json(
                client,
                "GET",
                API,
                headers={"User-Agent": "kampher/0.1 (opportunity research)"},
            )

        seen_until = cursor.get("newest_created_at", "")
        fresh = [s for s in payload if s.get("created_at", "") > seen_until]
        documents = [self._normalize(s) for s in fresh]
        new_cursor = dict(cursor)
        if fresh:
            new_cursor["newest_created_at"] = max(s["created_at"] for s in fresh)
        return CollectResult(documents=documents, cursor=new_cursor)

    def _normalize(self, s: dict[str, Any]) -> RawDocument:
        username = s.get("submitter_user") or "unknown"
        return RawDocument(
            source=self.source,
            external_id=s["short_id"],
            url=s.get("url") or s["comments_url"],
            title=s.get("title"),
            body=_strip_html(s.get("description") or ""),
            community="lobsters",
            author=RawAuthor(
                external_id=username,
                username=username,
                profile_url=f"https://lobste.rs/~{username}",
            ),
            posted_at=datetime.fromisoformat(s["created_at"]),
            metrics={
                "score": s.get("score", 0),
                "comments": s.get("comment_count", 0),
            },
            raw={"tags": s.get("tags", [])},
        )
