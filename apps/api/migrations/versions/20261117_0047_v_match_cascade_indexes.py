"""indexes on the foreign keys a match deletion follows

Deleting a match removes its clips, events and videos by ON DELETE CASCADE; for every removed row
the database looks up the rows pointing at it (CASCADE or SET NULL). These columns had no index,
so each lookup read the whole table while the delete held its locks.

Revision ID: 0047
Revises: 0046
Create Date: 2026-11-17 10:00:00.000000+00:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0047"
down_revision: str | None = "0046"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

COLUMNS = (
    ("focus_plans", "match_id"),
    ("collection_items", "clip_id"),
    ("comments", "clip_id"),
    ("player_feed_items", "clip_id"),
    ("presentation_slides", "clip_id"),
    ("live_tags", "event_id"),
    ("live_tag_sessions", "video_id"),
)


def upgrade() -> None:
    for table, column in COLUMNS:
        op.create_index(op.f(f"ix_{table}_{column}"), table, [column], unique=False)


def downgrade() -> None:
    for table, column in reversed(COLUMNS):
        op.drop_index(op.f(f"ix_{table}_{column}"), table_name=table)
