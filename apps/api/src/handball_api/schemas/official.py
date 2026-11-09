"""Official league data: team search, claim, suggestions, join and access requests,
verification (docs/plans/federation-onboarding.md)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import Field, StringConstraints

from handball_api.models.enums import OrgRole, TeamRole
from handball_api.schemas.common import ApiModel

Provider = Literal["handball_ch"]
PersonName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
Message = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)]


class OfficialClubOut(ApiModel):
    id: int
    name: str
    city: str | None


class OfficialTeamHit(ApiModel):
    provider: Provider = "handball_ch"
    official_id: int
    name: str
    league: str | None
    league_short: str | None
    group_name: str | None
    season_id: int
    club: OfficialClubOut
    # the club that registered the team (differs for joint teams)
    registered_club_id: int
    # available: nobody claimed the team; claimed: a club in the app has it (claiming asks its
    # admins for access, players can ask to join); member: you are in that club
    status: Literal["available", "claimed", "member"]
    # set when the team is in the app: players send their join request to this team
    team_id: uuid.UUID | None = None
    organization_id: uuid.UUID | None = None


class ClaimIn(ApiModel):
    club_id: int = Field(description="Official club id of the search hit (club.id)")
    org_id: uuid.UUID | None = Field(
        default=None, description="Link this existing club of yours instead of creating one"
    )
    team_name: PersonName | None = None
    message: Message | None = Field(default=None, description="For an access request")


class PrefillOut(ApiModel):
    matches_created: int = 0
    # games over the plan's matches per season: match_new suggestions with reason plan_limit
    matches_held_back: int = 0
    results: int = 0
    roster_suggestions: int = 0
    report_suggestions: int = 0
    other_suggestions: int = 0


class ClaimOut(ApiModel):
    # claimed: club and team created or linked and prefilled; access_requested: the club or team
    # belongs to a club in the app, its admins decide; already_member: nothing to do
    status: Literal["claimed", "access_requested", "already_member"]
    organization_id: uuid.UUID | None = None
    team_id: uuid.UUID | None = None
    created_organization: bool = False
    access_request_id: uuid.UUID | None = None
    verification: str | None = None
    prefill: PrefillOut | None = None


class OfficialLinkOut(ApiModel):
    linked: bool
    provider: str | None = None
    official_team_id: int | None = None
    official_club_id: int | None = None
    official_group_id: int | None = None
    official_season_id: int | None = None
    league: str | None = None
    group_name: str | None = None
    synced_at: datetime | None = None
    standing: list[dict[str, Any]] = Field(default_factory=list)
    open_suggestions: int = 0
    # organisers' choice: show the official statistics in roster suggestions (display only)
    roster_stats: bool = False


class OfficialPreferencesIn(ApiModel):
    roster_stats: bool


SuggestionKind = Literal[
    "roster_add", "roster_number", "roster_left", "match_new", "match_moved", "report", "season_new"
]


class SuggestionOut(ApiModel):
    id: uuid.UUID
    kind: SuggestionKind
    status: Literal["open", "accepted", "dismissed"]
    payload: dict[str, Any]
    created_at: datetime
    resolved_at: datetime | None
    # open match_new: accepting it would exceed the plan's matches per season (402 until upgrade)
    blocked: Literal["plan_limit"] | None = None


class SuggestionAcceptIn(ApiModel):
    # roster_add: a different shirt number than the official one (null = none)
    jersey_number: int | None = Field(default=None, ge=1, le=99)


class SuggestionResultOut(ApiModel):
    suggestion: SuggestionOut
    player_id: uuid.UUID | None = None
    match_id: uuid.UUID | None = None
    season_id: uuid.UUID | None = None
    report: dict[str, Any] | None = None


class SyncOut(ApiModel):
    matches_created: int = 0
    matches_held_back: int = 0
    results: int = 0
    roster_suggestions: int = 0
    report_suggestions: int = 0
    other_suggestions: int = 0
    synced_at: datetime | None = None


class JoinRequestIn(ApiModel):
    first_name: PersonName
    last_name: PersonName
    jersey_number: int | None = Field(default=None, ge=1, le=99)
    role: Literal["player", "goalkeeper"] = "player"
    message: Message | None = None


class MatchCandidate(ApiModel):
    kind: Literal["player", "suggestion"]
    id: uuid.UUID
    first_name: str
    last_name: str
    jersey_number: int | None


class JoinRequestOut(ApiModel):
    id: uuid.UUID
    team_id: uuid.UUID
    user_id: uuid.UUID
    email: str
    first_name: str
    last_name: str
    jersey_number: int | None
    role: str
    message: str | None
    status: str
    created_at: datetime
    suggested: MatchCandidate | None = None
    player_id: uuid.UUID | None = None


class MyJoinRequestOut(ApiModel):
    id: uuid.UUID
    team_id: uuid.UUID
    team_name: str
    organization_id: uuid.UUID
    organization_name: str
    status: str
    created_at: datetime


class JoinApproveIn(ApiModel):
    # omit both to take the suggested match; player_id or suggestion_id to choose another;
    # new_entry true to add the person as a new roster entry
    player_id: uuid.UUID | None = None
    suggestion_id: uuid.UUID | None = None
    new_entry: bool = False


class AccessRequestOut(ApiModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    email: str
    team_id: uuid.UUID | None
    official_team_id: int | None
    message: str | None
    status: str
    created_at: datetime


class MyAccessRequestOut(ApiModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    organization_name: str
    status: str
    created_at: datetime


class AccessApproveIn(ApiModel):
    org_role: OrgRole = OrgRole.MEMBER
    # role in the requested team (the team is created from the official data if needed)
    team_role: TeamRole = TeamRole.COACH


class VerificationOut(ApiModel):
    verification: Literal["none", "unverified", "verified"]
    verified_via: str | None
    verified_at: datetime | None
    official_provider: str | None
    official_club_id: int | None
    club_domains: list[str]
    methods: list[str]


class OperatorVerifyIn(ApiModel):
    verified: bool
