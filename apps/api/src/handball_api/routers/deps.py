from __future__ import annotations

import re
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Annotated
from urllib.parse import urlsplit

from fastapi import Depends, Path, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from handball_api.core.config import Settings, get_settings
from handball_api.core.db import get_session, set_current_user
from handball_api.core.errors import ProblemError
from handball_api.core.ratelimit import RateLimiter, parse_rate
from handball_api.core.security import constant_time_equals, csrf_for_session
from handball_api.models import AuthSession, Organization, User
from handball_api.services import auth as auth_service
from handball_api.services import orgs as org_service
from handball_api.services.context import Ctx

SettingsDep = Annotated[Settings, Depends(get_settings)]
DbDep = Annotated[AsyncSession, Depends(get_session)]
UNSAFE = {"POST", "PUT", "PATCH", "DELETE"}
OAUTH_CALLBACK = re.compile(r"^/v1/auth/oauth/[a-z]+/callback$")


def client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


async def csrf_protect(request: Request, settings: SettingsDep) -> None:
    """Applied to every route. Origin check for all unsafe requests, plus a signed double-submit
    token whenever a session cookie is present (ADR 008)."""
    if request.method not in UNSAFE:
        return
    if OAUTH_CALLBACK.match(request.url.path):
        return  # Apple posts the callback cross-site; the signed state cookie protects it
    if request.url.path.startswith("/internal/"):
        return  # worker callbacks: shared-secret header, never reachable via the web origin
    origin = request.headers.get("origin")
    if origin:
        allowed = {_origin(o) for o in [*settings.cors_origins, settings.web_base_url]}
        if _origin(origin) not in allowed:
            raise ProblemError(403, "origin-not-allowed", "Cross-origin request rejected")
    token = request.cookies.get(settings.session_cookie)
    if token is None:
        return
    sent = request.headers.get("x-csrf-token", "")
    expected = csrf_for_session(settings.secret_key.get_secret_value(), token)
    if not sent or not constant_time_equals(sent, expected):
        raise ProblemError(403, "csrf-failed", "Missing or invalid CSRF token")


def _origin(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}".lower()


def get_ctx(request: Request, db: DbDep, settings: SettingsDep) -> Ctx:
    return Ctx(
        db=db,
        settings=settings,
        email=request.app.state.email,
        storage=request.app.state.storage,
        jobs=request.app.state.jobs,
        events=request.app.state.events,
        text=request.app.state.text,
        ip=client_ip(request),
    )


CtxDep = Annotated[Ctx, Depends(get_ctx)]


async def optional_session(request: Request, ctx: CtxDep) -> tuple[AuthSession, User] | None:
    token = request.cookies.get(ctx.settings.session_cookie)
    if not token:
        return None
    return await auth_service.resolve_session(ctx, token)


OptionalSession = Annotated[tuple[AuthSession, User] | None, Depends(optional_session)]


@dataclass
class Authed:
    ctx: Ctx
    session: AuthSession
    user: User


async def require_user(ctx: CtxDep, found: OptionalSession) -> Authed:
    if found is None:
        raise ProblemError(401, "unauthenticated", "Please sign in")
    session, user = found
    if session.mfa_pending:
        raise ProblemError(401, "totp-required", "Second factor required")
    ctx.user_id = user.id
    await set_current_user(ctx.db, user.id)
    return Authed(ctx, session, user)


AuthedDep = Annotated[Authed, Depends(require_user)]


async def require_pending_totp(ctx: CtxDep, found: OptionalSession) -> Authed:
    if found is None:
        raise ProblemError(401, "unauthenticated", "Please sign in")
    session, user = found
    return Authed(ctx, session, user)


@dataclass
class OrgScope:
    ctx: Ctx
    user: User
    org: Organization
    session: AuthSession


async def org_scope(auth: AuthedDep, org_id: Annotated[uuid.UUID, Path()]) -> OrgScope:
    actor, org = await org_service.build_actor(auth.ctx, auth.user, org_id)
    auth.ctx.actor = actor
    return OrgScope(auth.ctx, auth.user, org, auth.session)


OrgDep = Annotated[OrgScope, Depends(org_scope)]


def rate_limit(scope: str) -> Callable[[Request, Settings], Awaitable[None]]:
    async def _dep(request: Request, settings: SettingsDep) -> None:
        limiter: RateLimiter = request.app.state.rate_limiter
        limit, window = parse_rate(settings.rate_limit_auth)
        if not await limiter.hit(f"{scope}:{client_ip(request)}", limit, window):
            raise ProblemError(429, "rate-limited", "Too many attempts, try again later")

    return _dep


def set_session_cookies(
    response: Response, settings: Settings, token: str, csrf: str, max_age: int
) -> None:
    common = {"secure": settings.cookie_secure, "samesite": "lax", "path": "/", "max_age": max_age}
    response.set_cookie(settings.session_cookie, token, httponly=True, **common)  # type: ignore[arg-type]
    response.set_cookie(settings.csrf_cookie, csrf, httponly=False, **common)  # type: ignore[arg-type]


def clear_session_cookies(response: Response, settings: Settings) -> None:
    response.delete_cookie(settings.session_cookie, path="/")
    response.delete_cookie(settings.csrf_cookie, path="/")
