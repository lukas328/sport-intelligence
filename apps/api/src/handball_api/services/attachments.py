"""Files kept with a match (K19): a photo or PDF of the paper match report, notes.

A plain place to find them again with the match, nothing is read out of them. The file goes from
the browser straight to storage like a video (one presigned part of a multipart upload, the video
bucket whose browser access is set up); on completion the API checks size and the first bytes, so
only photos and PDFs are kept. Shown inline (photos) or downloaded (PDFs), never as a page of the
app origin. Staff add and delete; everybody who sees the match can open them.
"""

from __future__ import annotations

import re
import uuid
from typing import Any

from sqlalchemy import func, select

from handball_api.core.errors import ProblemError
from handball_api.core.storage import ObjectNotFoundError
from handball_api.models import MatchAttachment, User
from handball_api.schemas.attachments import AttachmentCreate, AttachmentOut, AttachmentUpdate
from handball_api.services import audit, billing
from handball_api.services.context import Ctx
from handball_api.services.matches import get_match
from handball_api.services.policies import Action

MAX_BYTES = 25 * 1024**2
MAX_PER_MATCH = 40
TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/heic": "heic",
    "image/heif": "heif",
    "application/pdf": "pdf",
}
HEIF_BRANDS = (b"heic", b"heix", b"hevc", b"hevx", b"mif1", b"msf1", b"heim", b"heis")
SAFE_NAME = re.compile(r"[^\w.\- ()]+", re.UNICODE)


def sniff(head: bytes) -> str | None:
    """The type the first bytes say (photos and PDFs only), None for anything else."""
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    if head.startswith(b"%PDF-"):
        return "application/pdf"
    if head[4:8] == b"ftyp" and head[8:12] in HEIF_BRANDS:
        return "image/heic"
    return None


def clean_name(name: str) -> str:
    base = SAFE_NAME.sub("_", name.replace("/", "_").replace("\\", "_")).strip(" ._") or "datei"
    return base[:200]


def _out(a: MatchAttachment, by: str | None) -> AttachmentOut:
    return AttachmentOut(
        id=a.id,
        match_id=a.match_id,
        filename=a.filename,
        content_type=a.content_type,
        size_bytes=a.size_bytes,
        note=a.note,
        status=a.status,
        is_image=a.content_type.startswith("image/"),
        created_at=a.created_at,
        created_by=by,
    )


async def _get(ctx: Ctx, attachment_id: uuid.UUID, action: Action) -> MatchAttachment:
    a = await ctx.db.get(MatchAttachment, attachment_id)
    if a is None:
        raise ProblemError(404, "not-found", "File not found")
    await get_match(ctx, a.match_id, action)
    return a


async def _author(ctx: Ctx, a: MatchAttachment) -> str | None:
    if a.created_by_id is None:
        return None
    u = await ctx.db.get(User, a.created_by_id)
    return u.name if u is not None else None


async def list_for_match(ctx: Ctx, match_id: uuid.UUID) -> list[AttachmentOut]:
    await get_match(ctx, match_id)
    rows = (
        await ctx.db.execute(
            select(MatchAttachment, User.name)
            .outerjoin(User, User.id == MatchAttachment.created_by_id)
            .where(MatchAttachment.match_id == match_id, MatchAttachment.status == "ready")
            .order_by(MatchAttachment.created_at.desc())
        )
    ).all()
    return [_out(a, name) for a, name in rows]


async def create(
    ctx: Ctx, match_id: uuid.UUID, data: AttachmentCreate
) -> tuple[AttachmentOut, str]:
    match = await get_match(ctx, match_id, Action.MATCH_WRITE)
    if data.content_type not in TYPES:
        raise ProblemError(415, "unsupported-file", "Attach a photo (JPG, PNG, HEIC) or a PDF")
    if data.size_bytes > MAX_BYTES:
        raise ProblemError(413, "file-too-large", "A file can be at most 25 MB")
    count = await ctx.db.scalar(
        select(func.count(MatchAttachment.id)).where(MatchAttachment.match_id == match.id)
    )
    if int(count or 0) >= MAX_PER_MATCH:
        raise ProblemError(409, "too-many-files", f"At most {MAX_PER_MATCH} files per match")
    await billing.check_upload(ctx, match.organization_id, data.size_bytes)
    aid = uuid.uuid4()
    key = f"{match.organization_id}/{match.id}/attachments/{aid}/file.{TYPES[data.content_type]}"
    bucket = ctx.settings.s3_bucket_videos
    upload_id = await ctx.storage.create_multipart(bucket, key, data.content_type)
    a = MatchAttachment(
        id=aid,
        organization_id=match.organization_id,
        match_id=match.id,
        filename=clean_name(data.filename),
        content_type=data.content_type,
        size_bytes=data.size_bytes,
        storage_key=key,
        upload_id=upload_id,
        status="uploading",
        note=(data.note or "").strip() or None,
        created_by_id=ctx.user_id,
    )
    ctx.db.add(a)
    await ctx.db.flush()
    url = await ctx.storage.presign_part(bucket, key, upload_id, 1)
    return _out(a, None), url


async def complete(ctx: Ctx, attachment_id: uuid.UUID, etag: str) -> AttachmentOut:
    a = await _get(ctx, attachment_id, Action.MATCH_WRITE)
    if a.status != "uploading" or not a.upload_id:
        raise ProblemError(409, "upload-closed", "This upload is already finished")
    bucket = ctx.settings.s3_bucket_videos
    try:
        await ctx.storage.complete_multipart(
            bucket, a.storage_key, a.upload_id, [(1, etag.strip('"'))]
        )
        data, _ = await ctx.storage.get(bucket, a.storage_key)
    except (ValueError, ObjectNotFoundError) as exc:
        raise ProblemError(422, "incomplete-upload", "The file did not arrive completely") from exc
    except Exception as exc:  # storage rejected the part list (etag mismatch)
        raise ProblemError(422, "incomplete-upload", "The storage rejected the upload") from exc
    found = sniff(data[:32])
    same_family = found is not None and (
        found == a.content_type or (found == "image/heic" and a.content_type == "image/heif")
    )
    if len(data) != a.size_bytes or not same_family:
        await ctx.storage.delete(bucket, a.storage_key)
        await ctx.db.delete(a)
        await ctx.db.flush()
        raise ProblemError(415, "unsupported-file", "Attach a photo (JPG, PNG, HEIC) or a PDF")
    a.upload_id = None
    a.status = "ready"
    await audit.record(
        ctx,
        "attachment.added",
        target_type="match",
        target_id=a.match_id,
        data={"attachment": str(a.id), "type": a.content_type, "size": a.size_bytes},
    )
    return _out(a, await _author(ctx, a))


async def update(ctx: Ctx, attachment_id: uuid.UUID, data: AttachmentUpdate) -> AttachmentOut:
    a = await _get(ctx, attachment_id, Action.MATCH_WRITE)
    a.note = (data.note or "").strip() or None
    await audit.record(
        ctx,
        "attachment.updated",
        target_type="match",
        target_id=a.match_id,
        data={"attachment": str(a.id)},
    )
    return _out(a, await _author(ctx, a))


async def delete(ctx: Ctx, attachment_id: uuid.UUID) -> None:
    a = await _get(ctx, attachment_id, Action.MATCH_WRITE)
    bucket = ctx.settings.s3_bucket_videos
    if a.upload_id:
        await ctx.storage.abort_multipart(bucket, a.storage_key, a.upload_id)
    else:
        await ctx.storage.delete(bucket, a.storage_key)
    match_id = a.match_id
    await ctx.db.delete(a)
    await ctx.db.flush()
    await audit.record(
        ctx,
        "attachment.deleted",
        target_type="match",
        target_id=match_id,
        data={"attachment": str(attachment_id), "filename": a.filename},
    )


async def read(ctx: Ctx, attachment_id: uuid.UUID) -> tuple[bytes, MatchAttachment]:
    a = await _get(ctx, attachment_id, Action.MATCH_READ)
    if a.status != "ready":
        raise ProblemError(404, "not-found", "File not found")
    try:
        data, _ = await ctx.storage.get(ctx.settings.s3_bucket_videos, a.storage_key)
    except ObjectNotFoundError as exc:
        raise ProblemError(404, "not-found", "File not found") from exc
    return data, a


def headers(a: MatchAttachment, download: bool) -> dict[str, Any]:
    """Photos inline, PDFs as a download (never rendered as a page of the app origin)."""
    from urllib.parse import quote

    inline = a.content_type.startswith("image/") and not download
    name = quote(a.filename)
    return {
        "content-disposition": f"{'inline' if inline else 'attachment'}; filename*=UTF-8''{name}",
        "x-content-type-options": "nosniff",
        "content-security-policy": "default-src 'none'; img-src 'self'; sandbox",
        "cache-control": "private, max-age=3600",
    }
