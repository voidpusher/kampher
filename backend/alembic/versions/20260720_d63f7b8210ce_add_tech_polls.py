"""add tech survey poll tables

Revision ID: d63f7b8210ce
Revises: b52e17f3d4a2
Create Date: 2026-07-20
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision: str = "d63f7b8210ce"
down_revision: str | None = "b52e17f3d4a2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tech_surveys",
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("publisher", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=False),
        sa.Column("geography", sa.Text(), nullable=False),
        sa.Column("field_start", sa.Date(), nullable=True),
        sa.Column("field_end", sa.Date(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("methodology_url", sa.Text(), nullable=False),
        sa.Column("data_url", sa.Text(), nullable=True),
        sa.Column("license", sa.Text(), nullable=True),
        sa.Column("reliability_score", sa.Float(), nullable=False),
        sa.Column("bias_note", sa.Text(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tech_surveys")),
        sa.UniqueConstraint("slug", name=op.f("uq_tech_surveys_slug")),
    )
    op.create_table(
        "tech_polls",
        sa.Column("survey_id", sa.UUID(), nullable=False),
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("audience", sa.Text(), nullable=False),
        sa.Column("response_count", sa.Integer(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["survey_id"], ["tech_surveys.id"], name=op.f("fk_tech_polls_survey_id_tech_surveys"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tech_polls")),
        sa.UniqueConstraint("survey_id", "key", name=op.f("uq_tech_polls_survey_id")),
    )
    op.create_index("ix_tech_polls_category", "tech_polls", ["category"])
    op.create_table(
        "tech_poll_options",
        sa.Column("poll_id", sa.UUID(), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("percentage", sa.Float(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["poll_id"], ["tech_polls.id"], name=op.f("fk_tech_poll_options_poll_id_tech_polls"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tech_poll_options")),
        sa.UniqueConstraint("poll_id", "label", name=op.f("uq_tech_poll_options_poll_id")),
    )


def downgrade() -> None:
    op.drop_table("tech_poll_options")
    op.drop_index("ix_tech_polls_category", table_name="tech_polls")
    op.drop_table("tech_polls")
    op.drop_table("tech_surveys")
