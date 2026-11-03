from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from handball_api.schemas.common import ApiModel


class ScoutingOut(ApiModel):
    id: uuid.UUID
    match_id: uuid.UUID | None
    opponent_id: uuid.UUID
    generated_at: datetime
    facts: dict[str, Any]
    basis: dict[str, Any]
