"""shot zone empty_goal: shots on the empty goal leave long_range ("Fernwurf / leeres Tor")

Revision ID: 0033
Revises: 0032
Create Date: 2026-11-05 16:00:00.000000+00:00
"""
from collections.abc import Sequence

from alembic import op


revision: str = '0033'
down_revision: str | None = '0032'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # every shot on the empty goal is in its own zone, from any distance (zones spec version 2)
    op.execute(
        "UPDATE events SET shot_zone = 'empty_goal' "
        "WHERE type = 'shot' AND shot_type = 'empty_net'"
    )
    # cached stats recompute: their key carries METRICS_VERSION (0.3.0)


def downgrade() -> None:
    # back to the merged zone; the zone of a close shot on the empty goal is not restored
    op.execute("UPDATE events SET shot_zone = 'long_range' WHERE shot_zone = 'empty_goal'")
