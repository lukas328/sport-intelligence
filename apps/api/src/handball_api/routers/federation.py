"""Federation and volume licences (addendum 01, 5.10)."""

from __future__ import annotations

import uuid
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Query, Response

from handball_api.models import Federation
from handball_api.routers.deps import AuthedDep, OrgDep
from handball_api.routers.ops import OperatorDep
from handball_api.schemas.federation import (
    AdminIn,
    ClubFederation,
    FederationIn,
    FederationOut,
    InviteIn,
    InviteOut,
    JoinIn,
    Overview,
)
from handball_api.services import federation as service

ops = APIRouter(prefix="/v1/ops/federations", tags=["ops"])
admin = APIRouter(prefix="/v1/federations", tags=["federation"])
club = APIRouter(prefix="/v1/orgs/{org_id}/federation", tags=["federation"])


@ops.post("", response_model=FederationOut, status_code=201)
async def create(body: FederationIn, op: OperatorDep) -> Federation:
    return await service.create(op.ctx, body)


@ops.get("", response_model=list[FederationOut])
async def listing(op: OperatorDep) -> list[Federation]:
    return await service.all_federations(op.ctx)


@ops.post("/{federation_id}/admins", status_code=204)
async def add_admin(federation_id: uuid.UUID, body: AdminIn, op: OperatorDep) -> Response:
    await service.add_admin(op.ctx, federation_id, str(body.email))
    return Response(status_code=204)


@ops.get(
    "/{federation_id}/invoice",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}}}},
)
async def invoice(
    federation_id: uuid.UUID,
    op: OperatorDep,
    lang: Annotated[Literal["de-CH", "fr", "en"], Query()] = "de-CH",
) -> Response:
    """Joint QR invoice for all member clubs."""
    data, name = await service.invoice(op.ctx, federation_id, lang)
    return Response(
        data,
        media_type="application/pdf",
        headers={"content-disposition": f'inline; filename="{name}"'},
    )


@admin.get("", response_model=list[FederationOut])
async def mine(auth: AuthedDep) -> list[Federation]:
    return await service.mine(auth.ctx)


@admin.get("/{federation_id}", response_model=Overview)
async def overview(federation_id: uuid.UUID, auth: AuthedDep) -> dict[str, Any]:
    """Usage per club and anonymised aggregates; no videos or people."""
    return await service.overview(auth.ctx, federation_id)


@admin.post("/{federation_id}/invites", response_model=InviteOut, status_code=201)
async def invite(federation_id: uuid.UUID, body: InviteIn, auth: AuthedDep) -> dict[str, Any]:
    return await service.invite(auth.ctx, federation_id, str(body.email))


@admin.delete("/{federation_id}/members/{org_id}", status_code=204)
async def remove(federation_id: uuid.UUID, org_id: uuid.UUID, auth: AuthedDep) -> Response:
    await service.remove_member(auth.ctx, federation_id, org_id)
    return Response(status_code=204)


@club.get("", response_model=ClubFederation | None)
async def status(org_id: uuid.UUID, scope: OrgDep) -> dict[str, Any] | None:
    return await service.status(scope.ctx, org_id)


@club.post("/join")
async def join(org_id: uuid.UUID, body: JoinIn, scope: OrgDep) -> dict[str, Any]:
    """A club admin accepts the federation's invitation for this club."""
    return await service.accept(scope.ctx, org_id, body.token)


@club.delete("", status_code=204)
async def leave(org_id: uuid.UUID, scope: OrgDep) -> Response:
    await service.leave(scope.ctx, org_id)
    return Response(status_code=204)
