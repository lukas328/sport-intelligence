"""Federation and volume licences (addendum 01, 5.10)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import EmailStr, Field

from handball_api.schemas.common import ApiModel


class FederationIn(ApiModel):
    name: str = Field(min_length=2, max_length=160)
    plan: Literal["team", "club"] = "team"
    seat_quota: int = Field(ge=1, le=10000)
    contract_ref: str | None = Field(default=None, max_length=120)
    contract_until: date | None = None
    billing_address: dict[str, str] = Field(default_factory=dict)


class FederationOut(ApiModel):
    id: uuid.UUID
    name: str
    plan: str
    seat_quota: int
    contract_ref: str | None
    contract_until: date | None


class AdminIn(ApiModel):
    email: EmailStr


class InviteIn(ApiModel):
    email: EmailStr


class InviteOut(ApiModel):
    email: str
    expires_at: datetime


class JoinIn(ApiModel):
    token: str = Field(min_length=10, max_length=200)


class MemberUsage(ApiModel):
    organization_id: uuid.UUID
    name: str
    joined_at: datetime
    teams: int
    matches: int
    members: int
    analyses_30d: int


class Overview(ApiModel):
    federation: dict[str, Any]
    seats_used: int
    open_invites: int
    members: list[MemberUsage]
    aggregate: dict[str, Any]


class ClubFederation(ApiModel):
    federation: str
    plan: str
    joined_at: datetime
    contract_until: date | None
