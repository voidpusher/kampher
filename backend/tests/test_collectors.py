from __future__ import annotations

import asyncio
import time

import respx
from httpx import Response

from app.collectors.rate_limit import TokenBucket
from app.collectors.registry import all_collectors
from app.collectors.schema import RawDocument
from app.collectors.sources.hackernews import HackerNewsCollector
from app.collectors.sources.reddit import RedditCollector
from app.models.enums import Source

REDDIT_POST = {
    "name": "t3_abc123",
    "id": "abc123",
    "permalink": "/r/SaaS/comments/abc123/help/",
    "title": "Is there a tool for usage-based billing?",
    "selftext": "I keep writing spreadsheet hacks for metered pricing.",
    "subreddit": "SaaS",
    "author": "founder42",
    "created_utc": 1720000000,
    "score": 41,
    "num_comments": 17,
    "upvote_ratio": 0.94,
    "link_flair_text": None,
}

HN_HIT = {
    "objectID": "40000001",
    "title": "Ask HN: How do you monitor cron jobs?",
    "story_text": "Every tool I tried is overkill for a <b>solo dev</b>.",
    "author": "devperson",
    "created_at_i": 1720000500,
    "points": 120,
    "num_comments": 85,
    "url": None,
    "_tags": ["ask_hn", "story"],
}


class TestRegistry:
    def test_all_launch_sources_registered(self) -> None:
        registered = set(all_collectors())
        assert {
            Source.REDDIT,
            Source.X,
            Source.HACKERNEWS,
            Source.GITHUB_ISSUES,
            Source.GITHUB_DISCUSSIONS,
            Source.STACKOVERFLOW,
            Source.LOBSTERS,
        } <= registered


class TestNormalization:
    def test_reddit_normalizes_to_common_schema(self) -> None:
        doc = RedditCollector()._normalize(REDDIT_POST)
        assert isinstance(doc, RawDocument)
        assert doc.source is Source.REDDIT
        assert doc.external_id == "t3_abc123"
        assert doc.community == "r/SaaS"
        assert doc.metrics["score"] == 41
        assert doc.author is not None and doc.author.username == "founder42"
        assert doc.url.startswith("https://www.reddit.com/r/SaaS/")

    def test_hn_strips_html_and_builds_permalink(self) -> None:
        doc = HackerNewsCollector()._normalize(HN_HIT)
        assert doc.source is Source.HACKERNEWS
        assert "<b>" not in doc.body
        assert "solo dev" in doc.body
        assert doc.url == "https://news.ycombinator.com/item?id=40000001"

    def test_content_hash_ignores_whitespace_and_case(self) -> None:
        doc_a = RedditCollector()._normalize(REDDIT_POST)
        variant = dict(REDDIT_POST)
        variant["selftext"] = "  I keep writing   SPREADSHEET hacks for metered pricing. "
        doc_b = RedditCollector()._normalize(variant)
        assert doc_a.content_hash() == doc_b.content_hash()


SO_QUESTION = {
    "question_id": 79123456,
    "link": "https://stackoverflow.com/questions/79123456/oauth-refresh-fails",
    "title": "OAuth token refresh silently fails behind a corporate proxy",
    "body": "<p>Our SPA keeps logging users out because <code>refresh</code> fails.</p>",
    "creation_date": 1721000000,
    "score": 12,
    "view_count": 340,
    "answer_count": 0,
    "is_answered": False,
    "tags": ["authentication", "oauth"],
    "owner": {
        "user_id": 55,
        "display_name": "devuser",
        "link": "https://stackoverflow.com/users/55",
    },
}

LOBSTERS_STORY = {
    "short_id": "abc123",
    "title": "Why is deploying a static site still this hard?",
    "url": "",
    "comments_url": "https://lobste.rs/s/abc123",
    "description": "<p>Every host has a different <em>gotcha</em>.</p>",
    "created_at": "2026-07-17T10:00:00-05:00",
    "score": 44,
    "comment_count": 30,
    "tags": ["devops", "rant"],
    "submitter_user": "grumpydev",
}


DEVTO_ARTICLE = {
    "id": 987654,
    "title": "I spent a weekend fighting CI caching so you don't have to",
    "description": "Our pipeline re-downloaded 2GB of deps on every push. Here's why.",
    "url": "https://dev.to/grumpydev/ci-caching",
    "published_at": "2026-07-17T08:30:00Z",
    "positive_reactions_count": 55,
    "comments_count": 12,
    "tag_list": ["devops", "ci"],
    "user": {"username": "grumpydev", "name": "Grumpy Dev"},
}


class TestKeylessSources:
    def test_devto_normalizes_and_parses_zulu_timestamp(self) -> None:
        from app.collectors.sources.devto import DevToCollector

        doc = DevToCollector()._normalize(DEVTO_ARTICLE, "devops")
        assert doc.source is Source.DEVTO
        assert doc.community == "devto/devops"
        assert doc.metrics["reactions"] == 55
        assert doc.posted_at.tzinfo is not None
        assert doc.author is not None and doc.author.profile_url == "https://dev.to/grumpydev"

    def test_stackoverflow_strips_html_and_maps_metrics(self) -> None:
        from app.collectors.sources.stackoverflow import StackOverflowCollector

        doc = StackOverflowCollector()._normalize(SO_QUESTION, "authentication")
        assert doc.source is Source.STACKOVERFLOW
        assert "<p>" not in doc.body and "refresh" in doc.body
        assert doc.community == "so/authentication"
        assert doc.metrics["views"] == 340
        assert doc.author is not None and doc.author.username == "devuser"

    @respx.mock
    def test_stackoverflow_bootstraps_from_newest_questions(self) -> None:
        from app.collectors.sources.stackoverflow import API, StackOverflowCollector

        route = respx.get(API).mock(return_value=Response(200, json={"items": [SO_QUESTION]}))
        result = asyncio.run(StackOverflowCollector().collect("authentication", {}))

        assert route.called
        request = route.calls.last.request
        assert request.url.params["order"] == "desc"
        assert "fromdate" not in request.url.params
        assert result.cursor["newest_creation_date"] == SO_QUESTION["creation_date"]

    @respx.mock
    def test_stackoverflow_incremental_sync_walks_forward(self) -> None:
        from app.collectors.sources.stackoverflow import API, StackOverflowCollector

        route = respx.get(API).mock(return_value=Response(200, json={"items": []}))
        cursor = {"newest_creation_date": 1720000000}
        asyncio.run(StackOverflowCollector().collect("authentication", cursor))

        request = route.calls.last.request
        assert request.url.params["order"] == "asc"
        assert request.url.params["fromdate"] == "1720000001"

    def test_lobsters_falls_back_to_comments_url(self) -> None:
        from app.collectors.sources.lobsters import LobstersCollector

        doc = LobstersCollector()._normalize(LOBSTERS_STORY)
        assert doc.source is Source.LOBSTERS
        assert doc.url == "https://lobste.rs/s/abc123"
        assert "gotcha" in doc.body and "<em>" not in doc.body
        assert doc.posted_at.tzinfo is not None


class TestTokenBucket:
    def test_paces_after_burst_exhausted(self) -> None:
        async def scenario() -> float:
            bucket = TokenBucket(rate=50.0, capacity=1.0)
            start = time.monotonic()
            for _ in range(4):  # 1 free burst token + 3 paced at 20 ms each
                await bucket.acquire()
            return time.monotonic() - start

        elapsed = asyncio.run(scenario())
        assert elapsed >= 0.05
