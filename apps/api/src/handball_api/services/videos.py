"""Video upload (direct multipart to storage), link import, ingest jobs and media access."""

from __future__ import annotations

import math
import re
import uuid
from datetime import UTC, datetime
from pathlib import PurePosixPath

from sqlalchemy import delete, select

from handball_api.core.db import disable_system_access, enable_system_access, set_tenant
from handball_api.core.errors import ProblemError
from handball_api.core.net import UnsafeUrlError, check_public_https_url
from handball_api.core.storage import ObjectNotFoundError
from handball_api.models import CameraCalibration, Match, ProcessingJob, Track, VideoAsset
from handball_api.models.enums import JobStatus, MatchStatus, VideoRole, VideoStatus
from handball_api.schemas.matches import JobUpdate, LinkImport, UploadComplete, UploadCreate
from handball_api.services import audit
from handball_api.services.context import Ctx
from handball_api.services.matches import get_match
from handball_api.services.policies import Action

PIPELINE_VERSION = "0.2.0"
INGEST_FUNC = "handball_worker.ingest.run_ingest"
ANALYSIS_FUNC = "handball_gpu_worker.analysis.run_analysis"
IMPORT_FUNC = "handball_worker.ingest.run_import"
MEDIA_PATH = re.compile(r"^[A-Za-z0-9_\-]+(/[A-Za-z0-9_\-]+)*\.(m3u8|m4s|mp4|ts|jpg|vtt)$")
MEDIA_TYPES = {
    "m3u8": "application/vnd.apple.mpegurl",
    "m4s": "video/iso.segment",
    "mp4": "video/mp4",
    "ts": "video/mp2t",
    "jpg": "image/jpeg",
    "vtt": "text/vtt",
}
VIDEO_EXT = re.compile(r"\.(mp4|mov|m4v|mkv|avi|mts|m2ts|webm)$", re.IGNORECASE)


def _key(match: Match, asset_id: uuid.UUID, filename: str) -> str:
    m = VIDEO_EXT.search(filename)
    ext = m.group(0).lower() if m else ""
    return f"{match.organization_id}/{match.id}/{asset_id}/original{ext}"


def media_prefix(asset: VideoAsset) -> str:
    return f"{asset.organization_id}/{asset.match_id}/{asset.id}/"


async def create_upload(
    ctx: Ctx, match_id: uuid.UUID, data: UploadCreate
) -> tuple[VideoAsset, int, int]:
    match = await get_match(ctx, match_id, Action.VIDEO_UPLOAD)
    if data.size_bytes > ctx.settings.max_video_bytes:
        raise ProblemError(413, "video-too-large", "The video is too large")
    if not VIDEO_EXT.search(data.filename):
        raise ProblemError(415, "unsupported-video", "Use MP4, MOV, MKV, AVI, MTS or WebM")
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
    return asset, part_size, math.ceil(data.size_bytes / part_size)


async def get_asset(
    ctx: Ctx, asset_id: uuid.UUID, action: Action = Action.MATCH_READ
) -> VideoAsset:
    asset = await ctx.db.get(VideoAsset, asset_id)
    if asset is None:
        raise ProblemError(404, "not-found", "Video not found")
    await get_match(ctx, asset.match_id, action)
    return asset


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
    asset = await get_asset(ctx, asset_id, Action.VIDEO_UPLOAD)
    if asset.upload_id:
        await ctx.storage.abort_multipart(
            ctx.settings.s3_bucket_videos, asset.storage_key, asset.upload_id
        )
    await ctx.storage.delete_prefix(ctx.settings.s3_bucket_videos, media_prefix(asset))
    await ctx.db.delete(asset)
    await audit.record(ctx, "video.deleted", target_type="video", target_id=asset_id)


async def import_link(ctx: Ctx, match_id: uuid.UUID, data: LinkImport) -> VideoAsset:
    match = await get_match(ctx, match_id, Action.VIDEO_UPLOAD)
    url = str(data.url)
    try:
        check_public_https_url(url)
    except UnsafeUrlError as exc:
        raise ProblemError(422, "unsafe-url", str(exc)) from exc
    asset_id = uuid.uuid4()
    name = PurePosixPath(url.split("?")[0]).name or "video.mp4"
    if not VIDEO_EXT.search(name):
        name = f"{name}.mp4"
    asset = VideoAsset(
        id=asset_id,
        organization_id=match.organization_id,
        match_id=match.id,
        role=data.role,
        status=VideoStatus.UPLOADING,
        filename=name[:255],
        content_type="video/mp4",
        size_bytes=0,
        storage_key=_key(match, asset_id, name),
        part_size=ctx.settings.upload_part_size,
        source_url=url,
    )
    ctx.db.add(asset)
    await ctx.db.flush()
    job = await _new_job(ctx, asset, "import")
    ctx.require_jobs().enqueue(
        "pipeline", IMPORT_FUNC, str(job.id), _job_payload(ctx, asset, job, url=url)
    )
    await audit.record(
        ctx, "video.import_started", target_type="video", target_id=asset.id, data={"url": url}
    )
    return asset


async def _new_job(ctx: Ctx, asset: VideoAsset, kind: str) -> ProcessingJob:
    job = ProcessingJob(
        organization_id=asset.organization_id,
        match_id=asset.match_id,
        video_asset_id=asset.id,
        kind=kind,
        pipeline_version=PIPELINE_VERSION,
        status=JobStatus.QUEUED,
        progress=0.0,
        stages={},
    )
    ctx.db.add(job)
    await ctx.db.flush()
    return job


def _job_payload(ctx: Ctx, asset: VideoAsset, job: ProcessingJob, **extra: str) -> dict[str, str]:
    return {
        "job_id": str(job.id),
        "organization_id": str(asset.organization_id),
        "match_id": str(asset.match_id),
        "asset_id": str(asset.id),
        "bucket": ctx.settings.s3_bucket_videos,
        "key": asset.storage_key,
        "prefix": media_prefix(asset),
        **extra,
    }


async def start_ingest(ctx: Ctx, asset: VideoAsset) -> ProcessingJob:
    job = await _new_job(ctx, asset, "ingest")
    asset.status = VideoStatus.PROCESSING
    match = await ctx.db.get(Match, asset.match_id)
    if match is not None and match.status != MatchStatus.READY:
        match.status = MatchStatus.PROCESSING
    ctx.require_jobs().enqueue("pipeline", INGEST_FUNC, str(job.id), _job_payload(ctx, asset, job))
    return job


async def reprocess(ctx: Ctx, asset_id: uuid.UUID) -> ProcessingJob:
    asset = await get_asset(ctx, asset_id, Action.VIDEO_UPLOAD)
    if asset.status == VideoStatus.UPLOADING:
        raise ProblemError(409, "upload-open", "The upload is not finished")
    await audit.record(ctx, "video.reprocess", target_type="video", target_id=asset.id)
    return await start_ingest(ctx, asset)


async def set_offset(ctx: Ctx, asset_id: uuid.UUID, offset_ms: int) -> VideoAsset:
    asset = await get_asset(ctx, asset_id, Action.VIDEO_UPLOAD)
    asset.time_offset_ms = offset_ms
    return asset


async def read_media(ctx: Ctx, asset_id: uuid.UUID, path: str) -> tuple[bytes, str]:
    asset = await get_asset(ctx, asset_id)
    if not MEDIA_PATH.match(path) or ".." in path:
        raise ProblemError(404, "not-found", "Not found")
    if path == "proxy.mp4" or path.startswith("original"):
        raise ProblemError(404, "not-found", "Not found")
    try:
        data, _ = await ctx.storage.get(ctx.settings.s3_bucket_videos, media_prefix(asset) + path)
    except ObjectNotFoundError as exc:
        raise ProblemError(404, "not-found", "Not found") from exc
    return data, MEDIA_TYPES[path.rsplit(".", 1)[1]]


# ---- worker callbacks (internal) ------------------------------------------------------------


def job_event(job: ProcessingJob) -> dict[str, object]:
    return {
        "type": "job",
        "job_id": str(job.id),
        "kind": job.kind,
        "status": job.status,
        "progress": job.progress,
        "stages": job.stages,
        "error": job.error,
        "video_asset_id": str(job.video_asset_id) if job.video_asset_id else None,
    }


async def apply_job_update(ctx: Ctx, job_id: uuid.UUID, data: JobUpdate) -> ProcessingJob:
    await enable_system_access(ctx.db, reason="worker job callback")
    job = await ctx.db.get(ProcessingJob, job_id)
    await disable_system_access(ctx.db)
    if job is None:
        raise ProblemError(404, "not-found", "Job not found")
    await set_tenant(ctx.db, job.organization_id)
    now = datetime.now(UTC)
    if job.status in (JobStatus.SUCCEEDED, JobStatus.CANCELLED):
        return job  # late or duplicate callbacks are ignored (idempotent)
    if job.started_at is None and data.status != JobStatus.QUEUED:
        job.started_at = now
    job.status = data.status
    job.progress = (
        max(job.progress, data.progress) if data.status == JobStatus.RUNNING else data.progress
    )
    if data.stages is not None:
        job.stages = {**job.stages, **data.stages}
    if data.gpu_seconds is not None:
        job.gpu_seconds = data.gpu_seconds
    if data.cost_chf is not None:
        job.cost_chf = data.cost_chf
    asset = await ctx.db.get(VideoAsset, job.video_asset_id) if job.video_asset_id else None
    match = await ctx.db.get(Match, job.match_id)
    if data.status in (JobStatus.SUCCEEDED, JobStatus.FAILED):
        job.finished_at = now
        job.error = data.error
    if asset is not None and match is not None:
        if data.status == JobStatus.FAILED and job.kind == "analysis":
            pass  # the video stays playable; the analysis error is shown on its own
        elif data.status == JobStatus.FAILED:
            asset.status = VideoStatus.FAILED
            asset.error = data.error
            match.status = MatchStatus.FAILED
        elif data.status == JobStatus.SUCCEEDED and job.kind == "import" and data.result:
            asset.size_bytes = int(data.result.get("size_bytes", 0))
            asset.status = VideoStatus.UPLOADED
            await start_ingest(ctx, asset)
        elif data.status == JobStatus.SUCCEEDED and job.kind == "ingest" and data.result:
            _apply_ingest_result(asset, data.result)
            match.status = MatchStatus.READY
            if asset.role == VideoRole.MAIN and asset.proxy_key:
                await start_analysis(ctx, asset, match)
        elif data.status == JobStatus.SUCCEEDED and job.kind == "analysis" and data.result:
            await _apply_analysis_result(ctx, asset, job, data.result)
    await ctx.db.flush()
    await ctx.require_events().publish(f"match:{job.match_id}", job_event(job))
    return job


def _apply_ingest_result(asset: VideoAsset, r: dict[str, object]) -> None:
    def num(key: str) -> float | None:
        v = r.get(key)
        return float(v) if isinstance(v, int | float) else None

    asset.status = VideoStatus.READY
    asset.error = None
    asset.checksum_sha256 = str(r.get("checksum_sha256") or "") or None
    asset.duration_s = num("duration_s")
    asset.fps = num("fps")
    w, h = num("width"), num("height")
    asset.width = int(w) if w else None
    asset.height = int(h) if h else None
    asset.codec = str(r.get("codec") or "") or None
    asset.hls_prefix = str(r.get("hls_prefix") or "") or None
    asset.proxy_key = str(r.get("proxy_key") or "") or None
    asset.poster_key = str(r.get("poster_key") or "") or None
    report = r.get("quality_report")
    asset.quality_report = report if isinstance(report, dict) else None


# ---- analysis (stages 2 to 5) ---------------------------------------------------------------


async def start_analysis(
    ctx: Ctx, asset: VideoAsset, match: Match, points: list[dict[str, list[float]]] | None = None
) -> ProcessingJob:
    job = await _new_job(ctx, asset, "analysis")
    payload: dict[str, object] = {
        "job_id": str(job.id),
        "organization_id": str(asset.organization_id),
        "match_id": str(asset.match_id),
        "asset_id": str(asset.id),
        "bucket": ctx.settings.s3_bucket_videos,
        "proxy_key": asset.proxy_key,
        "prefix": media_prefix(asset),
        "kits": {
            "home": match.kit_own,
            "home_gk": match.kit_own_gk,
            "away": match.kit_opponent,
            "away_gk": match.kit_opponent_gk,
            "referee": "#1a1a1a",
        },
        "calibration_points": points,
    }
    ctx.require_jobs().enqueue("gpu", ANALYSIS_FUNC, str(job.id), payload)
    return job


async def _apply_analysis_result(
    ctx: Ctx, asset: VideoAsset, job: ProcessingJob, r: dict[str, object]
) -> None:
    cal = r.get("calibration")
    if isinstance(cal, dict):
        prev_points = (
            await ctx.db.scalar(
                select(CameraCalibration.points)
                .where(
                    CameraCalibration.video_asset_id == asset.id,
                    CameraCalibration.source == "user_correction",
                )
                .order_by(CameraCalibration.created_at.desc())
                .limit(1)
            )
            if cal.get("source") == "user_correction"
            else None
        )
        ctx.db.add(
            CameraCalibration(
                organization_id=asset.organization_id,
                video_asset_id=asset.id,
                homography=cal["homography"],
                image_size=cal["image_size"],
                confidence=float(cal["confidence"]),
                reprojection_px=float(cal["reprojection_px"]),
                source=str(cal["source"]),
                points=prev_points,
                pipeline_version=job.pipeline_version,
            )
        )
    await ctx.db.execute(delete(Track).where(Track.video_asset_id == asset.id))
    tracks = r.get("tracks")
    detector = str(r.get("detector") or "heuristic")
    if isinstance(tracks, list):
        for t in tracks:
            ctx.db.add(
                Track(
                    organization_id=asset.organization_id,
                    match_id=asset.match_id,
                    video_asset_id=asset.id,
                    track_no=int(t["track_id"]),
                    team=t.get("team"),
                    team_confidence=t.get("team_confidence"),
                    first_ms=int(t["first_ms"]),
                    last_ms=int(t["last_ms"]),
                    observed_share=float(t["observed_share"]),
                    source=detector,
                    pipeline_version=job.pipeline_version,
                )
            )
    asset.analysis = {
        k: r.get(k)
        for k in (
            "chunks",
            "chunk_ms",
            "fps",
            "frames",
            "detector",
            "versions",
            "timings_s",
            "elapsed_s",
            "stats",
        )
    }


async def analysis(ctx: Ctx, asset_id: uuid.UUID) -> dict[str, object]:
    asset = await get_asset(ctx, asset_id)
    cal = await ctx.db.scalar(
        select(CameraCalibration)
        .where(CameraCalibration.video_asset_id == asset.id)
        .order_by(CameraCalibration.created_at.desc())
        .limit(1)
    )
    tracks = (
        await ctx.db.scalars(
            select(Track).where(Track.video_asset_id == asset.id).order_by(Track.track_no)
        )
    ).all()
    job = await ctx.db.scalar(
        select(ProcessingJob)
        .where(ProcessingJob.video_asset_id == asset.id, ProcessingJob.kind == "analysis")
        .order_by(ProcessingJob.created_at.desc())
        .limit(1)
    )
    meta = asset.analysis or {}
    status = "none"
    if job is not None:
        status = {
            "queued": "running",
            "running": "running",
            "succeeded": "ready",
            "failed": "failed",
        }.get(job.status, "none")
    return {
        "status": status,
        "calibration": cal,
        "tracks": list(tracks),
        "chunk_ms": meta.get("chunk_ms"),
        "chunks": meta.get("chunks"),
        "fps": meta.get("fps"),
        "detector": meta.get("detector"),
        "elapsed_s": meta.get("elapsed_s"),
        "error": job.error if job is not None and job.status == "failed" else None,
    }


async def read_track_chunk(ctx: Ctx, asset_id: uuid.UUID, n: int) -> bytes:
    asset = await get_asset(ctx, asset_id)
    meta = asset.analysis or {}
    if not isinstance(meta.get("chunks"), int) or not 0 <= n < int(meta["chunks"]):
        raise ProblemError(404, "not-found", "No such chunk")
    try:
        data, _ = await ctx.storage.get(
            ctx.settings.s3_bucket_artifacts, f"{media_prefix(asset)}analysis/chunk_{n:05d}.bin"
        )
    except ObjectNotFoundError as exc:
        raise ProblemError(404, "not-found", "No such chunk") from exc
    return data


async def calibrate_manually(
    ctx: Ctx, asset_id: uuid.UUID, points: list[dict[str, list[float]]]
) -> ProcessingJob:
    """Store clicked correspondences and re-run the analysis with them (source user_correction)."""
    asset = await get_asset(ctx, asset_id, Action.VIDEO_UPLOAD)
    if asset.status != VideoStatus.READY or not asset.proxy_key:
        raise ProblemError(409, "video-not-ready", "The video is still being processed")
    match = await ctx.db.get(Match, asset.match_id)
    assert match is not None
    await audit.record(
        ctx,
        "video.calibrated_manually",
        target_type="video",
        target_id=asset.id,
        data={"points": len(points)},
    )
    return await start_analysis(ctx, asset, match, points)
