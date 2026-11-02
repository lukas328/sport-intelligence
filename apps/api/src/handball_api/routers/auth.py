from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status

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
    RegisterIn,
    TokenIn,
    TotpCodeIn,
    TotpSetupOut,
)
from handball_api.services import auth as service
from handball_api.services import invitations as invitation_service
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


@router.post("/auth/login", response_model=LoginResult, dependencies=[Depends(rate_limit("login"))])
async def login(data: LoginIn, request: Request, response: Response, ctx: CtxDep) -> LoginResult:
    return _apply(response, ctx, await service.login(ctx, data, request.headers.get("user-agent")))


@router.post(
    "/auth/login/totp", response_model=LoginResult, dependencies=[Depends(rate_limit("totp"))]
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
    return MeOut(
        id=u.id,
        email=u.email,
        name=u.name,
        locale=u.locale,
        totp_enabled=u.totp_enabled,
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


@router.post("/me/totp/enable", status_code=status.HTTP_204_NO_CONTENT, tags=["me"])
async def totp_enable(data: TotpCodeIn, auth: AuthedDep) -> None:
    await service.totp_enable(auth.ctx, auth.user, auth.session, data.code)


@router.post("/me/totp/disable", status_code=status.HTTP_204_NO_CONTENT, tags=["me"])
async def totp_disable(data: TotpCodeIn, auth: AuthedDep) -> None:
    await service.totp_disable(auth.ctx, auth.user, data.code)
