"""indexes on the foreign keys and lookups added with the official data and the candidates

Revision ID: 0034
Revises: 0033
Create Date: 2026-11-09 08:30:00.000000+00:00
"""
from collections.abc import Sequence

from alembic import op

revision: str = '0034'
down_revision: str | None = '0033'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# table -> columns: lookups by these columns, and the ON DELETE of the referenced row, would
# otherwise read the whole table
INDEXED = {
    'goal_candidates': ('event_id', 'reviewed_by_id'),
    'join_requests': (
        'player_id', 'suggested_player_id', 'suggested_suggestion_id', 'decided_by_id'
    ),
    'org_access_requests': ('team_id', 'decided_by_id'),
    'official_suggestions': ('resolved_by_id',),
    'organizations': ('claimed_by_id',),
}


def upgrade() -> None:
    for table, columns in INDEXED.items():
        for column in columns:
            op.create_index(op.f(f'ix_{table}_{column}'), table, [column], unique=False)


def downgrade() -> None:
    for table, columns in INDEXED.items():
        for column in columns:
            op.drop_index(op.f(f'ix_{table}_{column}'), table_name=table)
