"""track identity, physical load, video sync

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-03 00:30:00+00:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("tracks", sa.Column("number", sa.Integer(), nullable=True))
    op.add_column("tracks", sa.Column("identity_source", sa.String(length=20), nullable=True))
    op.add_column(
        "tracks", sa.Column("physical", postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    )
    op.add_column(
        "video_assets", sa.Column("sync", postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("video_assets", "sync")
    op.drop_column("tracks", "physical")
    op.drop_column("tracks", "identity_source")
    op.drop_column("tracks", "number")
