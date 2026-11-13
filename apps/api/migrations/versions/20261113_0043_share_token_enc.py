"""share links keep the token encrypted, so the coach can copy the same link again

Revision ID: 0043
Revises: 0042
Create Date: 2026-11-13 00:30:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0043"
down_revision: str | None = "0042"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("share_links", sa.Column("token_enc", sa.String(length=300), nullable=True))


def downgrade() -> None:
    op.drop_column("share_links", "token_enc")
