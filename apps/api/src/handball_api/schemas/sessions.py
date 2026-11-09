"""Training planning and attendance (addendum 01, 5.7)."""

from __future__ import annotations

import uuid
from datetime import date, datetime, time
from typing import Literal

from pydantic import Field, model_validator

from handball_api.schemas.common import ApiModel


class DrillItem(ApiModel):
    """Snapshot of a library drill (or a free item) inside a session."""

    drill_id: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=200)
    minutes: int = Field(ge=1, le=180)
    focus: list[str] = Field(default_factory=list, max_length=10)
    setup: str | None = Field(default=None, max_length=2000)
    coaching: str | None = Field(default=None, max_length=2000)
    note: str | None = Field(default=None, max_length=500)


class TrainingSessionIn(ApiModel):
    on_date: date
    starts_at: datetime | None = None
    title: str | None = Field(default=None, max_length=120)
    location: str | None = Field(default=None, max_length=160)
    notes: str | None = Field(default=None, max_length=5000)
    drills: list[DrillItem] = Field(default_factory=list, max_length=30)


class TrainingSessionOut(ApiModel):
    id: uuid.UUID
    team_id: uuid.UUID
    on_date: date
    starts_at: datetime | None
    title: str | None
    location: str | None
    notes: str | None
    drills: list[DrillItem]
    total_minutes: int
    external_ref: str | None
    slot_id: uuid.UUID | None


class TrainingSlotIn(ApiModel):
    """A recurring training time; `valid_from` and `valid_until` default to the season."""

    weekday: int = Field(ge=1, le=7, description="ISO weekday: 1 Monday ... 7 Sunday")
    start_time: time = Field(description="Local time in Switzerland, e.g. 19:00")
    duration_min: int = Field(ge=15, le=300)
    location: str | None = Field(default=None, max_length=160)
    title: str | None = Field(default=None, max_length=120)
    note: str | None = Field(default=None, max_length=500)
    valid_from: date | None = None
    valid_until: date | None = None

    @model_validator(mode="after")
    def _order(self) -> TrainingSlotIn:
        if self.valid_from and self.valid_until and self.valid_from > self.valid_until:
            raise ValueError("valid_from must not be after valid_until")
        return self


class TrainingSlotOut(ApiModel):
    id: uuid.UUID
    team_id: uuid.UUID
    season_id: uuid.UUID
    weekday: int
    start_time: time
    end_time: time
    duration_min: int
    location: str | None
    title: str | None
    note: str | None
    valid_from: date | None
    valid_until: date | None


class SlotGenerateIn(ApiModel):
    """Create the sessions of the slots for a date range (default and limit: the season)."""

    start: date | None = Field(default=None, alias="from")
    end: date | None = Field(default=None, alias="to")
    skip_dates: list[date] = Field(
        default_factory=list, max_length=366, description="Holidays and other days without training"
    )
    slot_ids: list[uuid.UUID] | None = Field(
        default=None, max_length=50, description="Only these slots (default: every slot)"
    )


class SlotGenerateOut(ApiModel):
    created: int = Field(description="New sessions")
    kept: int = Field(description="Days with a session at that time already, left as they were")
    skipped: int = Field(description="Days left out because they are in skip_dates")
    sessions: list[TrainingSessionOut] = Field(description="The new sessions, by date")


Status = Literal["present", "absent", "excused", "injured", "late"]


class AttendanceRecord(ApiModel):
    player_id: uuid.UUID
    status: Status | None = None
    reason: str | None = Field(default=None, max_length=200)


class AttendanceIn(ApiModel):
    records: list[AttendanceRecord] = Field(max_length=100)


class AttendanceRow(ApiModel):
    player_id: uuid.UUID
    name: str
    number: int | None
    response: Literal["yes", "no"] | None
    status: Status | None
    reason: str | None


class MyReply(ApiModel):
    kind: Literal["session", "match"]
    id: uuid.UUID
    player_id: uuid.UUID
    response: Literal["yes", "no"]
    reason: str | None = Field(default=None, max_length=200)


class ScheduleItem(ApiModel):
    kind: Literal["session", "match"]
    id: uuid.UUID
    title: str | None
    team: str
    on_date: date
    starts_at: datetime | None
    player_id: uuid.UUID
    player_name: str
    relation: Literal["self", "guardian"]
    response: Literal["yes", "no"] | None


class CalendarLink(ApiModel):
    url: str
