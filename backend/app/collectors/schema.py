"""The common envelope every collector emits.

Downstream layers (cleaning, enrichment, storage) only ever see
``RawDocument`` — nothing after this file knows what a subreddit or a GitHub
issue is. This is the contract that makes sources pluggable.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import Source

_WHITESPACE = re.compile(r"\s+")


class RawAuthor(BaseModel):
    external_id: str
    username: str
    display_name: str | None = None
    profile_url: str | None = None


class RawComment(BaseModel):
    external_id: str
    parent_external_id: str | None = None
    author: RawAuthor | None = None
    body: str
    posted_at: datetime
    metrics: dict[str, Any] = Field(default_factory=dict)


class RawDocument(BaseModel):
    source: Source
    external_id: str
    url: str
    title: str | None = None
    body: str = ""
    community: str | None = None  # subreddit, owner/repo, …
    thread_external_id: str | None = None
    author: RawAuthor | None = None
    posted_at: datetime
    metrics: dict[str, Any] = Field(default_factory=dict)
    comments: list[RawComment] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)

    def content_hash(self) -> str:
        """Hash of normalized text — dedups cross-posts regardless of source ids."""
        normalized = _WHITESPACE.sub(" ", f"{self.title or ''} {self.body}").strip().lower()
        return hashlib.sha256(normalized.encode()).hexdigest()

    @property
    def text(self) -> str:
        return f"{self.title}\n\n{self.body}".strip() if self.title else self.body


class CollectResult(BaseModel):
    """One collection run over one stream: documents + the cursor to persist."""

    documents: list[RawDocument]
    cursor: dict[str, Any]
