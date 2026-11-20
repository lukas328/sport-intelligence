"""Access requests: a second person finds a claimed club and asks its admins."""

from __future__ import annotations

import uuid

from sqlalchemy import select

from handball_api.core.db import disable_system_access, enable_system_access
from handball_api.core.errors import ProblemError
from handball_api.integrations import handball_ch as ch
from handball_api.models import (
    Membership,
    OrgAccessRequest,
    Organization,
    OrgMembership,
    User,
)
from handball_api.models.enums import (
    OrgRole,
)
from handball_api.schemas.official import AccessApproveIn
from handball_api.services import (
    audit,
    training,
)
from handball_api.services.context import Ctx
from handball_api.services.official._base import _now
from handball_api.services.official.claim import _create_team, _official_team
from handball_api.services.official.sync import sync_team
from handball_api.services.policies import Action, authorize

# ---- access requests (a second person finds a claimed club) ------------------------------------


async def list_access_requests(ctx: Ctx) -> list[tuple[OrgAccessRequest, User]]:
    authorize(ctx.require_actor(), Action.ORG_ACCESS_MANAGE, two_factor=ctx.two_factor)
    rows = await ctx.db.execute(
        select(OrgAccessRequest, User)
        .join(User, User.id == OrgAccessRequest.user_id)
        .where(OrgAccessRequest.status == "pending")
        .order_by(OrgAccessRequest.created_at)
    )
    return [(r, u) for r, u in rows]


async def _access_request(ctx: Ctx, request_id: uuid.UUID) -> OrgAccessRequest:
    actor = ctx.require_actor()
    authorize(actor, Action.ORG_ACCESS_MANAGE, two_factor=ctx.two_factor)
    # locked until the decision is saved: a second click waits and then finds it decided (409,
    # not a 500 from a duplicate membership)
    req = await ctx.db.scalar(
        select(OrgAccessRequest)
        .where(OrgAccessRequest.id == request_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if req is None or req.organization_id != actor.organization_id:
        raise ProblemError(404, "not-found", "Request not found")
    if req.status != "pending":
        raise ProblemError(409, "request-decided", "This request was already decided")
    return req


async def approve_access(
    ctx: Ctx, org: Organization, request_id: uuid.UUID, data: AccessApproveIn
) -> OrgAccessRequest:
    req = await _access_request(ctx, request_id)
    om = await ctx.db.scalar(
        select(OrgMembership).where(
            OrgMembership.organization_id == org.id, OrgMembership.user_id == req.user_id
        )
    )
    if om is None:
        ctx.db.add(OrgMembership(organization_id=org.id, user_id=req.user_id, role=data.org_role))
    elif data.org_role == OrgRole.ORG_ADMIN:
        om.role = OrgRole.ORG_ADMIN
    team_id = req.team_id
    if team_id is None and req.official_team_id is not None:
        # the team is not in the app yet: created from the official data, the person coaches it
        _, _, oteam = await _official_team(ctx, org.official_club_id or 0, req.official_team_id)
        season = await ch.current_season(ctx.db)
        team = await _create_team(ctx, org, season, oteam, req.user_id, role=data.team_role)
        await sync_team(ctx, team, initial=True)
        team_id = team.id
    elif team_id is not None:
        m = await ctx.db.scalar(
            select(Membership).where(
                Membership.team_id == team_id, Membership.user_id == req.user_id
            )
        )
        if m is None:
            ctx.db.add(
                Membership(
                    organization_id=org.id,
                    team_id=team_id,
                    user_id=req.user_id,
                    role=data.team_role,
                )
            )
    req.team_id = team_id
    req.status, req.decided_by_id, req.decided_at = "approved", ctx.user_id, _now()
    await training.notify(
        ctx,
        org.id,
        [req.user_id],
        "access_approved",
        {"organization_id": str(org.id)},
        f"/app/{org.id}",
    )
    await audit.record(
        ctx,
        "org.access_approved",
        target_type="org_access_request",
        target_id=req.id,
        data={"user_id": str(req.user_id), "org_role": data.org_role, "team_role": data.team_role},
    )
    await ctx.db.flush()
    return req


async def decline_access(ctx: Ctx, request_id: uuid.UUID) -> OrgAccessRequest:
    req = await _access_request(ctx, request_id)
    req.status, req.decided_by_id, req.decided_at = "declined", ctx.user_id, _now()
    await audit.record(
        ctx, "org.access_declined", target_type="org_access_request", target_id=req.id
    )
    return req


async def my_access_requests(ctx: Ctx, user: User) -> list[tuple[OrgAccessRequest, str]]:
    await enable_system_access(ctx.db, reason="own access requests")
    try:
        rows = await ctx.db.execute(
            select(OrgAccessRequest, Organization.name)
            .join(Organization, Organization.id == OrgAccessRequest.organization_id)
            .where(OrgAccessRequest.user_id == user.id)
            .order_by(OrgAccessRequest.created_at.desc())
        )
        return [(r, n) for r, n in rows]
    finally:
        await disable_system_access(ctx.db)
