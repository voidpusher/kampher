"""Importing this package registers every source plugin."""

from app.collectors.sources.devto import DevToCollector
from app.collectors.sources.github_discussions import GitHubDiscussionsCollector
from app.collectors.sources.github_issues import GitHubIssuesCollector
from app.collectors.sources.hackernews import HackerNewsCollector
from app.collectors.sources.lobsters import LobstersCollector
from app.collectors.sources.reddit import RedditCollector
from app.collectors.sources.stackoverflow import StackOverflowCollector
from app.collectors.sources.x import XCollector

__all__ = [
    "DevToCollector",
    "GitHubDiscussionsCollector",
    "GitHubIssuesCollector",
    "HackerNewsCollector",
    "LobstersCollector",
    "RedditCollector",
    "StackOverflowCollector",
    "XCollector",
]
