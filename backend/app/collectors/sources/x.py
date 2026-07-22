"""X (Twitter) collector — API v2 recent search.

Streams are configured search queries tuned for unmet-need language
("is there a tool", "why is there no", …). Cursor = ``since_id``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, ClassVar

from app.collectors.base import BaseCollector
from app.collectors.registry import register
from app.collectors.schema import CollectResult, RawAuthor, RawDocument
from app.models.enums import Source

API = "https://api.x.com/2/tweets/search/recent"


@register
class XCollector(BaseCollector):
    source: ClassVar[Source] = Source.X
    requests_per_second = 0.2  # recent-search quotas are strict on basic tiers

    def enabled(self) -> bool:
        return bool(self.settings.x_bearer_token and self.settings.x_queries)

    def streams(self) -> list[str]:
        return list(self.settings.x_queries)

    async def collect(self, stream: str, cursor: dict[str, Any]) -> CollectResult:
        token = self.settings.x_bearer_token
        assert token is not None  # guarded by enabled()
        params: dict[str, Any] = {
            "query": stream,
            "max_results": 100,
            "tweet.fields": "created_at,public_metrics,author_id,lang",
            "expansions": "author_id",
            "user.fields": "username,name",
        }
        if since_id := cursor.get("since_id"):
            params["since_id"] = since_id

        async with self.http_client() as client:
            payload = await self._request_json(
                client,
                "GET",
                API,
                params=params,
                headers={"Authorization": f"Bearer {token.get_secret_value()}"},
            )

        tweets = payload.get("data", [])
        users = {u["id"]: u for u in payload.get("includes", {}).get("users", [])}
        documents = [self._normalize(t, users) for t in tweets]
        new_cursor = dict(cursor)
        if newest_id := payload.get("meta", {}).get("newest_id"):
            new_cursor["since_id"] = newest_id
        return CollectResult(documents=documents, cursor=new_cursor)

    def _normalize(self, t: dict[str, Any], users: dict[str, dict[str, Any]]) -> RawDocument:
        user = users.get(t.get("author_id", ""), {})
        username = user.get("username", "unknown")
        metrics = t.get("public_metrics", {})
        return RawDocument(
            source=self.source,
            external_id=t["id"],
            url=f"https://x.com/{username}/status/{t['id']}",
            title=None,
            body=t.get("text", ""),
            community=None,
            author=RawAuthor(
                external_id=t.get("author_id", ""),
                username=username,
                display_name=user.get("name"),
                profile_url=f"https://x.com/{username}",
            ),
            posted_at=datetime.fromisoformat(t["created_at"].replace("Z", "+00:00")),
            metrics={
                "likes": metrics.get("like_count", 0),
                "reposts": metrics.get("retweet_count", 0),
                "replies": metrics.get("reply_count", 0),
                "impressions": metrics.get("impression_count", 0),
            },
            raw={"lang": t.get("lang")},
        )
