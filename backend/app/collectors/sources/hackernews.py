"""Hacker News collector via the Algolia search API (no credentials).

Streams: story feeds rich in problem statements (Ask HN, Show HN, front-page
stories). Cursor = newest unix timestamp seen per stream.
"""

from __future__ import annotations

import html
import re
from datetime import UTC, datetime
from typing import Any, ClassVar

from app.collectors.base import BaseCollector
from app.collectors.registry import register
from app.collectors.schema import CollectResult, RawAuthor, RawDocument
from app.models.enums import Source

API = "https://hn.algolia.com/api/v1/search_by_date"

_TAGS = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    return html.unescape(_TAGS.sub(" ", text)).strip()


@register
class HackerNewsCollector(BaseCollector):
    source: ClassVar[Source] = Source.HACKERNEWS
    requests_per_second = 2.0

    STREAM_TAGS: ClassVar[dict[str, str]] = {
        "ask_hn": "ask_hn",
        "show_hn": "show_hn",
        "story": "story",
    }

    def enabled(self) -> bool:
        return self.settings.hn_enabled

    def streams(self) -> list[str]:
        return list(self.STREAM_TAGS)

    async def collect(self, stream: str, cursor: dict[str, Any]) -> CollectResult:
        since = int(cursor.get("newest_created_i", 0))
        params: dict[str, Any] = {
            "tags": self.STREAM_TAGS[stream],
            "hitsPerPage": 100,
            "numericFilters": f"created_at_i>{since}",
        }
        async with self.http_client() as client:
            payload = await self._request_json(client, "GET", API, params=params)

        hits = payload.get("hits", [])
        documents = [self._normalize(h) for h in hits]
        new_cursor = dict(cursor)
        if hits:
            new_cursor["newest_created_i"] = max(h["created_at_i"] for h in hits)
        return CollectResult(documents=documents, cursor=new_cursor)

    def _normalize(self, h: dict[str, Any]) -> RawDocument:
        object_id = str(h["objectID"])
        author = h.get("author") or "unknown"
        return RawDocument(
            source=self.source,
            external_id=object_id,
            url=h.get("url") or f"https://news.ycombinator.com/item?id={object_id}",
            title=h.get("title"),
            body=_strip_html(h.get("story_text") or ""),
            community="hackernews",
            author=RawAuthor(
                external_id=author,
                username=author,
                profile_url=f"https://news.ycombinator.com/user?id={author}",
            ),
            posted_at=datetime.fromtimestamp(h["created_at_i"], tz=UTC),
            metrics={
                "score": h.get("points") or 0,
                "num_comments": h.get("num_comments") or 0,
            },
            raw={"tags": h.get("_tags", [])},
        )
