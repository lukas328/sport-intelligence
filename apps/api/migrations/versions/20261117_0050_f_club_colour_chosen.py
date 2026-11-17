"""a club without a chosen colour stores none

Decision E8 (17.11.2026): a new club that skips «Eure Vereinsfarbe» has no colour of its own and is
shown in a neutral slate (core/colors.py FALLBACK_CLUB_COLOUR) until it picks one. Until now every
club was stored with blue #0b6bcb whether anyone chose it or not, so the column becomes nullable:
NULL means «not chosen». Schema only: existing rows are not rewritten; a stored #0b6bcb is read as
«not chosen» (core/colors.py club_colour_chosen).

Revision ID: 0050
Revises: 0049
Create Date: 2026-11-17 18:00:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0050"
down_revision: str | None = "0049"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "organizations", "primary_color", existing_type=sa.String(length=7), nullable=True
    )


def downgrade() -> None:
    # the earlier schema needs a colour in every row: clubs without a choice get the blue that
    # meant «not chosen» before (and still reads that way)
    op.execute("UPDATE organizations SET primary_color = '#0b6bcb' WHERE primary_color IS NULL")
    op.alter_column(
        "organizations", "primary_color", existing_type=sa.String(length=7), nullable=False
    )
