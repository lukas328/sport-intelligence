"""Photographed paper match reports (addendum 01, 5.9)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import Field

from handball_api.schemas.common import ApiModel


class PaperIssue(ApiModel):
    field: str
    code: str
    detail: dict[str, Any] = Field(default_factory=dict)


class PaperUploadOut(ApiModel):
    id: uuid.UUID
    team_id: uuid.UUID
    status: str
    extraction: dict[str, Any] | None
    errors: list[PaperIssue]
    match_id: uuid.UUID | None
    created_at: datetime


class PaperCorrection(ApiModel):
    extraction: dict[str, Any]


class PaperConfirm(ApiModel):
    accept_warnings: bool = False
