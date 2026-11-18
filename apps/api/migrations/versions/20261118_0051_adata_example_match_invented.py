"""the example match mixes with nothing real (data only)

App review A2, A4 (18.11.2026): the example match of «Demo-Spiel ansehen» took the team's real
players for its goals and saves and was dated two days before it was opened, like a real match;
its opponent «Demo HC Beispiel» read like a placeholder. The example is recognised by its source
('demo', migration 0048), never by the opponent's name. For the examples that exist:

- the opponent «Demo HC Beispiel» of example matches (no counted match of the club against it) is
  renamed to «TSV Nachtwind», the invented opponent of the demo story;
- the example's events name no player of the roster: the player link and the credited own
  goalkeeper are kept in the event's attributes (demo_player_id, demo_goalkeeper_id) and the save
  goes to the example's invented goalkeeper number 12;
- the kickoff moves to the first day of the match's season (summer break, far from any fixture);
  the old one is kept in report_extra.demo_kickoff_was.

The downgrade restores all of it (a player deleted since stays unlinked).

Revision ID: 0051
Revises: 0050
Create Date: 2026-11-18 09:00:00.000000+00:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0051"
down_revision: str | None = "0050"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD_NAME = "Demo HC Beispiel"
NEW_NAME = "TSV Nachtwind"
EXAMPLE_ONLY = """
    EXISTS (SELECT 1 FROM matches m WHERE m.opponent_id = opponents.id AND m.source = 'demo')
    AND NOT EXISTS (
        SELECT 1 FROM matches m WHERE m.opponent_id = opponents.id AND m.source <> 'demo'
    )
"""
EXAMPLE_EVENTS = "match_id IN (SELECT id FROM matches WHERE source = 'demo') AND source = 'demo'"


def upgrade() -> None:
    op.execute(
        f"UPDATE opponents SET name = '{NEW_NAME}' WHERE name = '{OLD_NAME}' AND {EXAMPLE_ONLY}"
    )
    op.execute(
        f"""
        UPDATE events
        SET attributes = COALESCE(attributes, '{{}}'::jsonb)
                || jsonb_build_object('demo_player_id', player_id::text),
            player_id = NULL
        WHERE {EXAMPLE_EVENTS} AND player_id IS NOT NULL
        """
    )
    op.execute(
        f"""
        UPDATE events
        SET attributes = (attributes - 'goalkeeper_id')
                || jsonb_build_object(
                    'demo_goalkeeper_id', attributes->>'goalkeeper_id', 'goalkeeper_number', 12
                )
        WHERE {EXAMPLE_EVENTS} AND attributes ? 'goalkeeper_id'
        """
    )
    op.execute(
        """
        UPDATE matches
        SET report_extra = COALESCE(report_extra, '{}'::jsonb)
                || jsonb_build_object('demo_kickoff_was', to_jsonb(matches.kickoff_at)),
            kickoff_at = (s.starts_on + time '16:00') AT TIME ZONE 'UTC'
        FROM seasons s
        WHERE matches.season_id = s.id AND matches.source = 'demo'
          AND s.starts_on <= CURRENT_DATE
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE matches
        SET kickoff_at = (report_extra->>'demo_kickoff_was')::timestamptz,
            report_extra = report_extra - 'demo_kickoff_was'
        WHERE source = 'demo' AND report_extra ? 'demo_kickoff_was'
        """
    )
    op.execute(
        f"""
        UPDATE events
        SET attributes = (attributes - 'demo_goalkeeper_id' - 'goalkeeper_number')
                || CASE WHEN EXISTS (
                    SELECT 1 FROM players p WHERE p.id::text = attributes->>'demo_goalkeeper_id'
                ) THEN jsonb_build_object('goalkeeper_id', attributes->>'demo_goalkeeper_id')
                ELSE '{{}}'::jsonb END
        WHERE {EXAMPLE_EVENTS} AND attributes ? 'demo_goalkeeper_id'
        """
    )
    op.execute(
        f"""
        UPDATE events
        SET player_id = (
                SELECT p.id FROM players p WHERE p.id::text = events.attributes->>'demo_player_id'
            ),
            attributes = attributes - 'demo_player_id'
        WHERE {EXAMPLE_EVENTS} AND attributes ? 'demo_player_id'
        """
    )
    op.execute(
        f"UPDATE opponents SET name = '{OLD_NAME}' WHERE name = '{NEW_NAME}' AND {EXAMPLE_ONLY}"
    )
