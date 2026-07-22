"""Reddit collector — OAuth2 client-credentials against oauth.reddit.com.

Streams are subreddits; the cursor is the newest fullname seen, so each run
fetches only unseen posts via ``before=``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, ClassVar

import httpx

from app.collectors.base import BaseCollector
from app.collectors.registry import register
from app.collectors.schema import CollectResult, RawAuthor, RawDocument
from app.core.exceptions import SourceUnavailableError
from app.models.enums import Source

TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
API = "https://oauth.reddit.com"


@register
class RedditCollector(BaseCollector):
    source: ClassVar[Source] = Source.REDDIT
    requests_per_second = 0.9  # Reddit free tier: 100 req / 60 s with headroom

    def enabled(self) -> bool:
        s = self.settings
        return bool(s.reddit_client_id and s.reddit_client_secret)

    def streams(self) -> list[str]:
        return [f"r/{sub}" for sub in self.settings.reddit_subreddits]

    async def _token(self, client: httpx.AsyncClient) -> str:
        secret = self.settings.reddit_client_secret
        assert secret is not None  # guarded by enabled()
        response = await client.post(
            TOKEN_URL,
            auth=(self.settings.reddit_client_id, secret.get_secret_value()),
            data={"grant_type": "client_credentials"},
            headers={"User-Agent": self.settings.reddit_user_agent},
        )
        if response.status_code != 200:
            raise SourceUnavailableError(f"reddit token endpoint: {response.status_code}")
        return str(response.json()["access_token"])

    async def collect(self, stream: str, cursor: dict[str, Any]) -> CollectResult:
        subreddit = stream.removeprefix("r/")
        async with self.http_client() as client:
            token = await self._token(client)
            headers = {
                "Authorization": f"Bearer {token}",
                "User-Agent": self.settings.reddit_user_agent,
            }
            params: dict[str, Any] = {"limit": 100}
            if before := cursor.get("newest_fullname"):
                params["before"] = before

            payload = await self._request_json(
                client, "GET", f"{API}/r/{subreddit}/new", params=params, headers=headers
            )

        children = payload.get("data", {}).get("children", [])
        documents = [self._normalize(child["data"]) for child in children]
        new_cursor = dict(cursor)
        if children:
            new_cursor["newest_fullname"] = children[0]["data"]["name"]
        return CollectResult(documents=documents, cursor=new_cursor)

    def _normalize(self, d: dict[str, Any]) -> RawDocument:
        author_name = d.get("author") or "[deleted]"
        return RawDocument(
            source=self.source,
            external_id=d["name"],  # fullname, e.g. t3_abc123
            url=f"https://www.reddit.com{d['permalink']}",
            title=d.get("title"),
            body=d.get("selftext") or "",
            community=f"r/{d['subreddit']}",
            author=RawAuthor(
                external_id=author_name,
                username=author_name,
                profile_url=f"https://www.reddit.com/user/{author_name}",
            ),
            posted_at=datetime.fromtimestamp(d["created_utc"], tz=UTC),
            metrics={
                "score": d.get("score", 0),
                "num_comments": d.get("num_comments", 0),
                "upvote_ratio": d.get("upvote_ratio"),
            },
            raw={k: d.get(k) for k in ("id", "name", "subreddit", "link_flair_text")},
        )
