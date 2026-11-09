"""A player's season line: figures per match with the events behind them (M7)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from handball_api.models.enums import AttendanceStatus, Position
from handball_api.schemas.common import ApiModel


class LineFigures(ApiModel):
    """A player's figures as the match statistics count them (one source per goal). Field
    player: `shots` are on target (blocked ones apart, as on the match page), `turnovers` are
    technical faults, `suspensions` 2-minute suspensions. Goalkeeper (credited by the keeper
    recorded on the shot): `faced` = `saves` + `goals_against`."""

    goals: int
    shots: int
    misses: int
    posts: int
    saved: int
    blocked: int
    seven_m_goals: int
    seven_m_shots: int
    assists: int
    turnovers: int
    suspensions: int
    yellow_cards: int
    red_cards: int
    faced: int
    saves: int
    goals_against: int
    seven_m_faced: int
    seven_m_saves: int


class LineEvents(ApiModel):
    """The event ids behind each figure (same keys, as many ids as the figure counts), in
    match-clock order: open the clips with them."""

    goals: list[uuid.UUID]
    shots: list[uuid.UUID]
    misses: list[uuid.UUID]
    posts: list[uuid.UUID]
    saved: list[uuid.UUID]
    blocked: list[uuid.UUID]
    seven_m_goals: list[uuid.UUID]
    seven_m_shots: list[uuid.UUID]
    assists: list[uuid.UUID]
    turnovers: list[uuid.UUID]
    suspensions: list[uuid.UUID]
    yellow_cards: list[uuid.UUID]
    red_cards: list[uuid.UUID]
    faced: list[uuid.UUID]
    saves: list[uuid.UUID]
    goals_against: list[uuid.UUID]
    seven_m_faced: list[uuid.UUID]
    seven_m_saves: list[uuid.UUID]


class SeasonLineMatch(ApiModel):
    match_id: uuid.UUID
    kickoff_at: datetime
    opponent: str
    is_home: bool
    competition: str | None
    # the stored result, else the goals of the events (as the season statistics)
    score_own: int | None
    score_opponent: int | None
    result: Literal["win", "draw", "loss"] | None
    # events are recorded for the match; without, every figure is 0 and says nothing
    tagged: bool
    # at least one event of the player (or credited to them as goalkeeper)
    involved: bool
    # attendance recorded by the staff (present, absent, ...) and the player's reply (yes/no);
    # no playing minutes are recorded
    attendance: AttendanceStatus | None
    response: str | None
    figures: LineFigures
    shooting_pct: float | None
    save_pct: float | None
    events: LineEvents


class SeasonLineTotals(LineFigures):
    matches: int
    tagged_matches: int
    matches_involved: int
    matches_present: int
    shooting_pct: float | None
    save_pct: float | None


class SeasonLine(ApiModel):
    player_id: uuid.UUID
    team_id: uuid.UUID
    season_id: uuid.UUID
    first_name: str
    last_name: str
    jersey_number: int | None
    main_position: Position | None
    matches: list[SeasonLineMatch]
    totals: SeasonLineTotals
