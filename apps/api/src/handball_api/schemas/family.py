from __future__ import annotations

import uuid

from handball_api.models.enums import ConsentKind
from handball_api.schemas.common import ApiModel
from handball_api.schemas.roster import ConsentOut


class SubjectTeam(ApiModel):
    id: uuid.UUID
    name: str
    is_youth: bool


class ConsentSubject(ApiModel):
    player_id: uuid.UUID
    first_name: str
    last_name: str
    birth_year: int | None
    relation: str
    minor: bool | None
    teams: list[SubjectTeam]
    active: list[ConsentKind]
    history: list[ConsentOut]


class ConsentToggle(ApiModel):
    kind: ConsentKind
