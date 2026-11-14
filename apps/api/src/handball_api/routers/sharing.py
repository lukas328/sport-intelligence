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
    kind: Literal["play", "match", "playlist", "highlight", "scene", "collection"]
    target_id: uuid.UUID
    # a shared link is valid 30 days by default (SPEC 7.8), revocable at any time
    days: int = Field(default=30, ge=1, le=90)


class ShareOut(ApiModel):
    id: uuid.UUID
    kind: str
    target_id: uuid.UUID
    title: str
    expires_at: datetime
    revoked_at: datetime | None
    views: int
    created_at: datetime
    # the token for the team's staff, to copy the same link again (None for older links)
    token: str | None = None


class ShareCreated(ShareOut):
    token: str


@router.post(
    "/v1/orgs/{org_id}/teams/{team_id}/share-links", response_model=ShareCreated, status_code=201
)
async def create(team_id: uuid.UUID, data: ShareCreate, scope: OrgDep) -> ShareCreated:
    """Read-only link; the token stays copyable for the team's staff (list)."""
    link, token = await service.create(scope.ctx, team_id, data.kind, data.target_id, data.days)
    return ShareCreated.model_validate(
        {**ShareOut.model_validate(link, from_attributes=True).model_dump(), "token": token}
    )


@router.get("/v1/orgs/{org_id}/teams/{team_id}/share-links", response_model=list[ShareOut])
async def list_links(team_id: uuid.UUID, scope: OrgDep) -> list[Any]:
    links = await service.list_links(scope.ctx, team_id)
    return [
        {
            **ShareOut.model_validate(x, from_attributes=True).model_dump(),
            "token": service.token_of(scope.ctx, x),
        }
        for x in links
    ]


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


class SharePreview(ApiModel):
    """What a chat shows for the link (Open Graph): no names of people, nothing behind a login."""

    kind: str
    title: str
    club: str
    team: str
    scenes: int
    duration_s: int | None
    kit: dict[str, str]
    expires_at: datetime


@router.get(
    "/v1/share/{token}/preview",
    response_model=SharePreview,
    dependencies=[Depends(rate_limit("share"))],
)
async def preview(token: str, ctx: CtxDep) -> dict[str, Any]:
    """Data for the link preview (title, club, length); does not count as an opening."""
    return await service.preview(ctx, token)


@router.get(
    "/v1/share/{token}/videos/{video_id}/media/{path:path}",
    response_class=Response,
    responses={200: {"content": {"application/vnd.apple.mpegurl": {}, "video/mp4": {}}}},
)
async def public_media(token: str, video_id: uuid.UUID, path: str, ctx: CtxDep) -> Response:
    data, ctype = await service.public_media(ctx, token, video_id, path)
    cache = "private, no-cache" if path.endswith((".m3u8", ".vtt")) else "private, max-age=60"
    return Response(data, media_type=ctype, headers={"cache-control": cache})


@router.get(
    "/v1/share/{token}/reel.mp4",
    response_class=Response,
    responses={200: {"content": {"video/mp4": {}}}},
)
async def public_reel(token: str, ctx: CtxDep) -> Response:
    data = await service.public_reel(ctx, token)
    return Response(data, media_type="video/mp4", headers={"cache-control": "private, max-age=60"})
