from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import Field, model_validator

from handball_api.schemas.common import ApiModel, Name

PlayCategory = Literal["attack", "defence", "fast_break", "set_piece", "seven_m", "other"]


class TokenIn(ApiModel):
    id: str = Field(min_length=1, max_length=8)
    side: Literal["own", "opp"]
    label: str = Field(max_length=3)
    x: float = Field(ge=-2, le=42)
    y: float = Field(ge=-2, le=22)


class ArrowIn(ApiModel):
    kind: Literal["run", "pass", "screen", "dribble"]
    points: list[tuple[float, float]] = Field(min_length=2, max_length=12)


class BallIn(ApiModel):
    x: float = Field(ge=-2, le=42)
    y: float = Field(ge=-2, le=22)


class FrameIn(ApiModel):
    tokens: list[TokenIn] = Field(max_length=16)
    ball: BallIn | None = None
    arrows: list[ArrowIn] = Field(default_factory=list, max_length=20)
    note: str = Field(default="", max_length=300)
    duration_ms: int = Field(ge=300, le=10_000)

    @model_validator(mode="after")
    def _unique(self) -> FrameIn:
        if len({t.id for t in self.tokens}) != len(self.tokens):
            raise ValueError("token ids must be unique within a frame")
        return self


class PlayDocIn(ApiModel):
    """Tactics board document, format version 1 (packages/tactics/src/format.ts)."""

    formatVersion: Literal[1]  # noqa: N815 (shared JSON format)
    court: Literal["half", "full"]
    frames: list[FrameIn] = Field(min_length=1, max_length=30)


class PlaySource(ApiModel):
    match_id: uuid.UUID
    t_ms: int = Field(ge=0)


class PlayCreate(ApiModel):
    name: Name
    category: PlayCategory
    formation: str | None = Field(default=None, max_length=20)
    description: str | None = Field(default=None, max_length=4000)
    tags: list[str] = Field(default_factory=list, max_length=12)
    doc: PlayDocIn
    source: PlaySource | None = None
    shared_with_players: bool = False

    @model_validator(mode="after")
    def _tags(self) -> PlayCreate:
        self.tags = sorted({t.strip()[:30] for t in self.tags if t.strip()})
        return self


class PlayUpdate(ApiModel):
    name: Name | None = None
    category: PlayCategory | None = None
    formation: str | None = Field(default=None, max_length=20)
    description: str | None = Field(default=None, max_length=4000)
    tags: list[str] | None = Field(default=None, max_length=12)
    doc: PlayDocIn | None = None
    shared_with_players: bool | None = None


class PlayOut(ApiModel):
    id: uuid.UUID
    team_id: uuid.UUID
    name: str
    category: str
    formation: str | None
    description: str | None
    tags: list[str]
    doc: dict[str, Any]
    source: dict[str, Any] | None
    shared_with_players: bool
    created_at: datetime
    updated_at: datetime
