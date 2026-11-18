"""From a problem to training (addendum 01, 5.6)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import Field

from handball_api.schemas.common import ApiModel
from handball_api.schemas.sessions import DrillItem


class FocusSessionIn(ApiModel):
    on_date: date
    starts_at: datetime | None = None
    drills: list[DrillItem] = Field(default_factory=list, max_length=30)


class FocusIn(ApiModel):
    insight_key: str = Field(min_length=3, max_length=60)
    params: dict[str, Any] = Field(default_factory=dict)
    title: str | None = Field(default=None, max_length=200)
    note: str | None = Field(default=None, max_length=2000)
    session: FocusSessionIn | None = None
    playlist: bool = True
    assignment: bool = False


class FollowSide(ApiModel):
    matches: int
    value: float | None
    per_match: float | None
    sample: int | None


class Followup(ApiModel):
    metric: str
    before: FollowSide
    after: FollowSide
    trend: Literal["better", "worse", "same"] | None
    small_sample: bool
    note: str


class FocusOut(ApiModel):
    id: uuid.UUID
    team_id: uuid.UUID
    match_id: uuid.UUID | None
    insight_key: str
    params: dict[str, Any]
    focus: list[str]
    metric: str | None
    filter: dict[str, Any]
    higher_is_better: bool
    session_id: uuid.UUID | None
    playlist_id: uuid.UUID | None
    assignment_id: uuid.UUID | None
    closed_at: datetime | None
    created_at: datetime
    followup: Followup | None = None


class TipScene(ApiModel):
    event_id: uuid.UUID
    t_ms: int
    period: int | None
    clock_s: float | None


class TipMatch(ApiModel):
    match_id: uuid.UUID
    kickoff_at: datetime
    opponent: str | None


class TrainingTip(ApiModel):
    """A weakness of the last matches with a training topic (K21)."""

    id: str
    key: str
    params: dict[str, Any]
    evidence: dict[str, Any]
    sample: int | None
    score: float
    match_id: uuid.UUID = Field(description="The latest match the weakness came up in")
    matches: int = Field(description="In how many of the analysed matches it came up")
    of: int = Field(description="Matches analysed")
    topics: list[str]
    metric: str
    drills: list[str] = Field(description="Library drill ids for the topics")
    scenes: list[TipScene]


class TrainingTipsOut(ApiModel):
    matches_analysed: int = Field(description="Matches the tips are drawn from (with events)")
    matches_with_analysis: int = Field(
        default=0, description="Of these, matches with data beyond the official report"
    )
    matches_from_report: int = Field(
        default=0, description="Of these, matches known only from the official report"
    )
    plan_required: bool
    matches: list[TipMatch]
    tips: list[TrainingTip]
