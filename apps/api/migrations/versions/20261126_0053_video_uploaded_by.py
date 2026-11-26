"""who uploaded a video

Honest waiting (26.11.2026): whoever uploads waits for the analysis and is told when it is done
(the bell and a mail), also without a role in the team. Nullable and additive: videos from before
have none; deleting the account sets it to NULL.

Revision ID: 0053
Revises: 0052
Create Date: 2026-11-26 21:45:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0053"
down_revision: str | None = "0052"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "video_assets",
        sa.Column(
            "uploaded_by_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("video_assets", "uploaded_by_id")
