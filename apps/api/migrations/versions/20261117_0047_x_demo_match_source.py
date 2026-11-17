"""the example match of «Demo-Spiel ansehen» is marked by its source (data only)

The example match (services/support.demo_match) is no match of the team: lists, figures and
statistics leave out matches with source 'demo' (services/matches.counted, app review R1).
Example matches created before carry source 'video'; they are told apart from the seeded demo
club's matches (also is_demo) by their events, which the example match writes with source
'demo'. No schema change.

Revision ID: 0047
Revises: 0046
Create Date: 2026-11-17 12:00:00.000000+00:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0047"
down_revision: str | None = "0046"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE matches SET source = 'demo'
        WHERE is_demo AND source <> 'demo'
          AND EXISTS (SELECT 1 FROM events e WHERE e.match_id = matches.id AND e.source = 'demo')
        """
    )


def downgrade() -> None:
    op.execute("UPDATE matches SET source = 'video' WHERE source = 'demo'")
