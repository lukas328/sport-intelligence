"""Statistics matrix (addendum 01, 5.4)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import Field

from handball_api.schemas.common import ApiModel


class MatrixIn(ApiModel):
    rows: str = Field(description="Row dimension: number, position, play, match, period, ...")
    metrics: list[str] = Field(min_length=1, max_length=8)
    filter: dict[str, Any] = Field(default_factory=dict)


class ClipRef(ApiModel):
    event_id: str
    match_id: str
    t_ms: int | None = None


class MatrixCell(ApiModel):
    value: float | None
    numerator: float
    denominator: int | None
    events: int
    event_ids: list[str]
    clips: list[ClipRef]


class MatrixRow(ApiModel):
    key: str
    label: str
    cells: dict[str, MatrixCell]


class MatrixOut(ApiModel):
    by: str
    metrics: list[str]
    definitions: dict[str, str]
    rows: list[MatrixRow]
    totals: MatrixRow


class TemplateIn(ApiModel):
    name: str = Field(min_length=1, max_length=120)
    config: MatrixIn


class TemplateOut(ApiModel):
    id: uuid.UUID
    team_id: uuid.UUID
    name: str
    config: MatrixIn
    created_at: datetime
