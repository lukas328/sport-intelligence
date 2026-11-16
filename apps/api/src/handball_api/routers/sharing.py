from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, Request, Response
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


class ShareOptions(ApiModel):
    """What may be shared publicly for the team, per kind; a reason instead of a failed attempt."""

    youth: bool
    default_days: int
    kinds: dict[str, str | None] = Field(
        description="per kind: null when allowed, else forbidden, plan, unverified or "
        "youth-protection"
    )


@router.get("/v1/orgs/{org_id}/teams/{team_id}/share-options", response_model=ShareOptions)
async def options(team_id: uuid.UUID, scope: OrgDep) -> dict[str, Any]:
    """The share dialog asks first, so it can explain the youth rule or a missing right (K20)."""
    return await service.options(scope.ctx, team_id)


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


class PreviewGoal(ApiModel):
    team: Literal["own", "opp"]
    zone: str | None
    minute: float | None


class PreviewPlay(ApiModel):
    category: str
    formation: str | None
    doc: dict[str, Any]


class PreviewReel(ApiModel):
    format: str


class SharePreview(ApiModel):
    """What a chat shows for the link (Open Graph): no names of people, nothing behind a login.
    The match fields are set when the shared content belongs to one match."""

    kind: str
    title: str
    club: str
    team: str
    scenes: int
    duration_s: int | None
    kit: dict[str, str]
    expires_at: datetime
    opponent: str | None = None
    opp_kit: str | None = None
    score: list[int] | None = None
    halftime: list[int] | None = None
    kickoff_at: datetime | None = None
    is_home: bool | None = None
    # a shared goal scene: its minute, side and zone
    goal: PreviewGoal | None = None
    # a shared match: its goals by side and zone (the three things of the match card)
    goals: list[PreviewGoal] | None = None
    play: PreviewPlay | None = None
    reel: PreviewReel | None = None


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
async def public_reel(token: str, ctx: CtxDep, request: Request) -> Response:
    """The reel as one MP4. Byte ranges are served: Safari and the iMessage preview (og:video)
    play an MP4 inline only from a server that answers ranges."""
    data = await service.public_reel(ctx, token)
    headers = {"cache-control": "private, max-age=60", "accept-ranges": "bytes"}
    part = byte_range(request.headers.get("range"), len(data))
    if part is None:
        return Response(data, media_type="video/mp4", headers=headers)
    if part == "invalid":
        return Response(
            status_code=416, headers={**headers, "content-range": f"bytes */{len(data)}"}
        )
    start, end = part
    return Response(
        data[start : end + 1],
        status_code=206,
        media_type="video/mp4",
        headers={**headers, "content-range": f"bytes {start}-{end}/{len(data)}"},
    )


def byte_range(header: str | None, size: int) -> tuple[int, int] | Literal["invalid"] | None:
    """One range of a `Range: bytes=a-b` header (a-, -n and a-b); None: the whole file."""
    if not header or not header.startswith("bytes=") or "," in header:
        return None
    first, _, last = header[6:].strip().partition("-")
    try:
        if first == "":
            n = int(last)
            if n <= 0:
                return "invalid"
            return max(0, size - n), size - 1
        start = int(first)
        end = int(last) if last else size - 1
    except ValueError:
        return None
    if start >= size or end < start:
        return "invalid"
    return start, min(end, size - 1)
