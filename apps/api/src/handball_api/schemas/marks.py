"""Courtside marks with device time (addendum 01, 5.3)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field

from handball_api.schemas.common import ApiModel, HexColor


class MarkKey(ApiModel):
    key: str = Field(min_length=1, max_length=40, pattern=r"^[a-z0-9_]+$")
    label: str | None = Field(default=None, max_length=30)
    color: HexColor | None = None


class MarkKeysIn(ApiModel):
    keys: list[MarkKey] = Field(min_length=4, max_length=8)


class MarkSessionIn(ApiModel):
    device: str | None = Field(default=None, max_length=120)


class MarkSessionOut(ApiModel):
    id: uuid.UUID
    match_id: uuid.UUID
    started_at: datetime
    offset_ms: int | None
    sync_confidence: float | None
    sync_source: str | None


class MarkIn(ApiModel):
    client_id: uuid.UUID
    device_time: datetime
    key: str = Field(min_length=1, max_length=40)
    note: str | None = Field(default=None, max_length=300)


class MarksIn(ApiModel):
    marks: list[MarkIn] = Field(max_length=500)


class OffsetIn(ApiModel):
    offset_ms: int


class SyncOut(ApiModel):
    session_id: uuid.UUID
    offset_ms: int | None
    confidence: float | None
    source: str | None
    matched: int


class MarkOut(ApiModel):
    id: uuid.UUID
    session_id: uuid.UUID
    key: str
    label: str | None
    note: str | None
    device_time: datetime
    half: int
    t_ms: int | None


class MarkSessionInfo(ApiModel):
    id: uuid.UUID
    device: str | None
    started_at: datetime
    offset_ms: int | None
    confidence: float | None
    source: str | None


class MatchMarks(ApiModel):
    sessions: list[MarkSessionInfo]
    marks: list[MarkOut]
