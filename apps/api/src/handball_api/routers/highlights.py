"""Automatic highlights (addendum 01, 4.3)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Response

from handball_api.models import HighlightReel
from handball_api.routers.deps import OrgDep
from handball_api.schemas.highlights import HighlightIn, HighlightOut
from handball_api.services import highlights as service

router = APIRouter(prefix="/v1/orgs/{org_id}", tags=["highlights"])


@router.get("/matches/{match_id}/highlights", response_model=list[HighlightOut])
async def list_reels(match_id: uuid.UUID, scope: OrgDep) -> list[HighlightReel]:
    """Team reels and player reels the caller may see (created after every analysis)."""
    return await service.list_for_match(scope.ctx, match_id)


@router.post("/matches/{match_id}/highlights", response_model=HighlightOut, status_code=202)
async def create(match_id: uuid.UUID, data: HighlightIn, scope: OrgDep) -> HighlightReel:
    return await service.create(scope.ctx, match_id, data.format, data.player_id)


@router.get(
    "/highlights/{reel_id}/video.mp4",
    response_class=Response,
    responses={200: {"content": {"video/mp4": {}}}},
)
async def video(reel_id: uuid.UUID, scope: OrgDep) -> Response:
    return Response(
        await service.video(scope.ctx, reel_id),
        media_type="video/mp4",
        headers={"cache-control": "private, max-age=3600"},
    )
