"""Drill library: static drills and the club's own drills (M7)."""

from __future__ import annotations

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Path, Query, Response

from handball_api.routers.deps import OrgDep
from handball_api.schemas.drills import DrillIn, DrillOut
from handball_api.services import drills as service

router = APIRouter(prefix="/v1/orgs/{org_id}", tags=["training"])
Lang = Annotated[Literal["de-CH", "en", "fr"], Query()]


@router.get("/teams/{team_id}/drills", response_model=list[DrillOut])
async def list_drills(team_id: uuid.UUID, scope: OrgDep, lang: Lang = "de-CH") -> list[DrillOut]:
    """One list: the team's own drills and those shared in the club (`source` "club", by name),
    then the static library (`source` "library", texts in `lang`)."""
    return await service.list_drills(scope.ctx, team_id, lang)


@router.post("/teams/{team_id}/drills", response_model=DrillOut, status_code=201)
async def create_drill(team_id: uuid.UUID, data: DrillIn, scope: OrgDep) -> DrillOut:
    """An own drill of the team; `shared` shows it to every team of the club."""
    return await service.create_drill(scope.ctx, team_id, data)


@router.get("/drills/{drill_id}", response_model=DrillOut)
async def get_drill(
    drill_id: Annotated[str, Path(max_length=80)], scope: OrgDep, lang: Lang = "de-CH"
) -> DrillOut:
    """A library drill by its key or a club drill by its id."""
    return await service.get_drill(scope.ctx, drill_id, lang)


@router.put("/drills/{drill_id}", response_model=DrillOut)
async def update_drill(drill_id: uuid.UUID, data: DrillIn, scope: OrgDep) -> DrillOut:
    """Only the staff of the team that made it (sessions keep their snapshot)."""
    return await service.update_drill(scope.ctx, drill_id, data)


@router.delete("/drills/{drill_id}", status_code=204)
async def delete_drill(drill_id: uuid.UUID, scope: OrgDep) -> Response:
    await service.delete_drill(scope.ctx, drill_id)
    return Response(status_code=204)
