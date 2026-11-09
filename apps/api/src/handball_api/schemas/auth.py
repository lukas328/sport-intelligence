from __future__ import annotations

import uuid
from datetime import datetime
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
    # six-digit TOTP code or a recovery code (xxxx-xxxx)
    code: str = Field(min_length=6, max_length=12)


class RecoveryCodesOut(ApiModel):
    recovery_codes: list[str]


class MagicLinkIn(ApiModel):
    email: EmailStr


class TokenIn(ApiModel):
    token: str = Field(min_length=10, max_length=200)


class LoginResult(ApiModel):
    status: Literal["ok", "totp_required"]
    # only for the native apps (header x-client: native), which send it as a bearer token
    token: str | None = None


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
    recovery_codes_left: int = 0
    has_password: bool
    email_verified: bool
    linked_providers: list[str]
    is_platform_admin: bool
    organizations: list[OrgSummary]


class MeUpdate(ApiModel):
    name: Name | None = None
    locale: Locale | None = None


class ProvidersOut(ApiModel):
    providers: list[str]


class PasswordForgotIn(ApiModel):
    email: EmailStr


class PasswordResetIn(ApiModel):
    token: str = Field(min_length=10, max_length=200)
    password: str = Field(min_length=1, max_length=200)


class PasswordChangeIn(ApiModel):
    current_password: str | None = Field(default=None, max_length=200)
    new_password: str = Field(min_length=1, max_length=200)


class SessionOut(ApiModel):
    id: uuid.UUID
    created_at: datetime
    last_seen_at: datetime | None
    user_agent: str | None
    ip: str | None
    method: str
    current: bool
