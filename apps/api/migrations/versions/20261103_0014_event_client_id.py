"""event client id for idempotent offline sync

Revision ID: 0014
Revises: 0013
Create Date: 2026-11-03 06:00:00+00:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("events", sa.Column("client_id", sa.Uuid(), nullable=True))
    op.create_unique_constraint(op.f("uq_events_match_id"), "events", ["match_id", "client_id"])


def downgrade() -> None:
    op.drop_constraint(op.f("uq_events_match_id"), "events", type_="unique")
    op.drop_column("events", "client_id")
