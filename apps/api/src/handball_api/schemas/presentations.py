from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from handball_api.models.enums import SlideType
from handball_api.schemas.common import ApiModel


class PresentationIn(ApiModel):
    title: str = Field(min_length=1, max_length=160)
    match_id: uuid.UUID | None = None


class PresentationPatch(ApiModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    shared_with_players: bool | None = None


class SlideIn(ApiModel):
    """Content per type (addendum 01, 4.1):

    - clip: video_id, in_ms, out_ms, holds [{t_ms, duration_ms, shapes}], slow [{from_ms, to_ms,
      rate}], spotlight [track ids], notes
    - tactics_board: play_id (field), notes
    - text: title, body, notes
    - stat_card: title, rows [{label, value, n}], notes
    - image: caption, notes (image uploaded separately)
    """

    type: SlideType
    clip_id: uuid.UUID | None = None
    play_id: uuid.UUID | None = None
    content: dict[str, Any] = Field(default_factory=dict)


class SlidePatch(ApiModel):
    content: dict[str, Any] | None = None
    play_id: uuid.UUID | None = None


class SlideOut(ApiModel):
    id: uuid.UUID
    position: int
    type: str
    clip_id: uuid.UUID | None
    play_id: uuid.UUID | None
    content: dict[str, Any]


class PresentationOut(ApiModel):
    id: uuid.UUID
    team_id: uuid.UUID
    match_id: uuid.UUID | None
    title: str
    shared_with_players: bool
    slides: int
    export_status: str | None
    created_at: datetime


class PresentationDetail(PresentationOut):
    slide_list: list[SlideOut]
    can_edit: bool


class SlideOrder(ApiModel):
    slide_ids: list[uuid.UUID]


class RemotePairing(ApiModel):
    key: str = Field(description="pairing key, part of the QR code link")
    expires_in_s: int


class RemoteCommand(ApiModel):
    key: str = Field(min_length=16, max_length=64)
    action: Literal["next", "prev", "goto", "play", "pause", "draw", "clear"]
    slide: int | None = Field(default=None, ge=0, le=500)
    shapes: list[dict[str, Any]] | None = Field(default=None, max_length=50)
