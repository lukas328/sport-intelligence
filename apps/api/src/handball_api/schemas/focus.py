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
