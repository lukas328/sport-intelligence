from __future__ import annotations

import uuid
from typing import Literal

from pydantic import EmailStr, Field

from handball_api.schemas.common import ApiModel, Name

Locale = Literal["de-CH", "en", "fr"]


class RegisterIn(ApiModel):
    email: EmailStr
    name: Name
    password: str = Field(min_length=1, max_length=200)
    locale: Locale = "de-CH"
    accept_terms: bool
    invitation_token: str | None = None


class LoginIn(ApiModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class TotpCodeIn(ApiModel):
    code: str = Field(min_length=6, max_length=8)


class MagicLinkIn(ApiModel):
    email: EmailStr


class TokenIn(ApiModel):
    token: str = Field(min_length=10, max_length=200)


class LoginResult(ApiModel):
    status: Literal["ok", "totp_required"]


class TotpSetupOut(ApiModel):
    secret: str
    otpauth_uri: str


class OrgSummary(ApiModel):
    id: uuid.UUID
    name: str
    role: str


class MeOut(ApiModel):
    id: uuid.UUID
    email: str
    name: str
    locale: str
    totp_enabled: bool
    is_platform_admin: bool
    organizations: list[OrgSummary]


class MeUpdate(ApiModel):
    name: Name | None = None
    locale: Locale | None = None
