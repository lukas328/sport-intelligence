"""club kit: a pattern next to the two club colours (docs/design/ux-reset/TRIKOT.md, section 2)

Revision ID: 0039
Revises: 0038
Create Date: 2026-11-10 16:00:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0039"
down_revision: str | None = "0038"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "organizations",
        sa.Column("kit_pattern", sa.String(length=10), server_default="uni", nullable=False),
    )
    op.create_check_constraint(
        op.f("ck_organizations_kit_pattern_values"),
        "organizations",
        "kit_pattern IN ('uni', 'stripes', 'hoops', 'sash', 'halves')",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_organizations_kit_pattern_values"), "organizations", type_="check")
    op.drop_column("organizations", "kit_pattern")
