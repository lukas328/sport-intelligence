from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query

from handball_api.models import Play
from handball_api.routers.deps import OrgDep
from handball_api.schemas.tactics import PlayCreate, PlayOut, PlayUpdate
from handball_api.services import tactics as service

router = APIRouter(prefix="/v1/orgs/{org_id}", tags=["tactics"])


@router.get("/teams/{team_id}/plays", response_model=list[PlayOut])
async def list_plays(
    team_id: uuid.UUID,
    scope: OrgDep,
    category: Annotated[str | None, Query(max_length=20)] = None,
    q: Annotated[str | None, Query(max_length=60)] = None,
) -> list[Play]:
    """Play library; players see plays shared with them."""
    return await service.list_plays(scope.ctx, team_id, category, q)


@router.post("/teams/{team_id}/plays", response_model=PlayOut, status_code=201)
async def create_play(team_id: uuid.UUID, data: PlayCreate, scope: OrgDep) -> Play:
    return await service.create_play(scope.ctx, team_id, data)


@router.get("/plays/{play_id}", response_model=PlayOut)
async def get_play(play_id: uuid.UUID, scope: OrgDep) -> Play:
    return await service.get_play(scope.ctx, play_id)


@router.patch("/plays/{play_id}", response_model=PlayOut)
async def update_play(play_id: uuid.UUID, data: PlayUpdate, scope: OrgDep) -> Play:
    return await service.update_play(scope.ctx, play_id, data)


@router.delete("/plays/{play_id}", status_code=204)
async def delete_play(play_id: uuid.UUID, scope: OrgDep) -> None:
    await service.delete_play(scope.ctx, play_id)
