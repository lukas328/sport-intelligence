from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Annotated

from pydantic import EmailStr, Field, StringConstraints, model_validator

from handball_api.models.enums import (
    DataRegion,
    MatchFormatKey,
    OrgRole,
    Plan,
    TeamGender,
    TeamRole,
)
from handball_api.schemas.common import ApiModel, HexColor, Name

Country = Annotated[str, StringConstraints(pattern=r"^[A-Z]{2}$")]
InviteeName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]


class OrgCreate(ApiModel):
    name: Name
    country: Country = "CH"
    primary_color: HexColor = "#0b6bcb"
    secondary_color: HexColor = "#ffffff"


class OrgUpdate(ApiModel):
    name: Name | None = None
    country: Country | None = None
    primary_color: HexColor | None = None
    secondary_color: HexColor | None = None


class OrgOut(ApiModel):
    id: uuid.UUID
    name: str
    country: str
    primary_color: str
    secondary_color: str
    has_logo: bool
    plan: Plan
    data_region: DataRegion
    my_role: OrgRole
    two_factor_required: bool
    created_at: datetime
    # official club link (federation onboarding): none | unverified | verified
    verification: str = "none"
    official_club_id: int | None = None


class SeasonCreate(ApiModel):
    label: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]
    starts_on: date
    ends_on: date

    @model_validator(mode="after")
    def _order(self) -> SeasonCreate:
        if self.ends_on <= self.starts_on:
            raise ValueError("ends_on must be after starts_on")
        return self


class SeasonOut(ApiModel):
    id: uuid.UUID
    team_id: uuid.UUID
    label: str
    starts_on: date
    ends_on: date


class TeamSettings(ApiModel):
    players_see_team_stats: bool
    # "Teamfunktionen" (ADR 029): training, dates, RSVP, tasks and the player and parent areas.
    # Off by default, also for teams created before the setting existed.
    team_features: bool = False


class TeamSettingsUpdate(ApiModel):
    players_see_team_stats: bool | None = None
    team_features: bool | None = None


class TeamCreate(ApiModel):
    name: Name
    league: Name | None = None
    is_youth: bool = False
    gender: TeamGender
    join_as_coach: bool = True


class TeamUpdate(ApiModel):
    name: Name | None = None
    league: Name | None = None
    is_youth: bool | None = None
    gender: TeamGender | None = None
    settings: TeamSettingsUpdate | None = None
    level: Name | None = None
    default_format: MatchFormatKey | None = None


class TeamOut(ApiModel):
    id: uuid.UUID
    name: str
    league: str | None
    is_youth: bool
    gender: TeamGender
    settings: TeamSettings
    level: str | None = None
    default_format: str | None = None
    my_role: TeamRole | None
    current_season: SeasonOut | None
    # registered team in the official data (handball.ch team id of the season)
    official_team_id: int | None = None


class MemberOut(ApiModel):
    user_id: uuid.UUID
    name: str
    email: str
    org_role: OrgRole
    team_roles: dict[uuid.UUID, TeamRole]
    totp_enabled: bool


class TeamMemberOut(ApiModel):
    user_id: uuid.UUID
    name: str
    email: str
    role: TeamRole


class TeamMemberUpdate(ApiModel):
    role: TeamRole


class InvitationCreate(ApiModel):
    email: EmailStr
    org_role: OrgRole = OrgRole.MEMBER
    team_id: uuid.UUID | None = None
    team_role: TeamRole | None = None
    # the roster entry the invitee is (player roles) or the child (parent): the accepting
    # account is linked to it if it is still free (409 if it has another account)
    player_id: uuid.UUID | None = None
    # without player_id: name and/or shirt number of the invitee; when they match exactly one
    # roster entry of the team's current season that has no account yet, the invitation is
    # made for that entry (player and goalkeeper invitations only)
    first_name: InviteeName | None = None
    last_name: InviteeName | None = None
    jersey_number: int | None = Field(default=None, ge=1, le=99)

    @model_validator(mode="after")
    def _team_pair(self) -> InvitationCreate:
        if (self.team_id is None) != (self.team_role is None):
            raise ValueError("team_id and team_role go together")
        if self.org_role == OrgRole.MEMBER and self.team_id is None:
            raise ValueError("a member invitation needs a team")
        hints = (self.first_name, self.last_name, self.jersey_number)
        if self.team_id is None and any(h is not None for h in hints):
            raise ValueError("name and shirt number need a team invitation")
        return self


class InvitationOut(ApiModel):
    id: uuid.UUID
    email: str
    org_role: OrgRole
    team_id: uuid.UUID | None
    team_role: TeamRole | None
    player_id: uuid.UUID | None
    expires_at: datetime
    accepted_at: datetime | None
    revoked_at: datetime | None


class InvitationPreview(ApiModel):
    organization_name: str
    team_name: str | None
    email: str
    org_role: OrgRole
    team_role: TeamRole | None
    status: str = Field(description="pending, accepted, revoked or expired")
    account_exists: bool


class OrgRoleIn(ApiModel):
    org_role: OrgRole
