"""billing: subscription state on organizations, stripe webhook idempotency

Revision ID: 0011
Revises: 0010
Create Date: 2026-11-03 03:00:00+00:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("organizations", sa.Column("subscription_status", sa.String(30), nullable=True))
    op.add_column(
        "organizations", sa.Column("trial_ends_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "organizations", sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "organizations",
        sa.Column("goalkeeper_seats", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "organizations",
        sa.Column("trial_used", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("organizations", "goalkeeper_seats", server_default=None)
    op.alter_column("organizations", "trial_used", server_default=None)
    op.create_table(
        "stripe_events",
        sa.Column("id", sa.String(length=100), nullable=False),
        sa.Column("type", sa.String(length=100), nullable=False),
        sa.Column(
            "processed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_stripe_events")),
    )
    op.execute("GRANT SELECT, INSERT ON stripe_events TO handball_app")


def downgrade() -> None:
    op.drop_table("stripe_events")
    for col in ("trial_used", "goalkeeper_seats", "current_period_end", "trial_ends_at",
                "subscription_status"):
        op.drop_column("organizations", col)
