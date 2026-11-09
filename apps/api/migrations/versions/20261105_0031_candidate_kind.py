"""candidate kind and outcome: shot candidates in goal_candidates

Revision ID: 0031
Revises: 0030
Create Date: 2026-11-05 14:00:00.000000+00:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0031'
down_revision: str | None = '0030'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'goal_candidates',
        sa.Column('kind', sa.String(length=10), server_default='goal', nullable=False),
    )
    op.add_column('goal_candidates', sa.Column('outcome', sa.String(length=10), nullable=True))
    op.execute("UPDATE goal_candidates SET outcome = 'goal' WHERE status = 'confirmed'")


def downgrade() -> None:
    op.execute("DELETE FROM goal_candidates WHERE kind <> 'goal'")
    op.drop_column('goal_candidates', 'outcome')
    op.drop_column('goal_candidates', 'kind')
