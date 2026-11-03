"""Statistics matrix, exports and Sportscode import (addendum 01, 5.4)."""

from __future__ import annotations

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, File, Query, Response, UploadFile

from handball_api.models import MatrixTemplate
from handball_api.routers.deps import OrgDep
from handball_api.schemas.matrix import MatrixIn, MatrixOut, TemplateIn, TemplateOut
from handball_api.services import matrix as service
from handball_api.services import sportscode

router = APIRouter(prefix="/v1/orgs/{org_id}", tags=["matrix"])
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.post("/teams/{team_id}/matrix", response_model=MatrixOut)
async def matrix(team_id: uuid.UUID, body: MatrixIn, scope: OrgDep) -> MatrixOut:
    """Rows x metrics over the team's matches; every cell lists its events and clips."""
    return await service.matrix(scope.ctx, team_id, body)


@router.post(
    "/teams/{team_id}/matrix/export",
    response_class=Response,
    responses={200: {"content": {"text/csv": {}, XLSX: {}}}},
)
async def matrix_export(
    team_id: uuid.UUID,
    body: MatrixIn,
    scope: OrgDep,
    format: Annotated[Literal["csv", "xlsx"], Query()] = "csv",
) -> Response:
    out = await service.matrix(scope.ctx, team_id, body)
    if format == "xlsx":
        data, media = service.to_xlsx(out), XLSX
    else:
        data, media = service.to_csv(out), "text/csv; charset=utf-8"
    return Response(
        data,
        media_type=media,
        headers={"content-disposition": f'attachment; filename="matrix-{out.by}.{format}"'},
    )


@router.get("/teams/{team_id}/matrix/templates", response_model=list[TemplateOut])
async def templates(team_id: uuid.UUID, scope: OrgDep) -> list[MatrixTemplate]:
    return await service.templates(scope.ctx, team_id)


@router.post("/teams/{team_id}/matrix/templates", response_model=TemplateOut, status_code=201)
async def save_template(team_id: uuid.UUID, body: TemplateIn, scope: OrgDep) -> MatrixTemplate:
    return await service.save_template(scope.ctx, team_id, body)


@router.delete("/matrix/templates/{template_id}", status_code=204)
async def delete_template(template_id: uuid.UUID, scope: OrgDep) -> Response:
    await service.delete_template(scope.ctx, template_id)
    return Response(status_code=204)


@router.get(
    "/matches/{match_id}/export/sportscode",
    response_class=Response,
    responses={200: {"content": {"application/xml": {}}}},
)
async def export_sportscode(match_id: uuid.UUID, scope: OrgDep) -> Response:
    """Sportscode XML timeline: events with video time and clips with their tags."""
    data, name = await sportscode.export_xml(scope.ctx, match_id)
    return Response(
        data,
        media_type="application/xml",
        headers={"content-disposition": f'attachment; filename="{name}"'},
    )


@router.get(
    "/matches/{match_id}/export/events",
    response_class=Response,
    responses={200: {"content": {"text/csv": {}}}},
)
async def export_events(match_id: uuid.UUID, scope: OrgDep) -> Response:
    data, name = await sportscode.events_csv(scope.ctx, match_id)
    return Response(
        data,
        media_type="text/csv; charset=utf-8",
        headers={"content-disposition": f'attachment; filename="{name}"'},
    )


@router.post("/matches/{match_id}/import/sportscode")
async def import_sportscode(
    match_id: uuid.UUID, scope: OrgDep, file: Annotated[UploadFile, File()]
) -> dict[str, int]:
    """Instances become clips with own tags (code and labels); events stay untouched."""
    return await sportscode.import_xml(
        scope.ctx, match_id, await file.read(sportscode.MAX_BYTES + 1)
    )
