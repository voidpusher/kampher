"""Content models: what we collected and what the pipeline said about it."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Computed, Enum, ForeignKey, Index, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import EnrichmentStatus, Source


def _source_enum() -> Enum:
    return Enum(Source, name="source", values_callable=lambda e: [m.value for m in e])


class Author(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "authors"
    __table_args__ = (UniqueConstraint("source", "external_id"),)

    source: Mapped[Source] = mapped_column(_source_enum())
    external_id: Mapped[str] = mapped_column(Text)
    username: Mapped[str] = mapped_column(Text)
    display_name: Mapped[str | None] = mapped_column(Text)
    profile_url: Mapped[str | None] = mapped_column(Text)
    meta: Mapped[dict[str, Any]] = mapped_column(default=dict)

    posts: Mapped[list[Post]] = relationship(back_populates="author")


class Post(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "posts"
    __table_args__ = (
        UniqueConstraint("source", "external_id"),
        Index("ix_posts_posted_at", "posted_at"),
        Index("ix_posts_enrichment_status", "enrichment_status"),
        Index("ix_posts_content_hash", "content_hash"),
        Index("ix_posts_search_vector", "search_vector", postgresql_using="gin"),
    )

    source: Mapped[Source] = mapped_column(_source_enum())
    external_id: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text, default="")
    # Community context: subreddit, repo, HN front page, etc.
    community: Mapped[str | None] = mapped_column(Text)
    thread_external_id: Mapped[str | None] = mapped_column(Text)

    author_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("authors.id", ondelete="SET NULL")
    )
    author: Mapped[Author | None] = relationship(back_populates="posts")

    posted_at: Mapped[datetime]
    collected_at: Mapped[datetime]
    # SHA-256 of normalized body — cross-post dedup independent of source ids.
    content_hash: Mapped[str] = mapped_column(Text)
    metrics: Mapped[dict[str, Any]] = mapped_column(default=dict)
    raw: Mapped[dict[str, Any]] = mapped_column(default=dict)

    # Pipeline bookkeeping
    language: Mapped[str | None] = mapped_column(Text)
    is_spam: Mapped[bool | None]
    has_pain_signal: Mapped[bool | None]
    enrichment_status: Mapped[EnrichmentStatus] = mapped_column(
        Enum(
            EnrichmentStatus,
            name="enrichment_status",
            values_callable=lambda e: [m.value for m in e],
        ),
        default=EnrichmentStatus.PENDING,
    )
    pipeline_version: Mapped[int | None]

    search_vector: Mapped[str | None] = mapped_column(
        TSVECTOR,
        Computed(
            "to_tsvector('english', coalesce(title, '') || ' ' || coalesce(body, ''))",
            persisted=True,
        ),
    )

    comments: Mapped[list[Comment]] = relationship(back_populates="post")
    enrichments: Mapped[list[Enrichment]] = relationship(back_populates="post")


class Comment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "comments"
    __table_args__ = (
        UniqueConstraint("source", "external_id"),
        Index("ix_comments_post_id", "post_id"),
    )

    source: Mapped[Source] = mapped_column(_source_enum())
    external_id: Mapped[str] = mapped_column(Text)
    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("posts.id", ondelete="CASCADE")
    )
    parent_external_id: Mapped[str | None] = mapped_column(Text)
    author_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("authors.id", ondelete="SET NULL")
    )
    body: Mapped[str] = mapped_column(Text)
    posted_at: Mapped[datetime]
    metrics: Mapped[dict[str, Any]] = mapped_column(default=dict)

    post: Mapped[Post] = relationship(back_populates="comments")


class SourceCursor(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Per-(source, stream) incremental sync state, e.g. (reddit, r/SaaS)."""

    __tablename__ = "source_cursors"
    __table_args__ = (UniqueConstraint("source", "stream"),)

    source: Mapped[Source] = mapped_column(_source_enum())
    stream: Mapped[str] = mapped_column(Text)
    cursor: Mapped[dict[str, Any]] = mapped_column(default=dict)
    last_run_at: Mapped[datetime | None]
    last_error: Mapped[str | None] = mapped_column(Text)


class Enrichment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """One pipeline stage's structured output for one post, versioned."""

    __tablename__ = "enrichments"
    __table_args__ = (
        UniqueConstraint("post_id", "stage", "pipeline_version"),
        Index("ix_enrichments_stage", "stage"),
    )

    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("posts.id", ondelete="CASCADE")
    )
    stage: Mapped[str] = mapped_column(Text)
    pipeline_version: Mapped[int]
    output: Mapped[dict[str, Any]] = mapped_column(default=dict)
    model: Mapped[str | None] = mapped_column(Text)
    input_tokens: Mapped[int | None]
    output_tokens: Mapped[int | None]
    latency_ms: Mapped[int | None]

    post: Mapped[Post] = relationship(back_populates="enrichments")
