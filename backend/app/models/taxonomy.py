"""Taxonomy: topics and industries (seeded, hierarchical, extensible)."""

from __future__ import annotations

import uuid

from sqlalchemy import Float, ForeignKey, Index, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Topic(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "topics"

    slug: Mapped[str] = mapped_column(Text, unique=True)
    name: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("topics.id", ondelete="SET NULL")
    )

    children: Mapped[list[Topic]] = relationship()


class Industry(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "industries"

    slug: Mapped[str] = mapped_column(Text, unique=True)
    name: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("industries.id", ondelete="SET NULL")
    )

    children: Mapped[list[Industry]] = relationship()


class PostTopic(Base, TimestampMixin):
    """Post ↔ topic assignment with model confidence (association object)."""

    __tablename__ = "post_topics"
    __table_args__ = (
        UniqueConstraint("post_id", "topic_id"),
        Index("ix_post_topics_topic_id", "topic_id"),
    )

    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True
    )
    topic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True
    )
    confidence: Mapped[float] = mapped_column(Float, default=0.0)


class PostIndustry(Base, TimestampMixin):
    __tablename__ = "post_industries"
    __table_args__ = (
        UniqueConstraint("post_id", "industry_id"),
        Index("ix_post_industries_industry_id", "industry_id"),
    )

    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True
    )
    industry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("industries.id", ondelete="CASCADE"), primary_key=True
    )
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
