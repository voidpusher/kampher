"""GitHub Discussions collector (GraphQL — discussions have no REST API).

Streams are repos; cursor is the GraphQL ``endCursor`` plus the newest
``updatedAt`` seen, iterating discussions by most-recently-updated.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, ClassVar

from app.collectors.base import BaseCollector
from app.collectors.registry import register
from app.collectors.schema import CollectResult, RawAuthor, RawDocument
from app.core.exceptions import SourceUnavailableError
from app.models.enums import Source

GRAPHQL = "https://api.github.com/graphql"

QUERY = """
query($owner: String!, $name: String!, $after: String) {
  repository(owner: $owner, name: $name) {
    discussions(first: 50, after: $after, orderBy: {field: UPDATED_AT, direction: DESC}) {
      pageInfo { endCursor hasNextPage }
      nodes {
        id
        number
        title
        bodyText
        url
        createdAt
        updatedAt
        upvoteCount
        comments { totalCount }
        category { name }
        author { login url }
      }
    }
  }
}
"""


@register
class GitHubDiscussionsCollector(BaseCollector):
    source: ClassVar[Source] = Source.GITHUB_DISCUSSIONS
    requests_per_second = 0.5  # GraphQL points budget is tighter than REST

    def enabled(self) -> bool:
        return bool(self.settings.github_token and self.settings.github_repos)

    def streams(self) -> list[str]:
        return list(self.settings.github_repos)

    async def collect(self, stream: str, cursor: dict[str, Any]) -> CollectResult:
        owner, _, name = stream.partition("/")
        token = self.settings.github_token
        assert token is not None  # guarded by enabled()
        seen_until = cursor.get("newest_updated_at", "")

        async with self.http_client() as client:
            payload = await self._request_json(
                client,
                "POST",
                GRAPHQL,
                json={"query": QUERY, "variables": {"owner": owner, "name": name, "after": None}},
                headers={"Authorization": f"Bearer {token.get_secret_value()}"},
            )

        if payload.get("errors"):
            raise SourceUnavailableError(str(payload["errors"]), repo=stream)

        repo = (payload.get("data") or {}).get("repository")
        nodes = (repo or {}).get("discussions", {}).get("nodes", [])
        # Iterating newest-updated first: stop at anything we've already seen.
        fresh = [n for n in nodes if n["updatedAt"] > seen_until]
        documents = [self._normalize(n, stream) for n in fresh]
        new_cursor = dict(cursor)
        if fresh:
            new_cursor["newest_updated_at"] = max(n["updatedAt"] for n in fresh)
        return CollectResult(documents=documents, cursor=new_cursor)

    def _normalize(self, n: dict[str, Any], repo: str) -> RawDocument:
        author = n.get("author") or {}
        login = author.get("login", "ghost")
        return RawDocument(
            source=self.source,
            external_id=n["id"],
            url=n["url"],
            title=n.get("title"),
            body=n.get("bodyText") or "",
            community=repo,
            author=RawAuthor(external_id=login, username=login, profile_url=author.get("url")),
            posted_at=datetime.fromisoformat(n["createdAt"].replace("Z", "+00:00")),
            metrics={
                "upvotes": n.get("upvoteCount", 0),
                "comments": (n.get("comments") or {}).get("totalCount", 0),
            },
            raw={"number": n.get("number"), "category": (n.get("category") or {}).get("name")},
        )
