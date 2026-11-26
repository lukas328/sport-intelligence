"""Uploads (direct multipart to storage), deleting a file and the match status from its files."""

from __future__ import annotations

import math
import uuid

from sqlalchemy import select

from handball_api.core.errors import ProblemError
from handball_api.core.storage import ObjectNotFoundError
from handball_api.models import Match, VideoAsset
from handball_api.models.enums import MatchStatus, VideoRole, VideoStatus
from handball_api.schemas.matches import UploadComplete, UploadCreate
from handball_api.services import audit, billing, feed, highlights, timeline
from handball_api.services.context import Ctx
from handball_api.services.matches import get_match, parts_of
from handball_api.services.policies import Action
from handball_api.services.video_analysis import start_waiting
from handball_api.services.video_base import VIDEO_EXT, get_asset
from handball_api.services.video_jobs import start_ingest
from handball_api.services.video_media import media_prefix


def _key(match: Match, asset_id: uuid.UUID, filename: str) -> str:
    m = VIDEO_EXT.search(filename)
    ext = m.group(0).lower() if m else ""
    return f"{match.organization_id}/{match.id}/{asset_id}/original{ext}"


async def create_upload(
    ctx: Ctx, match_id: uuid.UUID, data: UploadCreate
) -> tuple[VideoAsset, int, int, bool]:
    """A new upload, or the unfinished upload of the same file (name, size, camera) to go on with
    (`resumed`): after a reload, on another device or with the browser's memory cleared, choosing
    the file again continues where it stopped instead of answering «already in the match» (L4)."""
    match = await get_match(ctx, match_id, Action.VIDEO_UPLOAD)
    if data.size_bytes > ctx.settings.max_video_bytes:
        raise ProblemError(413, "video-too-large", "The video is too large")
    if not VIDEO_EXT.search(data.filename):
        raise ProblemError(415, "unsupported-video", "Use MP4, MOV, MKV, AVI, MTS or WebM")
    open_upload = await ctx.db.scalar(
        select(VideoAsset).where(
            VideoAsset.match_id == match.id,
            VideoAsset.role == data.role,
            VideoAsset.filename == data.filename,
            VideoAsset.size_bytes == data.size_bytes,
            VideoAsset.status == VideoStatus.UPLOADING,
            VideoAsset.upload_id.is_not(None),
            VideoAsset.source_url.is_(None),
        )
    )
    if open_upload is not None:
        try:
            await ctx.storage.list_parts(
                ctx.settings.s3_bucket_videos, open_upload.storage_key, str(open_upload.upload_id)
            )
        except ObjectNotFoundError:
            # the storage forgot the parts: that upload is over, a new one starts below
            open_upload.status = VideoStatus.FAILED
            open_upload.error = "upload expired"
            open_upload.upload_id = None
            await ctx.db.flush()
        else:
            await audit.record(
                ctx, "video.upload_resumed", target_type="video", target_id=open_upload.id
            )
            count = math.ceil(open_upload.size_bytes / open_upload.part_size)
            return open_upload, open_upload.part_size, count, True
    same = await ctx.db.scalar(
        select(VideoAsset.id).where(
            VideoAsset.match_id == match.id,
            VideoAsset.role == data.role,
            VideoAsset.filename == data.filename,
            VideoAsset.size_bytes == data.size_bytes,
            VideoAsset.status != VideoStatus.FAILED,
        )
    )
    if same is not None:
        # the same file twice (chosen again, or both halves picked as one): said, not stored
        raise ProblemError(409, "same-file", "This file is already in the match")
    await billing.check_upload(ctx, match.organization_id, data.size_bytes)
    asset_id = uuid.uuid4()
    # S3 allows at most 10'000 parts; grow the part size for huge files.
    part_size = max(ctx.settings.upload_part_size, math.ceil(data.size_bytes / 10_000))
    key = _key(match, asset_id, data.filename)
    upload_id = await ctx.storage.create_multipart(
        ctx.settings.s3_bucket_videos, key, data.content_type
    )
    asset = VideoAsset(
        id=asset_id,
        organization_id=match.organization_id,
        match_id=match.id,
        role=data.role,
        status=VideoStatus.UPLOADING,
        filename=data.filename,
        content_type=data.content_type,
        size_bytes=data.size_bytes,
        storage_key=key,
        upload_id=upload_id,
        part_size=part_size,
        uploaded_by_id=ctx.user_id,
    )
    ctx.db.add(asset)
    if match.status == MatchStatus.SCHEDULED:
        match.status = MatchStatus.UPLOADING
    await ctx.db.flush()
    await audit.record(
        ctx,
        "video.upload_started",
        target_type="video",
        target_id=asset.id,
        data={"size": data.size_bytes, "role": data.role},
    )
    return asset, part_size, math.ceil(data.size_bytes / part_size), False


def _uploading(asset: VideoAsset) -> str:
    if asset.status != VideoStatus.UPLOADING or not asset.upload_id:
        raise ProblemError(409, "upload-closed", "This upload is already finished")
    return asset.upload_id


async def presign_parts(ctx: Ctx, asset_id: uuid.UUID, numbers: list[int]) -> list[tuple[int, str]]:
    asset = await get_asset(ctx, asset_id, Action.VIDEO_UPLOAD)
    upload_id = _uploading(asset)
    count = math.ceil(asset.size_bytes / asset.part_size)
    if any(n < 1 or n > count for n in numbers):
        raise ProblemError(422, "invalid-part", f"Part numbers must be between 1 and {count}")
    return [
        (
            n,
            await ctx.storage.presign_part(
                ctx.settings.s3_bucket_videos, asset.storage_key, upload_id, n
            ),
        )
        for n in sorted(set(numbers))
    ]


async def list_parts(ctx: Ctx, asset_id: uuid.UUID) -> list[tuple[int, str, int]]:
    asset = await get_asset(ctx, asset_id, Action.VIDEO_UPLOAD)
    upload_id = _uploading(asset)
    try:
        parts = await ctx.storage.list_parts(
            ctx.settings.s3_bucket_videos, asset.storage_key, upload_id
        )
    except ObjectNotFoundError as exc:
        raise ProblemError(410, "upload-expired", "The upload expired, start again") from exc
    return [(p.number, p.etag, p.size) for p in parts]


async def complete_upload(ctx: Ctx, asset_id: uuid.UUID, data: UploadComplete) -> VideoAsset:
    asset = await get_asset(ctx, asset_id, Action.VIDEO_UPLOAD)
    upload_id = _uploading(asset)
    count = math.ceil(asset.size_bytes / asset.part_size)
    numbers = sorted(p.number for p in data.parts)
    if numbers != list(range(1, count + 1)):
        raise ProblemError(422, "incomplete-upload", f"Expected parts 1 to {count}")
    try:
        await ctx.storage.complete_multipart(
            ctx.settings.s3_bucket_videos,
            asset.storage_key,
            upload_id,
            [(p.number, p.etag.strip('"')) for p in data.parts],
        )
        size = await ctx.storage.size(ctx.settings.s3_bucket_videos, asset.storage_key)
    except (ValueError, ObjectNotFoundError) as exc:
        raise ProblemError(422, "incomplete-upload", "Parts are missing or damaged") from exc
    except Exception as exc:  # storage errors (e.g. etag mismatch) surface as client errors
        raise ProblemError(422, "incomplete-upload", "The storage rejected the upload") from exc
    if size != asset.size_bytes:
        raise ProblemError(422, "incomplete-upload", "The uploaded size does not match")
    asset.upload_id = None
    asset.status = VideoStatus.UPLOADED
    await audit.record(ctx, "video.uploaded", target_type="video", target_id=asset.id)
    await start_ingest(ctx, asset)
    return asset


async def abort_upload(ctx: Ctx, asset_id: uuid.UUID) -> None:
    """Deletes a file of the match (an upload not finished, or a part): the parts after it move
    up, and what the analysis found in it goes with it."""
    asset = await get_asset(ctx, asset_id, Action.VIDEO_UPLOAD)
    # cancelling an upload that is still running is part of uploading; a file that arrived is
    # deleted by the staff only (players upload, they do not delete: K18)
    if asset.status != VideoStatus.UPLOADING:
        await get_asset(ctx, asset_id, Action.MATCH_DELETE)
    match = await ctx.db.get(Match, asset.match_id)
    before = await parts_of(ctx, asset.match_id)
    placed = any(p.video_id == asset.id for p in before)
    if asset.upload_id:
        await ctx.storage.abort_multipart(
            ctx.settings.s3_bucket_videos, asset.storage_key, asset.upload_id
        )
    await ctx.storage.delete_prefix(ctx.settings.s3_bucket_videos, media_prefix(asset))
    await ctx.storage.delete_prefix(ctx.settings.s3_bucket_artifacts, media_prefix(asset))
    await ctx.db.delete(asset)
    await ctx.db.flush()
    if match is not None and placed:
        await timeline.settle(ctx, match, before)
        await _whole_match(ctx, match)
        await start_waiting(ctx, match)
    if match is not None:
        # the last file gone, or only a failed one left: the match no longer says «wird
        # hochgeladen» or «Analyse läuft» (second round A1)
        await settle_status(ctx, match)
    await audit.record(ctx, "video.deleted", target_type="video", target_id=asset_id)


async def settle_status(ctx: Ctx, match: Match) -> None:
    """The match's status from its files, after one was removed or given up: playable when one
    plays, being processed or uploaded while one is, failed when all failed; with no file left
    it waits for a video again."""
    if match.status not in (
        MatchStatus.UPLOADING,
        MatchStatus.PROCESSING,
        MatchStatus.READY,
        MatchStatus.FAILED,
    ):
        return
    rows = (
        await ctx.db.scalars(
            select(VideoAsset.status).where(
                VideoAsset.match_id == match.id, VideoAsset.role == VideoRole.MAIN
            )
        )
    ).all()
    states = set(rows)
    if VideoStatus.READY in states:
        match.status = MatchStatus.READY
    elif states & {VideoStatus.UPLOADED, VideoStatus.PROCESSING}:
        match.status = MatchStatus.PROCESSING
    elif VideoStatus.UPLOADING in states:
        match.status = MatchStatus.UPLOADING
    elif states:
        match.status = MatchStatus.FAILED
    elif match.status != MatchStatus.READY:
        # no video left: a match with a report stays as it is, one without waits for a video
        match.status = MatchStatus.SCHEDULED
    await ctx.db.flush()


async def _whole_match(ctx: Ctx, match: Match) -> None:
    """What looks at the whole match, again after its parts changed: «Deine Szenen» and the
    reels (the result, the three things and the numbers are read live from the events)."""
    await feed.generate(ctx, match)
    await highlights.auto(ctx, match)
