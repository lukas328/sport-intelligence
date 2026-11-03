"""Public player profile (addendum 01, 5.8)."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Response

from handball_api.routers.deps import CtxDep, OrgDep
from handball_api.schemas.profiles import MyProfile, ProfileIn, ProfileOut, PublicProfileOut
from handball_api.services import profiles as service

router = APIRouter(prefix="/v1/orgs/{org_id}", tags=["profiles"])
public = APIRouter(prefix="/v1/public/profiles", tags=["profiles"])


@router.get("/me/profiles", response_model=list[MyProfile])
async def mine(scope: OrgDep) -> list[dict[str, Any]]:
    """Profiles I manage: my own and my children's, with the reels that can go on them."""
    return await service.mine(scope.ctx)


@router.put("/players/{player_id}/profile", response_model=ProfileOut)
async def save(player_id: uuid.UUID, body: ProfileIn, scope: OrgDep) -> dict[str, Any]:
    return await service.save(scope.ctx, player_id, body)


@router.delete("/players/{player_id}/profile", status_code=204)
async def remove(player_id: uuid.UUID, scope: OrgDep) -> Response:
    await service.remove(scope.ctx, player_id)
    return Response(status_code=204)


@public.get("/{slug}", response_model=PublicProfileOut)
async def show(slug: str, ctx: CtxDep, response: Response) -> dict[str, Any]:
    data = await service.public(ctx, slug)
    if not data["indexable"]:
        response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return data


@public.get(
    "/{slug}/reels/{reel_id}",
    response_class=Response,
    responses={200: {"content": {"video/mp4": {}}}},
)
async def reel(slug: str, reel_id: uuid.UUID, ctx: CtxDep) -> Response:
    data = await service.public_reel(ctx, slug, reel_id)
    return Response(
        data,
        media_type="video/mp4",
        headers={"X-Robots-Tag": "noindex", "cache-control": "private, max-age=300"},
    )
