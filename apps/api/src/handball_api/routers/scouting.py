"""Automatic preparation report (addendum 01, 4.6)."""

from __future__ import annotations

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Query, Response

from handball_api.models import ScoutingReport
from handball_api.routers.deps import OrgDep
from handball_api.schemas.scouting import ScoutingOut
from handball_api.services import scouting as service

router = APIRouter(prefix="/v1/orgs/{org_id}", tags=["scouting"])
Lang = Annotated[Literal["de-CH", "en", "fr"], Query()]


@router.post("/matches/{match_id}/scouting", response_model=ScoutingOut, status_code=201)
async def generate(match_id: uuid.UUID, scope: OrgDep) -> ScoutingReport:
    """Creates the report now (it is created automatically 72 h before kickoff)."""
    return await service.generate(scope.ctx, match_id)


@router.get("/matches/{match_id}/scouting", response_model=ScoutingOut)
async def latest(match_id: uuid.UUID, scope: OrgDep) -> ScoutingReport:
    return await service.latest(scope.ctx, match_id)


@router.get(
    "/scouting/{report_id}/pdf",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}}}},
)
async def report_pdf(report_id: uuid.UUID, scope: OrgDep, lang: Lang = "de-CH") -> Response:
    data, name = await service.pdf(scope.ctx, report_id, lang, card=False)
    return Response(
        data,
        media_type="application/pdf",
        headers={"content-disposition": f'inline; filename="{name}"'},
    )


@router.get(
    "/scouting/{report_id}/goalkeeper-card",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}}}},
)
async def goalkeeper_card(report_id: uuid.UUID, scope: OrgDep, lang: Lang = "de-CH") -> Response:
    """A6 shooter card for goalkeepers (number, position, preferred goal zones)."""
    data, name = await service.pdf(scope.ctx, report_id, lang, card=True)
    return Response(
        data,
        media_type="application/pdf",
        headers={"content-disposition": f'inline; filename="{name}"'},
    )
