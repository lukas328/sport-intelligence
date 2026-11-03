"""Event model shared by API, pipeline and importers (BRIEF 4.5)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class Side(StrEnum):
    OWN = "own"
    OPPONENT = "opponent"

    @property
    def other(self) -> Side:
        return Side.OPPONENT if self is Side.OWN else Side.OWN


class EventType(StrEnum):
    SHOT = "shot"
    PASS = "pass"  # noqa: S105 (event type, not a secret)
    TURNOVER = "turnover"
    STEAL = "steal"
    FOUL = "foul"
    FREE_THROW = "free_throw"
    SEVEN_METER_AWARDED = "seven_meter_awarded"
    SUSPENSION = "suspension_2min"
    YELLOW = "yellow_card"
    RED = "red_card"
    TIMEOUT = "timeout"
    THROW_OFF = "throw_off"
    SUBSTITUTION = "substitution"
    PERIOD_START = "period_start"
    PERIOD_END = "period_end"


SHOT_OUTCOMES = ("goal", "save", "miss", "post", "blocked")
TURNOVER_TYPES = (
    "bad_pass",
    "catch_error",
    "steps",
    "double_dribble",
    "offensive_foul",
    "line_violation",
    "passive_play",
    "other",
)
SHOT_TYPES = ("jump_shot", "standing", "pivot", "wing", "fast_break", "penalty", "empty_net")
SOURCES = (
    "model",
    "heuristic",
    "official_feed",
    "scoreboard_ocr",
    "goal_cam",
    "user_correction",
    "paper_report",
)


@dataclass(frozen=True)
class Event:
    id: str
    type: EventType
    side: Side
    period: int = 1
    clock_s: float | None = None  # match clock in seconds since throw-off of the game (0..3600)
    t_ms: int | None = None  # video time
    player_id: str | None = None
    number: int | None = None  # jersey number (used for opponents without roster)
    x: float | None = None  # court position normalised to attack towards x = 40
    y: float | None = None
    outcome: str | None = None  # shots: goal, save, miss, post, blocked
    shot_zone: str | None = None
    goal_zone: str | None = None  # TL..BR from the shooter's view
    shot_type: str | None = None
    turnover_type: str | None = None
    assist_player_id: str | None = None
    confidence: float = 1.0
    source: str = "user_correction"
    attributes: dict[str, Any] = field(default_factory=dict)

    @property
    def is_shot(self) -> bool:
        return self.type is EventType.SHOT

    @property
    def is_goal(self) -> bool:
        return self.is_shot and self.outcome == "goal"
