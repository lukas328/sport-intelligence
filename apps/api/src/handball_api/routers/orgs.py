from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, File, Query, Response, UploadFile, status

from handball_api.models import Invitation, Organization
from handball_api.routers.deps import AuthedDep, CtxDep, OrgDep, OrgScope
from handball_api.schemas.common import ApiModel
from handball_api.schemas.orgs import (
    InvitationCreate,
    InvitationOut,
    InvitationPreview,
    MemberOut,
    OrgCreate,
    OrgOut,
    OrgRoleIn,
    OrgUpdate,
)
from handball_api.services import invitations as invitation_service
from handball_api.services import orgs as service

router = APIRouter(prefix="/v1", tags=["organizations"])


def org_out(scope: OrgScope, org: Organization | None = None) -> OrgOut:
    org = org or scope.org
    actor = scope.ctx.require_actor()
    return OrgOut(
        id=org.id,
        name=org.name,
        country=org.country,
        primary_color=org.primary_color,
        secondary_color=org.secondary_color,
        has_logo=org.logo_key is not None,
        plan=org.plan,
        data_region=org.data_region,
        my_role=actor.org_role,
        two_factor_required=actor.is_org_admin
        and scope.ctx.settings.org_admin_2fa_required
        and not actor.has_2fa,
        created_at=org.created_at,
    )


@router.post("/orgs", response_model=OrgOut, status_code=status.HTTP_201_CREATED)
async def create_org(data: OrgCreate, auth: AuthedDep) -> OrgOut:
    org = await service.create_org(auth.ctx, auth.user, data)
    await auth.ctx.db.refresh(org)
    actor, org = await service.build_actor(auth.ctx, auth.user, org.id)
    auth.ctx.actor = actor
    return org_out(OrgScope(auth.ctx, auth.user, org, auth.session))


@router.get("/orgs/{org_id}", response_model=OrgOut)
async def get_org(scope: OrgDep) -> OrgOut:
    return org_out(scope)


@router.patch("/orgs/{org_id}", response_model=OrgOut)
async def update_org(data: OrgUpdate, scope: OrgDep) -> OrgOut:
    await service.update_org(scope.ctx, scope.org, data)
    await scope.ctx.db.flush()
    await scope.ctx.db.refresh(scope.org)
    return org_out(scope)


@router.put("/orgs/{org_id}/logo", response_model=OrgOut)
async def upload_logo(scope: OrgDep, file: Annotated[UploadFile, File()]) -> OrgOut:
    data = await file.read(scope.ctx.settings.max_logo_bytes + 1)
    await service.set_logo(scope.ctx, scope.org, data)
    await scope.ctx.db.flush()
    await scope.ctx.db.refresh(scope.org)
    return org_out(scope)


@router.get(
    "/orgs/{org_id}/logo",
    response_class=Response,
    responses={200: {"content": {"image/png": {}, "image/jpeg": {}, "image/webp": {}}}},
)
async def get_logo(scope: OrgDep) -> Response:
    data, ctype = await service.get_logo(scope.ctx, scope.org)
    return Response(data, media_type=ctype, headers={"cache-control": "private, max-age=300"})


@router.get("/orgs/{org_id}/members", response_model=list[MemberOut])
async def list_members(scope: OrgDep) -> list[MemberOut]:
    return [
        MemberOut(
            user_id=u.id,
            name=u.name,
            email=u.email,
            org_role=r,
            team_roles=t,
            totp_enabled=u.totp_enabled,
        )
        for u, r, t in await service.list_org_members(scope.ctx)
    ]


@router.patch("/orgs/{org_id}/members/{user_id}", response_model=OrgRoleIn)
async def set_member_role(user_id: uuid.UUID, data: OrgRoleIn, scope: OrgDep) -> OrgRoleIn:
    """Club admin handover: promote a member to club admin, or step down (another admin stays)."""
    return OrgRoleIn(org_role=await service.set_org_role(scope.ctx, user_id, data.org_role))


@router.post(
    "/orgs/{org_id}/invitations",
    response_model=InvitationOut,
    status_code=status.HTTP_201_CREATED,
    tags=["invitations"],
)
async def create_invitation(data: InvitationCreate, scope: OrgDep) -> Invitation:
    inv, _token = await invitation_service.create(scope.ctx, scope.org, scope.user, data)
    return inv


@router.get("/orgs/{org_id}/invitations", response_model=list[InvitationOut], tags=["invitations"])
async def list_invitations(
    scope: OrgDep, team_id: Annotated[uuid.UUID | None, Query()] = None
) -> list[Invitation]:
    return await invitation_service.list_for_org(scope.ctx, team_id)


@router.delete(
    "/orgs/{org_id}/invitations/{invitation_id}", response_model=InvitationOut, tags=["invitations"]
)
async def revoke_invitation(invitation_id: uuid.UUID, scope: OrgDep) -> Invitation:
    return await invitation_service.revoke(scope.ctx, invitation_id)


@router.get("/invitations/{token}", response_model=InvitationPreview, tags=["invitations"])
async def preview_invitation(token: str, ctx: CtxDep) -> InvitationPreview:
    return await invitation_service.preview(ctx, token)


class AcceptedOut(ApiModel):
    organization_id: uuid.UUID


@router.post("/invitations/{token}/accept", response_model=AcceptedOut, tags=["invitations"])
async def accept_invitation(token: str, auth: AuthedDep) -> AcceptedOut:
    org = await invitation_service.accept(auth.ctx, token, auth.user)
    return AcceptedOut(organization_id=org.id)
