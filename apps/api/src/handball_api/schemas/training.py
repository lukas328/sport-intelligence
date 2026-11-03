from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from handball_api.schemas.common import ApiModel

AssignmentKind = Literal["playlist", "play", "match", "drill"]


class AssignmentCreate(ApiModel):
    kind: AssignmentKind
    target_id: str = Field(min_length=2, max_length=60, pattern=r"^[A-Za-z0-9_-]+$")
    title: str = Field(min_length=1, max_length=200)
    note: str | None = Field(default=None, max_length=2000)
    due_at: datetime | None = None
    # empty: every player and goalkeeper of the team
    user_ids: list[uuid.UUID] = Field(default_factory=list, max_length=60)
    notify_email: bool = True


class AssignmentOut(ApiModel):
    id: uuid.UUID
    team_id: uuid.UUID
    kind: str
    target_id: str
    title: str
    note: str | None
    due_at: datetime | None
    created_at: datetime
    recipients: int
    done: int
    # only in "my assignments"
    seen_at: datetime | None = None
    done_at: datetime | None = None
    team_name: str | None = None
    progress: list[dict[str, Any]] | None = None


class AssignmentStatusIn(ApiModel):
    done: bool


class NotificationOut(ApiModel):
    id: uuid.UUID
    kind: str
    params: dict[str, Any]
    link: str | None
    read_at: datetime | None
    created_at: datetime


class NotificationList(ApiModel):
    unread: int
    items: list[NotificationOut]


class NotificationsRead(ApiModel):
    ids: list[uuid.UUID] = Field(default_factory=list, max_length=200)  # empty: all
