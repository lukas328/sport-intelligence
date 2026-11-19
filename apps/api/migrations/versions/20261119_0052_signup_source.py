"""where a sign-up came from

Website review (19.11.2026): links from the website carry `?src=<place>` (hero, pricing, shared
scene, ...). The app keeps it in the browser through the sign-up (no cookie) and stores it with
the new account and the club it creates, so operators see which places bring clubs. Nullable:
accounts from before, invitations and direct visits have none.

Revision ID: 0052
Revises: 0051
Create Date: 2026-11-19 12:00:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0052"
down_revision: str | None = "0051"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("signup_source", sa.String(length=40), nullable=True))
    op.add_column("organizations", sa.Column("signup_source", sa.String(length=40), nullable=True))


def downgrade() -> None:
    op.drop_column("organizations", "signup_source")
    op.drop_column("users", "signup_source")
