"""Stack Overflow collector — Stack Exchange API v2.3.

Anonymous access is officially supported (300 req/day; an optional free app
key raises it to 10k). Streams are tags; cursor is the newest question
creation_date seen, synced incrementally via ``fromdate``.

Questions are dense with pain by construction — every one is somebody stuck.
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

API = "https://api.stackexchange.com/2.3/questions"

_TAGS = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    return html.unescape(_TAGS.sub(" ", text)).strip()


@register
class StackOverflowCollector(BaseCollector):
    source: ClassVar[Source] = Source.STACKOVERFLOW
    requests_per_second = 0.3  # be a polite anonymous client

    def enabled(self) -> bool:
        return self.settings.stackoverflow_enabled

    def streams(self) -> list[str]:
        return list(self.settings.stackoverflow_tags)

    async def collect(self, stream: str, cursor: dict[str, Any]) -> CollectResult:
        params: dict[str, Any] = {
            "site": "stackoverflow",
            "tagged": stream,
            "sort": "creation",
            # Bootstrap from the newest questions so a fresh deployment is
            # useful immediately. Once a cursor exists, walk forward in
            # ascending order so bursts larger than one page are not skipped.
            "order": "desc",
            "pagesize": 100,
            # withbody: include the question body in the response.
            "filter": "withbody",
        }
        if self.settings.stackoverflow_key:
            params["key"] = self.settings.stackoverflow_key
        if fromdate := cursor.get("newest_creation_date"):
            params["fromdate"] = int(fromdate) + 1
            params["order"] = "asc"

        async with self.http_client() as client:
            payload = await self._request_json(client, "GET", API, params=params)

        items = payload.get("items", [])
        documents = [self._normalize(q, stream) for q in items]
        new_cursor = dict(cursor)
        if items:
            new_cursor["newest_creation_date"] = max(q["creation_date"] for q in items)
        return CollectResult(documents=documents, cursor=new_cursor)

    def _normalize(self, q: dict[str, Any], tag: str) -> RawDocument:
        owner = q.get("owner") or {}
        return RawDocument(
            source=self.source,
            external_id=str(q["question_id"]),
            url=q["link"],
            title=_strip_html(q.get("title") or ""),
            body=_strip_html(q.get("body") or ""),
            community=f"so/{tag}",
            author=RawAuthor(
                external_id=str(owner.get("user_id", "anonymous")),
                username=owner.get("display_name", "anonymous"),
                profile_url=owner.get("link"),
            ),
            posted_at=datetime.fromtimestamp(q["creation_date"], tz=UTC),
            metrics={
                "score": q.get("score", 0),
                "views": q.get("view_count", 0),
                "answers": q.get("answer_count", 0),
                "is_answered": q.get("is_answered", False),
            },
            raw={"tags": q.get("tags", [])},
        )
