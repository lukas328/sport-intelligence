"""Drill library: the static drills (packages/tactics) and the club's own drills in one shape."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from handball_api.schemas.common import ApiModel

Level = Literal["basic", "advanced"]
Tag = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]


class DrillIn(ApiModel):
    """An own drill; `shared` makes it visible to every team of the club."""

    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    setup: str | None = Field(default=None, max_length=2000, description="Set-up, description")
    coaching: str | None = Field(default=None, max_length=2000, description="Coaching points")
    minutes: int = Field(ge=1, le=180)
    players: str | None = Field(
        default=None, pattern=r"^\d{1,2}(-\d{1,2})?$", description='Number of players, "6-12"'
    )
    level: Level | None = None
    focus: list[Tag] = Field(
        default_factory=list, max_length=10, description="Category and tags, e.g. wings"
    )
    shared: bool = False


class DrillOut(ApiModel):
    """A drill of the library (`source` "library", texts in the asked language) or of the club
    (`source` "club", texts as written). `id` is the library key or the club drill's UUID; it
    goes into a session's `drill_id` and an assignment's `target_id`."""

    id: str
    source: Literal["library", "club"]
    own: bool = Field(description="A drill of the club (not the static library)")
    name: str
    setup: str | None
    coaching: str | None
    minutes: int
    players: str | None
    level: Level | None
    focus: list[str]
    team_id: uuid.UUID | None = Field(description="The team that made it (club drills)")
    team_name: str | None
    shared: bool = Field(description="Seen by every team of the club (library: always)")
    editable: bool = Field(description="The caller may edit and delete it")
    updated_at: datetime | None
