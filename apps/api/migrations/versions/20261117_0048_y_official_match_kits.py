"""matches from the federation's schedule wear the club's colour

The schedule sync made its matches with the default kit (blue, goalkeeper orange) instead of the
club's colour, as a match made by hand gets it: the upload of a club in green showed blue shirts
(review R16). Matches without a video yet take the club's colour; a match with a video keeps what
its analysis used.

Revision ID: 0048
Revises: 0047
Create Date: 2026-11-17 12:00:00.000000+00:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0048"
down_revision: str | None = "0047"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE matches AS m
        SET kit_own = o.primary_color
        FROM organizations AS o
        WHERE o.id = m.organization_id
          AND m.source = 'official'
          AND lower(m.kit_own) = '#0b6bcb'
          AND o.primary_color IS NOT NULL
          AND lower(o.primary_color) <> '#0b6bcb'
          AND m.kind <> 'scouting'
          AND NOT EXISTS (SELECT 1 FROM video_assets v WHERE v.match_id = m.id)
        """
    )


def downgrade() -> None:
    # a colour fix of data: nothing to undo (the earlier default was no choice of anyone)
    pass
