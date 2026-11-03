"""Public player profile (addendum 01, 5.8)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field

from handball_api.schemas.common import ApiModel


class ProfileIn(ApiModel):
    active: bool = False
    bio: str | None = Field(default=None, max_length=400)
    stats: list[str] = Field(default_factory=list, max_length=7)
    reel_ids: list[uuid.UUID] = Field(default_factory=list, max_length=5)
    show_position: bool = True
    show_hand: bool = True
    indexable: bool = False


class ProfileOut(ApiModel):
    slug: str
    active: bool
    views: int
    bio: str | None
    stats: list[str]
    reel_ids: list[str]
    show_position: bool
    show_hand: bool
    indexable: bool


class ReelRef(ApiModel):
    id: uuid.UUID
    created_at: datetime
    format: str


class MyProfile(ApiModel):
    player_id: uuid.UUID
    name: str
    relation: str
    blocked: str | None
    profile: ProfileOut | None
    reels: list[ReelRef]
    stats_available: list[str]


class PublicProfileOut(ApiModel):
    name: str
    club: str
    team: str
    position: str | None
    shooting_hand: str | None
    bio: str | None
    stats: dict[str, float | int | None]
    reels: list[str]
    indexable: bool
