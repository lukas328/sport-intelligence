from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import Field

from handball_api.schemas.common import ApiModel


class AttachmentCreate(ApiModel):
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(
        max_length=100, description="image/jpeg, image/png, image/webp, image/heic or PDF"
    )
    size_bytes: int = Field(gt=0, description="at most 25 MB")
    note: str | None = Field(default=None, max_length=2000)


class AttachmentUpdate(ApiModel):
    note: str | None = Field(default=None, max_length=2000, description="null or empty clears it")


class AttachmentComplete(ApiModel):
    etag: str = Field(min_length=1, max_length=100, description="ETag storage answered the PUT")


class AttachmentOut(ApiModel):
    id: uuid.UUID
    match_id: uuid.UUID
    filename: str
    content_type: str
    size_bytes: int
    note: str | None
    status: Literal["uploading", "ready"]
    is_image: bool
    created_at: datetime
    created_by: str | None = Field(default=None, description="the name of who added it")


class AttachmentUploadOut(ApiModel):
    attachment: AttachmentOut
    upload_url: str = Field(description="PUT the file here (presigned, one part), then complete")
