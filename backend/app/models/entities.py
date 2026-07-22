"""Extracted real-world entities and their mentions in content."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Enum, Float, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import EntityType


class Company(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "companies"

    slug: Mapped[str] = mapped_column(Text, unique=True)
    name: Mapped[str] = mapped_column(Text)
    domain: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    meta: Mapped[dict[str, Any]] = mapped_column(default=dict)

    products: Mapped[list[Product]] = relationship(back_populates="company")


class Product(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "products"

    slug: Mapped[str] = mapped_column(Text, unique=True)
    name: Mapped[str] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(Text)
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="SET NULL")
    )
    description: Mapped[str | None] = mapped_column(Text)
    meta: Mapped[dict[str, Any]] = mapped_column(default=dict)

    company: Mapped[Company | None] = relationship(back_populates="products")


class Technology(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "technologies"

    slug: Mapped[str] = mapped_column(Text, unique=True)
    name: Mapped[str] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(Text)


class EntityMention(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A single mention of an entity in a post.

    ``entity_id`` points into companies/products/technologies depending on
    ``entity_type`` (person mentions stay unresolved by design — we never
    build profiles of private individuals, only track that *a* person was
    referenced). Polymorphic target, so no FK constraint; resolution is the
    entity service's job.
    """

    __tablename__ = "entity_mentions"
    __table_args__ = (
        Index("ix_entity_mentions_post_id", "post_id"),
        Index("ix_entity_mentions_entity", "entity_type", "entity_id"),
    )

    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("posts.id", ondelete="CASCADE")
    )
    entity_type: Mapped[EntityType] = mapped_column(
        Enum(EntityType, name="entity_type", values_callable=lambda e: [m.value for m in e])
    )
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    surface_text: Mapped[str] = mapped_column(Text)
    sentiment: Mapped[float | None] = mapped_column(Float)  # -1 … 1
    context_quote: Mapped[str | None] = mapped_column(Text)
