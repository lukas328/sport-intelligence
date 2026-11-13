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
    t_ms: int = Field(ge=0, description="a time in the video")
    clock_s: float | None = Field(
        default=None,
        ge=0,
        le=4 * 3600,
        description="match clock (s) shown at t_ms; default: the half's throw-off. A video that "
        "starts after the throw-off (a clip from mid-half) gets its clock this way.",
    )
    absent: bool = Field(
        default=False,
        description="the throw-off is not in the video (a clip, a recording that starts later): "
        "Prüfen stops asking; with clock_s the video start gets that match clock",
    )


class OfficialReportIn(ApiModel):
    # handball.ch match centre, DHB press report, nuLiga game report (page or PDF) or HLA report
    # link; a plain game id needs the provider (nuLiga: the link, it names the association)
    url: str = Field(min_length=1, max_length=500)
    provider: Literal["handball_ch", "dhb", "hla"] | None = None


class OfficialReportResult(ApiModel):
    provider: str  # handball_ch, dhb, nuliga, hla
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
CandidateKind = Literal["goal", "shot"]
ShotOutcome = Literal["goal", "save", "miss", "post", "blocked"]


class CandidateGoal(ApiModel):
    """A shot already stored that covers a candidate (same moment)."""

    event_id: uuid.UUID
    source: str
    side: str
    t_ms: int | None
    outcome: str | None = None


class OfficialShot(ApiModel):
    """A shot of the official report and where it lies on the video."""

    event_id: uuid.UUID
    side: str
    outcome: str | None
    penalty: bool
    number: int | None
    player_id: uuid.UUID | None
    name: str | None
    period: int
    clock_s: float | None
    official_time: str | None
    # video time: confirmed on the video, else from the match clock (overlay clock, confirmed
    # entries and throw-offs as anchors)
    t_ms: int | None
    uncertainty_ms: int | None  # 0: exact (overlay clock or confirmed), null: unknown


class GoalCandidateRow(ApiModel):
    """A moment of the video that is probably a goal or a shot (analysis), with the coach's
    review."""

    id: uuid.UUID
    kind: CandidateKind
    video_asset_id: uuid.UUID
    t_ms: int  # score peak, a median 1.5 s after the goal or shot
    goal_ms: int  # estimated goal (shot) time (the event gets it on confirmation)
    start_ms: int  # clip: 10 s (shots 8 s) before to 4 s after the peak
    end_ms: int
    score: float
    rate: int  # lowest candidates-per-minute rate (goals 1, 2, 4; shots 2, 4, 6) proposing it
    suggested_side: Side | None  # whose attack ended just before it
    status: CandidateStatus
    side: Side | None  # confirmed: whose shot
    outcome: ShotOutcome | None  # confirmed: the shot's outcome
    event_id: uuid.UUID | None  # confirmed: the shot event (or the report entry it pinned)
    period: int | None
    clock_s: float | None
    known: CandidateGoal | None  # open but already a known shot (overlay, report, tagged)
    # shot candidates with an official report: the report shot at this moment; confirming
    # without a side takes it (one key)
    suggestion: OfficialShot | None = None


class GoalCandidateCounts(ApiModel):
    total: int
    open: int  # open and not covered by a known shot
    open_by_rate: dict[str, int]
    confirmed: int
    rejected: int
    known: int
    suggested: int = 0  # open with a suggestion from the official report


class OfficialShotRow(OfficialShot):
    # confirmed: on the video (a candidate, or the overlay for goals); suggested: an open
    # candidate suggests it; outside: before or after the video; missing: no candidate near it
    status: Literal["confirmed", "suggested", "missing", "outside"]
    candidate_id: uuid.UUID | None


class OfficialShotCounts(ApiModel):
    total: int
    confirmed: int
    suggested: int
    missing: int
    outside: int


class OfficialShots(ApiModel):
    counts: OfficialShotCounts
    shots: list[OfficialShotRow]


class GoalCandidateList(ApiModel):
    kind: CandidateKind = "goal"
    template: str | None
    rates: list[int]
    default_rate: int
    counts: GoalCandidateCounts
    candidates: list[GoalCandidateRow]
    official: OfficialShots | None = None  # shot candidates: the report's shots on the video


class GoalCandidateReviewIn(ApiModel):
    status: Literal["confirmed", "rejected"] | None  # null: back to open (undo)
    # to confirm: whose shot and its outcome (goal candidates: default goal); a shot candidate
    # without a side takes its suggestion from the official report
    side: Side | None = None
    outcome: ShotOutcome | None = None
    official_event_id: uuid.UUID | None = None  # pin this report entry to the candidate
    number: int | None = Field(default=None, ge=0, le=99)  # scorer, when no report entry
    player_id: uuid.UUID | None = None


class FeedImportResult(ApiModel):
    created: int
    skipped: int
    errors: list[str]
