"""Dev.to collector — the Forem public API (no credentials).

Streams are tags, synced via ``state=fresh`` newest-first listings; cursor is
the newest published_at seen. The list endpoint returns title + description
(not full body) — enough signal for pain detection without a per-article
request storm.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, ClassVar

from app.collectors.base import BaseCollector
from app.collectors.registry import register
from app.collectors.schema import CollectResult, RawAuthor, RawDocument
from app.models.enums import Source

API = "https://dev.to/api/articles"


@register
class DevToCollector(BaseCollector):
    source: ClassVar[Source] = Source.DEVTO
    requests_per_second = 0.5

    def enabled(self) -> bool:
        return self.settings.devto_enabled and bool(self.settings.devto_tags)

    def streams(self) -> list[str]:
        return list(self.settings.devto_tags)

    async def collect(self, stream: str, cursor: dict[str, Any]) -> CollectResult:
        params: dict[str, Any] = {"tag": stream, "state": "fresh", "per_page": 100}
        async with self.http_client() as client:
            payload = await self._request_json(
                client,
                "GET",
                API,
                params=params,
                headers={"User-Agent": "kampher/0.1 (opportunity research)"},
            )

        seen_until = cursor.get("newest_published_at", "")
        fresh = [a for a in payload if (a.get("published_at") or "") > seen_until]
        documents = [self._normalize(a, stream) for a in fresh]
        new_cursor = dict(cursor)
        if fresh:
            new_cursor["newest_published_at"] = max(a["published_at"] for a in fresh)
        return CollectResult(documents=documents, cursor=new_cursor)

    def _normalize(self, a: dict[str, Any], tag: str) -> RawDocument:
        user = a.get("user") or {}
        username = user.get("username", "unknown")
        return RawDocument(
            source=self.source,
            external_id=str(a["id"]),
            url=a["url"],
            title=a.get("title"),
            body=a.get("description") or "",
            community=f"devto/{tag}",
            author=RawAuthor(
                external_id=username,
                username=username,
                display_name=user.get("name"),
                profile_url=f"https://dev.to/{username}",
            ),
            posted_at=datetime.fromisoformat(a["published_at"].replace("Z", "+00:00")),
            metrics={
                "reactions": a.get("positive_reactions_count", 0),
                "comments": a.get("comments_count", 0),
            },
            raw={"tags": a.get("tag_list", [])},
        )
