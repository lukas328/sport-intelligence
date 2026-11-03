from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import Field, model_validator

from handball_api.schemas.common import ApiModel

EventType = Literal[
    "shot",
    "turnover",
    "steal",
    "foul",
    "free_throw",
    "seven_meter_awarded",
    "suspension_2min",
    "yellow_card",
    "red_card",
    "timeout",
    "throw_off",
    "substitution",
]
Side = Literal["own", "opponent"]
GoalZone = Literal["TL", "TC", "TR", "ML", "MC", "MR", "BL", "BC", "BR"]


class EventIn(ApiModel):
    type: EventType
    side: Side
    period: int = Field(default=1, ge=1, le=4)
    clock_s: float | None = Field(default=None, ge=0, le=5400)
    t_ms: int | None = Field(default=None, ge=0)
    player_id: uuid.UUID | None = None
    number: int | None = Field(default=None, ge=0, le=99)
    x: float | None = Field(default=None, ge=-2, le=42)
    y: float | None = Field(default=None, ge=-2, le=22)
    outcome: Literal["goal", "save", "miss", "post", "blocked"] | None = None
    goal_zone: GoalZone | None = None
    shot_type: (
        Literal["jump_shot", "standing", "pivot", "wing", "fast_break", "penalty", "empty_net"]
        | None
    ) = None
    turnover_type: (
        Literal[
            "bad_pass",
            "catch_error",
            "steps",
            "double_dribble",
            "offensive_foul",
            "line_violation",
            "passive_play",
            "other",
        ]
        | None
    ) = None
    assist_player_id: uuid.UUID | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _consistent(self) -> EventIn:
        if self.type == "shot" and self.outcome is None:
            raise ValueError("a shot needs an outcome")
        if self.type != "shot" and (self.outcome or self.goal_zone or self.shot_type):
            raise ValueError("outcome, goal zone and shot type only apply to shots")
        if self.type != "turnover" and self.turnover_type:
            raise ValueError("turnover type only applies to turnovers")
        if (self.x is None) != (self.y is None):
            raise ValueError("give both x and y")
        if len(str(self.attributes)) > 2000:
            raise ValueError("attributes too large")
        return self


class EventPatch(ApiModel):
    side: Side | None = None
    period: int | None = Field(default=None, ge=1, le=4)
    clock_s: float | None = Field(default=None, ge=0, le=5400)
    t_ms: int | None = Field(default=None, ge=0)
    player_id: uuid.UUID | None = None
    number: int | None = Field(default=None, ge=0, le=99)
    x: float | None = Field(default=None, ge=-2, le=42)
    y: float | None = Field(default=None, ge=-2, le=22)
    outcome: Literal["goal", "save", "miss", "post", "blocked"] | None = None
    goal_zone: GoalZone | None = None
    shot_type: (
        Literal["jump_shot", "standing", "pivot", "wing", "fast_break", "penalty", "empty_net"]
        | None
    ) = None
    turnover_type: (
        Literal[
            "bad_pass",
            "catch_error",
            "steps",
            "double_dribble",
            "offensive_foul",
            "line_violation",
            "passive_play",
            "other",
        ]
        | None
    ) = None
    assist_player_id: uuid.UUID | None = None


class EventOut(ApiModel):
    id: uuid.UUID
    type: str
    side: str
    period: int
    clock_s: float | None
    t_ms: int | None
    player_id: uuid.UUID | None
    number: int | None
    x: float | None
    y: float | None
    outcome: str | None
    shot_zone: str | None
    goal_zone: str | None
    shot_type: str | None
    turnover_type: str | None
    assist_player_id: uuid.UUID | None
    confidence: float
    source: str
    attributes: dict[str, Any]
    created_at: datetime


class KickoffIn(ApiModel):
    period: int = Field(ge=1, le=4)
    t_ms: int = Field(ge=0)


class FeedImportResult(ApiModel):
    created: int
    skipped: int
    errors: list[str]
