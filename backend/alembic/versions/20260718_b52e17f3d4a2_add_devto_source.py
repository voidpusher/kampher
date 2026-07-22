"""add devto to source enum

Revision ID: b52e17f3d4a2
Revises: a41f09d2c3e1
Create Date: 2026-07-18
"""
from __future__ import annotations

from alembic import op

revision: str = "b52e17f3d4a2"
down_revision: str | None = "a41f09d2c3e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE source ADD VALUE IF NOT EXISTS 'devto'")


def downgrade() -> None:
    # Postgres cannot drop enum values without a type rebuild; no-op.
    pass
