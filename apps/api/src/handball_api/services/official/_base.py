"""Settings and small helpers shared by the official data modules."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from handball_api.core.errors import ProblemError
from handball_api.core.logging import get_logger
from handball_api.integrations import handball_ch as ch

log = get_logger("handball_api.official")
PROVIDER = ch.PROVIDER
MIN_QUERY = 3
MAX_CLUBS = 5
# shirt numbers and appearances from the last played games (cached forever once played)
STATS_GAMES = 10
SYNC_EVERY = timedelta(hours=20)
SYNC_BATCH = 20
REPORT_AFTER = timedelta(minutes=90)  # a game is over and the log complete
REPORT_WINDOW = timedelta(days=7)
# the reports of the season's earlier games (a team taken over in mid-season, a game whose report
# was only offered): imported by the tick too, so the scorers of every report count everywhere
# (app review R3); a game without a log by then is asked this often and then left alone
REPORT_BACKFILL_TRIES = 3
REPORT_BATCH = 20
# a game without a game log yet: asked again after an hour, then after ever longer waits
REPORT_RETRY = timedelta(hours=1)
REPORT_RETRY_MAX = timedelta(days=1)
SYSTEM_USER = uuid.UUID(int=0)
# reason of a match_new suggestion made at the claim instead of a match: the plan's match limit
PLAN_LIMIT = "plan_limit"
# team preference (team.settings): show the official statistics in roster suggestions
ROSTER_STATS = "official_roster_stats"


def _now() -> datetime:
    return datetime.now(UTC)


def _unavailable(exc: Exception) -> ProblemError:
    return ProblemError(
        503, "official-unavailable", "handball.ch does not answer right now, try again later"
    )
