"""Several files per match, match boundaries in tournament videos (addendum 01, 4.8)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter

from handball_api.routers.deps import OrgDep
from handball_api.schemas.common import ApiModel
from handball_api.services import segments as service

router = APIRouter(prefix="/v1/orgs/{org_id}", tags=["matches"])


class PartOut(ApiModel):
    video_id: uuid.UUID
    filename: str
    position: int
    # where the part starts on the match timeline (None while a part before has no length)
    start_ms: int | None = None
    duration_s: float | None
    recorded_at: datetime | None
    gap_before_ms: int | None
    source: str
    confirmed: bool


class PartOrder(ApiModel):
    video_ids: list[uuid.UUID]


class BoundaryOut(ApiModel):
    video_id: uuid.UUID
    t_ms: int
    pause_ms: int | None
    confidence: float | None


@router.get("/matches/{match_id}/parts", response_model=list[PartOut])
async def parts(match_id: uuid.UUID, scope: OrgDep) -> list[dict[str, Any]]:
    """Main-camera files in order (camera clock), with the gap before each file."""
    return await service.parts(scope.ctx, match_id)


@router.put("/matches/{match_id}/parts", response_model=list[PartOut])
async def reorder(match_id: uuid.UUID, data: PartOrder, scope: OrgDep) -> list[dict[str, Any]]:
    return await service.reorder(scope.ctx, match_id, data.video_ids)


@router.get("/matches/{match_id}/boundaries", response_model=list[BoundaryOut])
async def boundaries(match_id: uuid.UUID, scope: OrgDep) -> list[dict[str, Any]]:
    """Suggested match boundaries (long pause, then a throw-off): split the video there."""
    return await service.boundaries(scope.ctx, match_id)
