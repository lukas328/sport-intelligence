"""Photographed paper match reports (addendum 01, 5.9)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, File, Request, Response, UploadFile

from handball_api.models import PaperReportUpload
from handball_api.routers.deps import OrgDep
from handball_api.schemas.paper_vision import PaperConfirm, PaperCorrection, PaperUploadOut
from handball_api.services import paper_vision as service

router = APIRouter(prefix="/v1/orgs/{org_id}", tags=["paper"])


@router.post("/teams/{team_id}/paper-photos", response_model=PaperUploadOut, status_code=201)
async def upload(
    team_id: uuid.UUID, scope: OrgDep, request: Request, file: Annotated[UploadFile, File()]
) -> PaperReportUpload:
    """Reads a photo of a match report sheet; the result waits for review."""
    data = await file.read(service.MAX_PHOTO + 1)
    return await service.upload(
        scope.ctx, request.app.state.paper, team_id, data, file.content_type or ""
    )


@router.get("/teams/{team_id}/paper-photos", response_model=list[PaperUploadOut])
async def listing(team_id: uuid.UUID, scope: OrgDep) -> list[PaperReportUpload]:
    return await service.listing(scope.ctx, team_id)


@router.get("/paper-photos/{upload_id}", response_model=PaperUploadOut)
async def get(upload_id: uuid.UUID, scope: OrgDep) -> PaperReportUpload:
    return await service.get(scope.ctx, upload_id)


@router.get(
    "/paper-photos/{upload_id}/photo",
    response_class=Response,
    responses={200: {"content": {"image/jpeg": {}}}},
)
async def photo(upload_id: uuid.UUID, scope: OrgDep) -> Response:
    data, media = await service.photo(scope.ctx, upload_id)
    return Response(data, media_type=media, headers={"cache-control": "private, max-age=600"})


@router.put("/paper-photos/{upload_id}", response_model=PaperUploadOut)
async def correct(upload_id: uuid.UUID, body: PaperCorrection, scope: OrgDep) -> PaperReportUpload:
    return await service.correct(scope.ctx, upload_id, body.extraction)


@router.post("/paper-photos/{upload_id}/confirm", response_model=PaperUploadOut)
async def confirm(upload_id: uuid.UUID, body: PaperConfirm, scope: OrgDep) -> PaperReportUpload:
    """Imports the reviewed sheet as a match with source "paper_report"."""
    return await service.confirm(scope.ctx, upload_id, body.accept_warnings)
