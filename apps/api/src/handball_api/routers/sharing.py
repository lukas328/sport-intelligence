from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, Response
from pydantic import Field

from handball_api.routers.deps import CtxDep, OrgDep, rate_limit
from handball_api.schemas.common import ApiModel
from handball_api.services import sharing as service

router = APIRouter(tags=["sharing"])


class ShareCreate(ApiModel):
    kind: Literal["play", "match", "playlist"]
    target_id: uuid.UUID
    days: int = Field(default=14, ge=1, le=90)


class ShareOut(ApiModel):
    id: uuid.UUID
    kind: str
    target_id: uuid.UUID
    title: str
    expires_at: datetime
    revoked_at: datetime | None
    views: int
    created_at: datetime


class ShareCreated(ShareOut):
    token: str


@router.post(
    "/v1/orgs/{org_id}/teams/{team_id}/share-links", response_model=ShareCreated, status_code=201
)
async def create(team_id: uuid.UUID, data: ShareCreate, scope: OrgDep) -> ShareCreated:
    """Read-only link; the token is shown once."""
    link, token = await service.create(scope.ctx, team_id, data.kind, data.target_id, data.days)
    return ShareCreated.model_validate(
        {**ShareOut.model_validate(link, from_attributes=True).model_dump(), "token": token}
    )


@router.get("/v1/orgs/{org_id}/teams/{team_id}/share-links", response_model=list[ShareOut])
async def list_links(team_id: uuid.UUID, scope: OrgDep) -> list[Any]:
    return await service.list_links(scope.ctx, team_id)


@router.delete("/v1/orgs/{org_id}/share-links/{link_id}", status_code=204)
async def revoke(link_id: uuid.UUID, scope: OrgDep) -> None:
    await service.revoke(scope.ctx, link_id)


@router.get(
    "/v1/share/{token}",
    response_model=dict[str, Any],
    dependencies=[Depends(rate_limit("share"))],
)
async def public(token: str, ctx: CtxDep) -> dict[str, Any]:
    """Public, read-only content of a share link (no sign-in)."""
    return await service.public(ctx, token)


@router.get(
    "/v1/share/{token}/videos/{video_id}/media/{path:path}",
    response_class=Response,
    responses={200: {"content": {"application/vnd.apple.mpegurl": {}, "video/mp4": {}}}},
)
async def public_media(token: str, video_id: uuid.UUID, path: str, ctx: CtxDep) -> Response:
    data, ctype = await service.public_media(ctx, token, video_id, path)
    return Response(data, media_type=ctype, headers={"cache-control": "private, max-age=60"})
