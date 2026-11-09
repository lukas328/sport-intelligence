"""official report import: tries and next try of a game without a game log yet

Revision ID: 0035
Revises: 0034
Create Date: 2026-11-09 09:00:00.000000+00:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0035'
down_revision: str | None = '0034'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'matches',
        sa.Column('official_report_tries', sa.SmallInteger(), server_default='0', nullable=False),
    )
    op.add_column(
        'matches', sa.Column('official_report_retry_at', sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('matches', 'official_report_retry_at')
    op.drop_column('matches', 'official_report_tries')
