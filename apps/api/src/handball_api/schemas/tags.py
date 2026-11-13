from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import Field

from handball_api.schemas.common import ApiModel, HexColor


class TagIn(ApiModel):
    name: str = Field(min_length=1, max_length=60)
    color: HexColor | None = None
    hotkey: str | None = Field(default=None, pattern=r"^[a-z0-9]$")


class TagPatch(ApiModel):
    name: str | None = Field(default=None, min_length=1, max_length=60)
    color: HexColor | None = None
    hotkey: str | None = Field(default=None, pattern=r"^[a-z0-9]$")


class TagOut(ApiModel):
    id: uuid.UUID
    name: str
    color: str | None
    hotkey: str | None


class TagSetIn(ApiModel):
    name: str = Field(min_length=1, max_length=60)
    tags: list[TagIn] = Field(default_factory=list, max_length=50)


class TagSetOut(ApiModel):
    id: uuid.UUID
    name: str
    tags: list[TagOut]


class TagLinksIn(ApiModel):
    """Replaces the team tags on one target (clip, event or play)."""

    target_type: Literal["clip", "event", "play"]
    target_id: uuid.UUID
    tag_ids: list[uuid.UUID] = Field(max_length=50)


class MatchTagLinks(ApiModel):
    clips: dict[uuid.UUID, list[uuid.UUID]]
    events: dict[uuid.UUID, list[uuid.UUID]]


class SearchFilter(ApiModel):
    """Combines automatic attributes and own tags (4.4). Empty lists mean "any"."""

    season_id: uuid.UUID | None = None
    match_ids: list[uuid.UUID] = Field(default_factory=list, max_length=200)
    opponent_id: uuid.UUID | None = None
    kind: Literal["match", "training"] | None = None
    types: list[str] = Field(default_factory=list, max_length=20)
    sides: list[Literal["own", "opponent"]] = Field(default_factory=list)
    outcomes: list[str] = Field(default_factory=list, max_length=20)
    player_ids: list[uuid.UUID] = Field(default_factory=list, max_length=50)
    numbers: list[int] = Field(default_factory=list, max_length=50)
    shot_zones: list[str] = Field(default_factory=list, max_length=20)
    goal_zones: list[str] = Field(default_factory=list, max_length=20)
    turnover_types: list[str] = Field(default_factory=list, max_length=20)
    tags_all: list[uuid.UUID] = Field(default_factory=list, max_length=20)
    tags_any: list[uuid.UUID] = Field(default_factory=list, max_length=20)
    include_clips: bool = True
    limit: int = Field(default=200, ge=1, le=500)


class SearchHit(ApiModel):
    kind: Literal["event", "clip"]
    id: uuid.UUID
    match_id: uuid.UUID
    match_label: str
    kickoff_at: datetime
    video_id: uuid.UUID | None
    start_ms: int | None
    end_ms: int | None
    t_ms: int | None
    clock_s: float | None = Field(
        default=None, description="the match clock of an event, where it is known"
    )
    type: str | None = None
    side: str | None = None
    outcome: str | None = None
    number: int | None = None
    player_id: uuid.UUID | None = None
    title: str | None = None
    tag_ids: list[uuid.UUID]


class SearchResult(ApiModel):
    hits: list[SearchHit]
    total: int
    truncated: bool
    facets: dict[str, dict[str, int]] = Field(
        description="counts per event type and per tag id over all hits"
    )


class SavedFilterIn(ApiModel):
    name: str = Field(min_length=1, max_length=120)
    query: SearchFilter


class SavedFilterOut(ApiModel):
    id: uuid.UUID
    name: str
    query: SearchFilter
    created_at: datetime
