"""match referee kit

Revision ID: 0030
Revises: 0029
Create Date: 2026-11-05 08:00:00.000000+00:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0030'
down_revision: str | None = '0029'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('matches', sa.Column('kit_referee', sa.String(length=7), nullable=True))


def downgrade() -> None:
    op.drop_column('matches', 'kit_referee')
