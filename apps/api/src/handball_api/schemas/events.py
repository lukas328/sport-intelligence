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
    # set by offline clients (live mode): a retry with the same id returns the stored event
    client_id: uuid.UUID | None = None
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
    client_id: uuid.UUID | None = None
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


class OfficialReportIn(ApiModel):
    # handball.ch match centre or DHB press report link; a plain game id needs the provider
    url: str = Field(min_length=1, max_length=500)
    provider: Literal["handball_ch", "dhb"] | None = None


class OfficialReportResult(ApiModel):
    provider: str
    game_id: int
    source_url: str
    home: str | None
    away: str | None
    final: list[int] | None
    created: int
    replaced: int  # official report events of an earlier import
    matched_video_goals: int  # automatic goals that are the same goal (video time kept)
    unmatched_video_goals: int  # overlay goals without an official counterpart (kept)
    kept_manual_goals: int  # goals entered by a person (no official duplicate added)
    skipped: int
    warnings: list[str]


ReviewStatus = Literal["confirmed", "dismissed"]


class VideoReading(ApiModel):
    """What the video analysis read for an official goal."""

    source: str  # scoreboard_ocr (broadcast overlay or hall scoreboard), heuristic, model
    t_ms: int | None
    clock_s: float | None
    confidence: float | None
    event_id: uuid.UUID | None  # the automatic goal paired at read time (none: merged on import)


class OfficialGoalRow(ApiModel):
    event_id: uuid.UUID
    side: str
    period: int
    clock_s: float | None
    official_time: str | None  # match time as in the report, "MM:SS"
    t_ms: int | None  # video time: the video reading, else derived from the match clock
    estimated: bool  # t_ms comes from the match clock only
    number: int | None
    player_id: uuid.UUID | None
    name: str | None
    score: list[int] | None  # own, opponent after the goal
    penalty: bool
    # outside: not found, and its time from the match clock is before or after the main video
    status: Literal["found", "missing", "outside"]
    video: VideoReading | None
    review: ReviewStatus | None


class VideoGoalRow(ApiModel):
    """An automatic goal from the video with no official counterpart."""

    event_id: uuid.UUID
    side: str
    period: int
    clock_s: float | None
    official_time: str | None
    t_ms: int | None
    source: str
    confidence: float
    number: int | None
    player_id: uuid.UUID | None
    name: str | None
    score: list[int] | None
    review: ReviewStatus | None


class GoalComparisonCounts(ApiModel):
    official: int
    found: int  # official goals the video saw
    missing: int  # official goals the video did not see (within the video's time range)
    outside: int  # official goals before or after the main video (a clip of part of the game)
    extra: int  # video goals without an official one
    open: int  # missing and extra rows nobody confirmed or dismissed yet


class GoalComparison(ApiModel):
    imported: bool
    provider: str | None
    source_url: str | None
    home: str | None
    away: str | None
    window_s: float  # an official and a video goal of the same side this close are the same goal
    counts: GoalComparisonCounts
    goals: list[OfficialGoalRow]
    extra: list[VideoGoalRow]


class GoalReviewIn(ApiModel):
    event_id: uuid.UUID
    status: ReviewStatus | None  # null: undo the check


CandidateStatus = Literal["open", "confirmed", "rejected"]


class CandidateGoal(ApiModel):
    """A goal already stored that covers a candidate (same moment)."""

    event_id: uuid.UUID
    source: str
    side: str
    t_ms: int | None


class GoalCandidateRow(ApiModel):
    """A moment of the video that is probably a goal (analysis), with the coach's review."""

    id: uuid.UUID
    video_asset_id: uuid.UUID
    t_ms: int  # score peak, a median 1.5 s after the goal
    goal_ms: int  # estimated goal time (the goal event gets it on confirmation)
    start_ms: int  # clip: 10 s before to 4 s after the peak
    end_ms: int
    score: float
    rate: int  # lowest candidates-per-minute rate (1, 2, 4) that proposes it
    suggested_side: Side | None  # whose attack ended just before it
    status: CandidateStatus
    side: Side | None  # confirmed: whose goal
    event_id: uuid.UUID | None  # confirmed: the goal event
    period: int | None
    clock_s: float | None
    known: CandidateGoal | None  # open but already a goal (overlay, report, tagged)


class GoalCandidateCounts(ApiModel):
    total: int
    open: int  # open and not covered by a known goal
    open_by_rate: dict[str, int]
    confirmed: int
    rejected: int
    known: int


class GoalCandidateList(ApiModel):
    template: str | None
    rates: list[int]
    default_rate: int
    counts: GoalCandidateCounts
    candidates: list[GoalCandidateRow]


class GoalCandidateReviewIn(ApiModel):
    status: Literal["confirmed", "rejected"] | None  # null: back to open (undo)
    side: Side | None = None  # required to confirm

    @model_validator(mode="after")
    def _side(self) -> GoalCandidateReviewIn:
        if self.status == "confirmed" and self.side is None:
            raise ValueError("a confirmed goal needs the side that scored")
        return self


class FeedImportResult(ApiModel):
    created: int
    skipped: int
    errors: list[str]
