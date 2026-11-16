"""Files kept with a match (K19): list, upload (presigned), note, open, delete."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, Response

from handball_api.routers.deps import OrgDep
from handball_api.schemas.attachments import (
    AttachmentComplete,
    AttachmentCreate,
    AttachmentOut,
    AttachmentUpdate,
    AttachmentUploadOut,
)
from handball_api.services import attachments as service

router = APIRouter(prefix="/v1/orgs/{org_id}", tags=["attachments"])


@router.get("/matches/{match_id}/attachments", response_model=list[AttachmentOut])
async def list_attachments(match_id: uuid.UUID, scope: OrgDep) -> list[AttachmentOut]:
    return await service.list_for_match(scope.ctx, match_id)


@router.post("/matches/{match_id}/attachments", response_model=AttachmentUploadOut, status_code=201)
async def create_attachment(
    match_id: uuid.UUID, data: AttachmentCreate, scope: OrgDep
) -> AttachmentUploadOut:
    """Starts the upload: PUT the file to `upload_url`, then complete with the ETag."""
    out, url = await service.create(scope.ctx, match_id, data)
    return AttachmentUploadOut(attachment=out, upload_url=url)


@router.post("/attachments/{attachment_id}/complete", response_model=AttachmentOut)
async def complete_attachment(
    attachment_id: uuid.UUID, data: AttachmentComplete, scope: OrgDep
) -> AttachmentOut:
    return await service.complete(scope.ctx, attachment_id, data.etag)


@router.patch("/attachments/{attachment_id}", response_model=AttachmentOut)
async def update_attachment(
    attachment_id: uuid.UUID, data: AttachmentUpdate, scope: OrgDep
) -> AttachmentOut:
    return await service.update(scope.ctx, attachment_id, data)


@router.delete("/attachments/{attachment_id}", status_code=204)
async def delete_attachment(attachment_id: uuid.UUID, scope: OrgDep) -> None:
    await service.delete(scope.ctx, attachment_id)


@router.get(
    "/attachments/{attachment_id}/file",
    response_class=Response,
    responses={200: {"content": {"image/*": {}, "application/pdf": {}}}},
)
async def attachment_file(
    attachment_id: uuid.UUID,
    scope: OrgDep,
    download: Annotated[bool, Query(description="as a download, also for photos")] = False,
) -> Response:
    data, a = await service.read(scope.ctx, attachment_id)
    return Response(content=data, media_type=a.content_type, headers=service.headers(a, download))
