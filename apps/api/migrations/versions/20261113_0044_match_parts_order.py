"""matches with several main files keep their timeline: the parts in upload order

Since Q-VIDEO-PARTS all main files of a match lie one after the other on the match timeline, in
the order of their match_segments rows. Before, event times referred to the first uploaded file
alone, and the rows were ordered by the camera clock. Matches that already have several parts get
them in upload order, confirmed, so the first uploaded file stays at the start of the timeline and
every stored time keeps its meaning. Data only; the downgrade leaves the rows as they are (the
earlier code reads them the same way).

Revision ID: 0044
Revises: 0043
Create Date: 2026-11-13 12:00:00.000000+00:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0044"
down_revision: str | None = "0043"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("SELECT set_config('app.bypass_rls', 'on', true)")
    op.execute(
        """
        WITH several AS (
            SELECT match_id FROM match_segments GROUP BY match_id HAVING count(*) > 1
        ),
        ordered AS (
            SELECT s.id,
                   row_number() OVER (
                       PARTITION BY s.match_id ORDER BY v.created_at, v.id
                   ) - 1 AS pos
            FROM match_segments s
            JOIN video_assets v ON v.id = s.video_id
            WHERE s.match_id IN (SELECT match_id FROM several)
        )
        UPDATE match_segments s
        SET position = ordered.pos, confirmed = true, source = 'upload_order'
        FROM ordered
        WHERE s.id = ordered.id
        """
    )
    op.execute("SELECT set_config('app.bypass_rls', 'off', true)")


def downgrade() -> None:
    pass
