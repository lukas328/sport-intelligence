"""the opponent's colour per match as somebody said it; unknown stays null (docs/design/ux-reset)

Revision ID: 0040
Revises: 0038
Create Date: 2026-11-10 16:20:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0040"
down_revision: str | None = "0038"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("matches", sa.Column("opponent_kit", sa.String(length=7), nullable=True))


def downgrade() -> None:
    op.drop_column("matches", "opponent_kit")
