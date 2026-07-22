"""Published technology surveys and their normalized aggregate poll results."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Float, ForeignKey, Index, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class TechSurvey(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "tech_surveys"

    slug: Mapped[str] = mapped_column(Text, unique=True)
    publisher: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    year: Mapped[int]
    sample_size: Mapped[int]
    geography: Mapped[str] = mapped_column(Text)
    field_start: Mapped[date | None]
    field_end: Mapped[date | None]
    source_url: Mapped[str] = mapped_column(Text)
    methodology_url: Mapped[str] = mapped_column(Text)
    data_url: Mapped[str | None] = mapped_column(Text)
    license: Mapped[str | None] = mapped_column(Text)
    reliability_score: Mapped[float] = mapped_column(Float)
    bias_note: Mapped[str] = mapped_column(Text)

    polls: Mapped[list[TechPoll]] = relationship(
        back_populates="survey", cascade="all, delete-orphan"
    )


class TechPoll(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "tech_polls"
    __table_args__ = (
        UniqueConstraint("survey_id", "key"),
        Index("ix_tech_polls_category", "category"),
    )

    survey_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tech_surveys.id", ondelete="CASCADE")
    )
    key: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(Text)
    question: Mapped[str] = mapped_column(Text)
    audience: Mapped[str] = mapped_column(Text, default="All respondents")
    response_count: Mapped[int | None] = mapped_column(Integer)
    note: Mapped[str | None] = mapped_column(Text)

    survey: Mapped[TechSurvey] = relationship(back_populates="polls")
    options: Mapped[list[TechPollOption]] = relationship(
        back_populates="poll", cascade="all, delete-orphan", order_by="TechPollOption.rank"
    )


class TechPollOption(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "tech_poll_options"
    __table_args__ = (UniqueConstraint("poll_id", "label"),)

    poll_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tech_polls.id", ondelete="CASCADE")
    )
    label: Mapped[str] = mapped_column(Text)
    percentage: Mapped[float] = mapped_column(Float)
    rank: Mapped[int]

    poll: Mapped[TechPoll] = relationship(back_populates="options")
