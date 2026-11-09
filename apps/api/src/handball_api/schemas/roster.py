from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import Field, field_validator

from handball_api.models.enums import (
    ConsentGivenBy,
    ConsentKind,
    Hand,
    PlayerAvailability,
    Position,
)
from handball_api.schemas.common import ApiModel, ShortName


class PlayerFields(ApiModel):
    first_name: ShortName
    last_name: ShortName
    birth_year: int | None = Field(default=None, ge=1940, le=2030)
    shooting_hand: Hand | None = None
    main_position: Position | None = None
    secondary_positions: list[Position] = Field(default_factory=list, max_length=6)


class RosterEntryCreate(PlayerFields):
    jersey_number: int | None = Field(default=None, ge=1, le=99)


class RosterEntryUpdate(ApiModel):
    first_name: ShortName | None = None
    last_name: ShortName | None = None
    birth_year: int | None = Field(default=None, ge=1940, le=2030)
    shooting_hand: Hand | None = None
    main_position: Position | None = None
    secondary_positions: list[Position] | None = None
    jersey_number: int | None = Field(default=None, ge=1, le=99)
    active: bool | None = None


class PlayerStatusIn(ApiModel):
    """Injured or absent; fit is no status (DELETE). The note is short, never a diagnosis."""

    kind: PlayerAvailability
    until: date | None = None
    note: str | None = Field(default=None, max_length=140)


class PlayerStatusOut(ApiModel):
    player_id: uuid.UUID
    team_id: uuid.UUID
    kind: PlayerAvailability
    # inclusive; from the next day the player reads as fit again
    until: date | None
    note: str | None
    updated_at: datetime


class RosterEntryOut(ApiModel):
    id: uuid.UUID
    player_id: uuid.UUID
    season_id: uuid.UUID
    jersey_number: int | None
    active: bool
    first_name: str
    last_name: str
    birth_year: int | None
    shooting_hand: Hand | None
    main_position: Position | None
    secondary_positions: list[Position]
    has_account: bool
    consent_complete: bool
    # injured or absent (None: fit); staff see every player's, players only their own
    status: PlayerStatusOut | None = None


class ImportRowError(ApiModel):
    row: int
    field: str | None
    message: str


class ImportResult(ApiModel):
    dry_run: bool
    rows: list[RosterEntryCreate]
    errors: list[ImportRowError]
    created: int


class ConsentCreate(ApiModel):
    kind: ConsentKind
    given_by: ConsentGivenBy
    given_by_name: ShortName
    given_at: datetime
    document_ref: str | None = Field(default=None, max_length=300)

    @field_validator("given_at")
    @classmethod
    def _tz(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("given_at needs a timezone")
        return v


class ConsentOut(ApiModel):
    id: uuid.UUID
    player_id: uuid.UUID
    kind: ConsentKind
    given_by: ConsentGivenBy
    given_by_name: str
    given_at: datetime
    document_ref: str | None
    revoked_at: datetime | None


ConsentState = Literal["granted", "refused", "missing"]


class PurposeState(ApiModel):
    """A player's consent for one purpose: `granted` (an unrevoked consent, `since` = its
    given_at), `refused` (the latest consent was revoked, `since` = revoked_at) or `missing`
    (never given). `given_by` and `given_by_name` are those of that consent: the player
    (`self`), a parent or a guardian; who revoked it is in the audit log."""

    kind: ConsentKind
    state: ConsentState
    since: datetime | None
    given_by: ConsentGivenBy | None
    given_by_name: str | None
    consent_id: uuid.UUID | None
    # false for the public purposes in youth teams (4.9): they cannot be given there
    applicable: bool


class ConsentOverviewPlayer(ApiModel):
    player_id: uuid.UUID
    roster_entry_id: uuid.UUID
    jersey_number: int | None
    first_name: str
    last_name: str
    has_account: bool
    # None when the birth year is unknown; minors consent through a parent or guardian
    minor: bool | None
    purposes: list[PurposeState]


class PurposeSummary(ApiModel):
    """One purpose over the listed players: "12 von 14" is `granted` of `players`."""

    kind: ConsentKind
    applicable: bool
    players: int
    granted: int
    refused: int
    missing: int


class ConsentOverview(ApiModel):
    team_id: uuid.UUID
    season_id: uuid.UUID
    is_youth: bool
    players: list[ConsentOverviewPlayer]
    summary: list[PurposeSummary]
