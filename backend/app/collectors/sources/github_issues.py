"""GitHub Issues collector (REST v3).

Streams are repos; incremental sync via ``since`` (ISO timestamp of last
update seen). Issues are dense with pain and feature requests — the labels
and reaction counts come along as metrics.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, ClassVar

from app.collectors.base import BaseCollector
from app.collectors.registry import register
from app.collectors.schema import CollectResult, RawAuthor, RawDocument
from app.models.enums import Source

API = "https://api.github.com"


@register
class GitHubIssuesCollector(BaseCollector):
    source: ClassVar[Source] = Source.GITHUB_ISSUES
    requests_per_second = 1.0  # 5000/hr authenticated; stay far below

    def enabled(self) -> bool:
        return bool(self.settings.github_token and self.settings.github_repos)

    def streams(self) -> list[str]:
        return list(self.settings.github_repos)

    def _headers(self) -> dict[str, str]:
        token = self.settings.github_token
        assert token is not None  # guarded by enabled()
        return {
            "Authorization": f"Bearer {token.get_secret_value()}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def collect(self, stream: str, cursor: dict[str, Any]) -> CollectResult:
        params: dict[str, Any] = {
            "state": "open",
            "sort": "updated",
            "direction": "asc",
            "per_page": 100,
        }
        if since := cursor.get("since"):
            params["since"] = since

        async with self.http_client() as client:
            payload = await self._request_json(
                client,
                "GET",
                f"{API}/repos/{stream}/issues",
                params=params,
                headers=self._headers(),
            )

        # The issues endpoint also returns PRs; skip them.
        issues = [i for i in payload if "pull_request" not in i]
        documents = [self._normalize(i, stream) for i in issues]
        new_cursor = dict(cursor)
        if issues:
            new_cursor["since"] = max(i["updated_at"] for i in issues)
        return CollectResult(documents=documents, cursor=new_cursor)

    def _normalize(self, issue: dict[str, Any], repo: str) -> RawDocument:
        user = issue.get("user") or {}
        reactions = issue.get("reactions") or {}
        return RawDocument(
            source=self.source,
            external_id=str(issue["id"]),
            url=issue["html_url"],
            title=issue.get("title"),
            body=issue.get("body") or "",
            community=repo,
            author=RawAuthor(
                external_id=str(user.get("id", "")),
                username=user.get("login", "ghost"),
                profile_url=user.get("html_url"),
            ),
            posted_at=datetime.fromisoformat(issue["created_at"].replace("Z", "+00:00")),
            metrics={
                "comments": issue.get("comments", 0),
                "reactions": reactions.get("total_count", 0),
                "thumbs_up": reactions.get("+1", 0),
            },
            raw={
                "number": issue.get("number"),
                "labels": [label["name"] for label in issue.get("labels", [])],
                "state": issue.get("state"),
            },
        )
