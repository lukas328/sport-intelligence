from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from handball_api.models.enums import ReelFormat
from handball_api.schemas.common import ApiModel


class HighlightIn(ApiModel):
    format: ReelFormat = ReelFormat.LANDSCAPE
    player_id: uuid.UUID | None = None


class HighlightOut(ApiModel):
    id: uuid.UUID
    match_id: uuid.UUID | None
    player_id: uuid.UUID | None
    format: str
    status: str
    clip_ids: list[str]
    consent: dict[str, Any]
    created_at: datetime
