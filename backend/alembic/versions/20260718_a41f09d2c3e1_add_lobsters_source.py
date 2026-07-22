"""add lobsters to source enum

Revision ID: a41f09d2c3e1
Revises: c9bb26f7a23b
Create Date: 2026-07-18
"""
from __future__ import annotations

from alembic import op

revision: str = "a41f09d2c3e1"
down_revision: str | None = "c9bb26f7a23b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # PG >= 12 allows ADD VALUE inside a transaction as long as the new value
    # isn't used in the same transaction — this migration only adds it.
    op.execute("ALTER TYPE source ADD VALUE IF NOT EXISTS 'lobsters'")


def downgrade() -> None:
    # Postgres cannot drop enum values; removing 'lobsters' would require
    # rebuilding the type. Intentionally a no-op.
    pass
