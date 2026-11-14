"""a part of a match can say whether the teams changed ends before it

A recording the phone split mid-half has no side change between its parts; a coach can say so for
each later part (Echtlauf 5 P9). Null: the app decides from the gap between the recordings.

Revision ID: 0045
Revises: 0044
Create Date: 2026-11-14 06:00:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0045"
down_revision: str | None = "0044"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("match_segments", sa.Column("side_change", sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column("match_segments", "side_change")
