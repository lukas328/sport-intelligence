"""The public entry: team search and preview from the federation's published data."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from handball_api.schemas.common import ApiModel


class PublicClub(ApiModel):
    id: int
    name: str
    city: str | None


class PublicTeamHit(ApiModel):
    official_id: int
    name: str
    league: str | None
    group_name: str | None
    club: PublicClub
    # the team is already in the app: saving asks that club's admins for access
    in_app: bool


class PublicGame(ApiModel):
    opponent: str
    home: bool
    own: int | None
    opp: int | None
    half_own: int | None
    half_opp: int | None
    kickoff_at: datetime
    venue: str | None


class PublicTableRow(ApiModel):
    rank: int | None
    name: str | None
    games: int | None
    points: int | None
    goal_difference: int | None
    own: bool


class PublicRun(ApiModel):
    result: Literal["w", "d", "l"]
    count: int


class PublicScorer(ApiModel):
    name: str
    goals: int


class PublicTeamPreview(ApiModel):
    official_id: int
    name: str
    club: PublicClub
    league: str | None
    group_name: str | None
    season: str
    last: PublicGame | None
    next: PublicGame | None
    rank: int | None
    table: list[PublicTableRow]
    form: list[Literal["w", "d", "l"]]
    run: PublicRun | None
    played: int
    scorers: list[PublicScorer]
    # how many played games the scorers come from (the federation's player statistics)
    scorer_games: int
    in_app: bool = False
