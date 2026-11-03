from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from handball_api.core.errors import ProblemError
from handball_api.core.oidc import enabled_providers
from handball_api.models import OAuthIdentity
from handball_api.routers.deps import (
    Authed,
    AuthedDep,
    CtxDep,
    OptionalSession,
    clear_session_cookies,
    rate_limit,
    require_pending_totp,
    set_session_cookies,
)
from handball_api.schemas.auth import (
    LoginIn,
    LoginResult,
    MagicLinkIn,
    MeOut,
    MeUpdate,
    OrgSummary,
    PasswordChangeIn,
    PasswordForgotIn,
    PasswordResetIn,
    ProvidersOut,
    RecoveryCodesOut,
    RegisterIn,
    SessionOut,
    TokenIn,
    TotpCodeIn,
    TotpSetupOut,
)
from handball_api.services import auth as service
from handball_api.services import invitations as invitation_service
from handball_api.services import oauth as oauth_service
from handball_api.services import orgs as org_service
from handball_api.services.auth import IssuedSession
from handball_api.services.context import Ctx

router = APIRouter(prefix="/v1", tags=["auth"])


def _apply(response: Response, ctx: Ctx, issued: IssuedSession) -> LoginResult:
    max_age = int((issued.expires_at - datetime.now(UTC)).total_seconds())
    set_session_cookies(response, ctx.settings, issued.token, issued.csrf, max_age)
    return LoginResult(status="totp_required" if issued.mfa_pending else "ok")


@router.post(
    "/auth/register",
    response_model=LoginResult,
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit("register"))],
)
async def register(
    data: RegisterIn, request: Request, response: Response, ctx: CtxDep
) -> LoginResult:
    user, issued = await service.register(ctx, data, request.headers.get("user-agent"))
    if data.invitation_token:
        await invitation_service.accept(ctx, data.invitation_token, user)
    return _apply(response, ctx, issued)


@router.post(
    "/auth/login",
    response_model=LoginResult,
    response_model_exclude_none=True,
    dependencies=[Depends(rate_limit("login"))],
)
async def login(data: LoginIn, request: Request, response: Response, ctx: CtxDep) -> LoginResult:
    issued = await service.login(ctx, data, request.headers.get("user-agent"))
    if request.headers.get("x-client") == "native":
        # the apps keep the session token in the device keychain and send it as a bearer token;
        # no cookies, so no CSRF surface (a web page cannot set this header cross-site)
        return LoginResult(
            status="totp_required" if issued.mfa_pending else "ok", token=issued.token
        )
    return _apply(response, ctx, issued)


@router.post(
    "/auth/login/totp",
    response_model=LoginResult,
    response_model_exclude_none=True,
    dependencies=[Depends(rate_limit("totp"))],
)
async def login_totp(
    data: TotpCodeIn, auth: Annotated[Authed, Depends(require_pending_totp)]
) -> LoginResult:
    await service.complete_totp(auth.ctx, auth.session, auth.user, data.code)
    return LoginResult(status="ok")


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response, ctx: CtxDep, found: OptionalSession) -> None:
    if found is not None:
        await service.logout(ctx, found[0])
    clear_session_cookies(response, ctx.settings)


@router.post(
    "/auth/magic-link",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(rate_limit("magic"))],
)
async def magic_link(data: MagicLinkIn, ctx: CtxDep) -> None:
    await service.request_magic_link(ctx, data.email)


@router.post(
    "/auth/magic-link/consume",
    response_model=LoginResult,
    response_model_exclude_none=True,
    dependencies=[Depends(rate_limit("magic-consume"))],
)
async def magic_link_consume(
    data: TokenIn, request: Request, response: Response, ctx: CtxDep
) -> LoginResult:
    return _apply(
        response,
        ctx,
        await service.consume_magic_link(ctx, data.token, request.headers.get("user-agent")),
    )


async def _me(auth: Authed) -> MeOut:
    orgs = await org_service.list_my_orgs(auth.ctx, auth.user)
    u = auth.user
    providers = await auth.ctx.db.scalars(
        select(OAuthIdentity.provider).where(OAuthIdentity.user_id == u.id)
    )
    return MeOut(
        id=u.id,
        email=u.email,
        name=u.name,
        locale=u.locale,
        totp_enabled=u.totp_enabled,
        has_password=u.password_hash is not None,
        recovery_codes_left=len(u.recovery_codes or []),
        email_verified=u.email_verified_at is not None,
        linked_providers=sorted(str(p) for p in providers.all()),
        is_platform_admin=u.is_platform_admin,
        organizations=[OrgSummary(id=o.id, name=o.name, role=r) for o, r in orgs],
    )


@router.get("/me", response_model=MeOut, tags=["me"])
async def me(auth: AuthedDep) -> MeOut:
    return await _me(auth)


@router.patch("/me", response_model=MeOut, tags=["me"])
async def update_me(data: MeUpdate, auth: AuthedDep) -> MeOut:
    await service.update_me(auth.ctx, auth.user, data)
    return await _me(auth)


@router.post("/me/totp/setup", response_model=TotpSetupOut, tags=["me"])
async def totp_setup(auth: AuthedDep) -> TotpSetupOut:
    secret, uri = await service.totp_setup(auth.ctx, auth.user)
    return TotpSetupOut(secret=secret, otpauth_uri=uri)


@router.post("/me/totp/enable", response_model=RecoveryCodesOut, tags=["me"])
async def totp_enable(data: TotpCodeIn, auth: AuthedDep) -> RecoveryCodesOut:
    """Turn two-factor sign-in on; returns ten one-time recovery codes (shown only now)."""
    codes = await service.totp_enable(auth.ctx, auth.user, auth.session, data.code)
    return RecoveryCodesOut(recovery_codes=codes)


@router.post("/me/totp/recovery-codes", response_model=RecoveryCodesOut, tags=["me"])
async def recovery_codes(data: TotpCodeIn, auth: AuthedDep) -> RecoveryCodesOut:
    """New recovery codes (the old ones stop working)."""
    return RecoveryCodesOut(
        recovery_codes=await service.regenerate_recovery_codes(auth.ctx, auth.user, data.code)
    )


@router.post("/me/totp/disable", status_code=status.HTTP_204_NO_CONTENT, tags=["me"])
async def totp_disable(data: TotpCodeIn, auth: AuthedDep) -> None:
    await service.totp_disable(auth.ctx, auth.user, data.code)


# ---- password reset, e-mail verification, password change, sessions -----------------------


@router.post(
    "/auth/password/forgot",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(rate_limit("forgot"))],
)
async def password_forgot(data: PasswordForgotIn, ctx: CtxDep) -> None:
    await service.request_password_reset(ctx, data.email)


@router.post(
    "/auth/password/reset",
    response_model=LoginResult,
    response_model_exclude_none=True,
    dependencies=[Depends(rate_limit("reset"))],
)
async def password_reset(
    data: PasswordResetIn, request: Request, response: Response, ctx: CtxDep
) -> LoginResult:
    issued = await service.reset_password(
        ctx, data.token, data.password, request.headers.get("user-agent")
    )
    return _apply(response, ctx, issued)


@router.post(
    "/auth/email/verify",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(rate_limit("verify"))],
)
async def email_verify(data: TokenIn, ctx: CtxDep) -> None:
    await service.verify_email(ctx, data.token)


@router.post(
    "/me/email/verify",
    status_code=status.HTTP_202_ACCEPTED,
    tags=["me"],
    dependencies=[Depends(rate_limit("verify-resend"))],
)
async def email_verify_resend(auth: AuthedDep) -> None:
    await service.send_email_verification(auth.ctx, auth.user)


@router.post(
    "/me/password",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["me"],
    dependencies=[Depends(rate_limit("password-change"))],
)
async def password_change(data: PasswordChangeIn, auth: AuthedDep) -> None:
    await service.change_password(
        auth.ctx, auth.user, auth.session, data.current_password, data.new_password
    )


@router.get("/me/sessions", response_model=list[SessionOut], tags=["me"])
async def sessions(auth: AuthedDep) -> list[SessionOut]:
    return [
        SessionOut(
            id=s.id,
            created_at=s.created_at,
            last_seen_at=s.last_seen_at,
            user_agent=s.user_agent,
            ip=str(s.ip) if s.ip else None,
            method=s.method,
            current=s.id == auth.session.id,
        )
        for s in await service.list_sessions(auth.ctx, auth.user)
    ]


@router.delete("/me/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["me"])
async def revoke_session(session_id: uuid.UUID, auth: AuthedDep) -> None:
    await service.revoke_session(auth.ctx, auth.user, session_id)


@router.post("/me/sessions/revoke-others", status_code=status.HTTP_204_NO_CONTENT, tags=["me"])
async def revoke_other_sessions(auth: AuthedDep) -> None:
    await service.revoke_other_sessions(auth.ctx, auth.user, auth.session)


# ---- Google / Apple (ADR 010) --------------------------------------------------------------

OAUTH_COOKIE = "hb_oauth"


@router.get("/auth/providers", response_model=ProvidersOut)
async def providers(ctx: CtxDep) -> ProvidersOut:
    return ProvidersOut(providers=sorted(enabled_providers(ctx.settings)))


def _safe_next(value: str | None) -> str:
    if not value or not value.startswith("/") or value.startswith("//") or value.startswith("/\\"):
        return "/app"
    return value


@router.get(
    "/auth/oauth/{provider}/start",
    status_code=status.HTTP_302_FOUND,
    response_class=RedirectResponse,
    dependencies=[Depends(rate_limit("oauth"))],
)
async def oauth_start(
    provider: str,
    ctx: CtxDep,
    next: str | None = Query(default=None),
    invite: str | None = Query(default=None, max_length=200),
) -> RedirectResponse:
    url, cookie = oauth_service.start(ctx, provider, _safe_next(next), invite)
    resp = RedirectResponse(url, status_code=status.HTTP_302_FOUND)
    # Apple posts the callback cross-site: the state cookie must be SameSite=None (needs Secure).
    cross_site = provider == "apple" and ctx.settings.cookie_secure
    resp.set_cookie(
        OAUTH_COOKIE,
        cookie,
        max_age=oauth_service.STATE_TTL_S,
        httponly=True,
        secure=ctx.settings.cookie_secure,
        samesite="none" if cross_site else "lax",
        path="/v1/auth/oauth",
    )
    return resp


async def _oauth_callback(provider: str, request: Request, ctx: CtxDep) -> RedirectResponse:
    params: dict[str, str] = dict(request.query_params)
    apple_name: str | None = None
    if request.method == "POST":
        form = await request.form()
        params.update({k: str(v) for k, v in form.items() if isinstance(v, str)})
        apple_name = _apple_name(params.get("user"))
    base = ctx.settings.web_base_url
    try:
        if params.get("error"):
            raise ProblemError(400, "oauth-cancelled", "Sign-in was cancelled")
        result = await oauth_service.callback(
            ctx,
            request.app.state.oidc,
            provider,
            params.get("code"),
            params.get("state"),
            request.cookies.get(OAUTH_COOKIE),
            request.headers.get("user-agent"),
            apple_name,
        )
    except ProblemError as exc:
        resp = RedirectResponse(f"{base}/login?error={quote(exc.code)}", status_code=303)
        resp.delete_cookie(OAUTH_COOKIE, path="/v1/auth/oauth")
        return resp
    if result.session.mfa_pending:
        target = f"{base}/login?totp=1&next={quote(result.next_path)}"
    elif result.created and result.next_path == "/app":
        target = f"{base}/onboarding"
    else:
        target = f"{base}{result.next_path}"
    resp = RedirectResponse(target, status_code=303)
    max_age = int((result.session.expires_at - datetime.now(UTC)).total_seconds())
    set_session_cookies(resp, ctx.settings, result.session.token, result.session.csrf, max_age)
    resp.delete_cookie(OAUTH_COOKIE, path="/v1/auth/oauth")
    return resp


def _apple_name(raw: str | None) -> str | None:
    """Apple sends the user's name only on the first sign-in, as JSON in the form field `user`."""
    if not raw:
        return None
    try:
        name = json.loads(raw).get("name", {})
    except (ValueError, AttributeError):
        return None
    full = " ".join(p for p in (name.get("firstName"), name.get("lastName")) if p)
    return full or None


router.add_api_route(
    "/auth/oauth/{provider}/callback",
    _oauth_callback,
    methods=["GET", "POST"],
    response_class=RedirectResponse,
    status_code=303,
    include_in_schema=False,
)
