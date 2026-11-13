"""Video upload (direct multipart to storage), link import, ingest jobs and media access."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import math
import re
import uuid
from datetime import UTC, datetime
from pathlib import PurePosixPath
from typing import Any

from sqlalchemy import delete, func, select

from handball_api.core.colors import analysis_kits
from handball_api.core.db import disable_system_access, enable_system_access, set_tenant
from handball_api.core.email import try_send
from handball_api.core.errors import ProblemError
from handball_api.core.net import UnsafeUrlError, check_public_https_url
from handball_api.core.storage import ObjectNotFoundError
from handball_api.models import (
    CameraCalibration,
    Event,
    Match,
    Opponent,
    OpponentPlayer,
    ProcessingJob,
    RosterEntry,
    Team,
    Track,
    User,
    VideoAsset,
)
from handball_api.models.enums import JobStatus, MatchStatus, VideoRole, VideoStatus
from handball_api.schemas.matches import JobUpdate, LinkImport, UploadComplete, UploadCreate
from handball_api.services import audit, auto_events, billing, feed, halls, segments, training
from handball_api.services.context import Ctx
from handball_api.services.mail_templates import render
from handball_api.services.matches import get_match, timeline_video
from handball_api.services.policies import Action
from handball_api.services.roster import numbers as roster_numbers
from handball_api.services.segments import parse_recorded
from handball_api.services.support import failure_code

PIPELINE_VERSION = "0.2.0"
# keys of VideoAsset.analysis: the court points the coach clicked (of the last run that succeeded
# with them, reused by every later run) and those of a run still going
CLICKED, PENDING = "court_points", "court_points_pending"
INGEST_FUNC = "handball_worker.ingest.run_ingest"
ANALYSIS_FUNC = "handball_gpu_worker.analysis.run_analysis"
SYNC_FUNC = "handball_gpu_worker.sync.run_sync"
SYNC_MIN_CONFIDENCE = 0.35
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
    return media_prefix_of(asset.organization_id, asset.match_id, asset.id)


def media_prefix_of(org_id: uuid.UUID, match_id: uuid.UUID, video_id: uuid.UUID) -> str:
    return f"{org_id}/{match_id}/{video_id}/"


async def create_upload(
    ctx: Ctx, match_id: uuid.UUID, data: UploadCreate
) -> tuple[VideoAsset, int, int]:
    match = await get_match(ctx, match_id, Action.VIDEO_UPLOAD)
    if data.size_bytes > ctx.settings.max_video_bytes:
        raise ProblemError(413, "video-too-large", "The video is too large")
    if not VIDEO_EXT.search(data.filename):
        raise ProblemError(415, "unsupported-video", "Use MP4, MOV, MKV, AVI, MTS or WebM")
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


THREE_THINGS_MIN_GOALS = 3  # fewer goals in the video carry no three things


async def _tell_staff(ctx: Ctx, match: Match, kind: str, extra: dict[str, Any]) -> None:
    """A note in the bell and an e-mail to the team's coaches and analysts, naming the match
    (UX test H06, B29): on the phone the bell alone is easy to miss."""
    team = await ctx.db.get(Team, match.team_id)
    opp = await ctx.db.get(Opponent, match.opponent_id) if match.opponent_id else None
    opponent = opp.name if opp else "Training"
    link = f"/app/{match.organization_id}/matches/{match.id}"
    staff = await training.staff_of(ctx, match.team_id)
    await training.notify(
        ctx,
        match.organization_id,
        staff,
        kind,
        {"match_id": str(match.id), "opponent": opponent, **extra},
        link,
    )
    users = (await ctx.db.scalars(select(User).where(User.id.in_(staff)))).all() if staff else []
    for u in users:
        await try_send(
            ctx.email,
            render(
                kind,
                u.locale,
                to=u.email,
                name=u.name,
                team=team.name if team else "",
                opponent=opponent,
                link=f"{ctx.settings.web_base_url}{link}",
                **{k: v for k, v in extra.items() if k == "questions"},
            ),
            kind,
            user_id=str(u.id),
        )


async def _ready_note(ctx: Ctx, match: Match) -> tuple[str, dict[str, Any]]:
    """What the mail may promise after the analysis (UX test N05): the three things only with
    goals placed in the video; otherwise that the analysis is done and how many questions wait."""
    goals = await ctx.db.scalar(
        select(func.count())
        .select_from(Event)
        .where(
            Event.match_id == match.id,
            Event.type == "shot",
            Event.outcome == "goal",
            Event.t_ms.is_not(None),
        )
    )
    if (goals or 0) >= THREE_THINGS_MIN_GOALS:
        return "analysis_ready", {}
    # the same questions the start and Prüfen show (UX test A02: one count, not two)
    from handball_api.services.graphics import open_checks

    questions = len(await open_checks(ctx, match))
    return ("analysis_questions" if questions else "analysis_no_goals"), {"questions": questions}


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
        await asyncio.to_thread(check_public_https_url, url)  # DNS lookup blocks
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
    await ctx.enqueue("pipeline", IMPORT_FUNC, str(job.id), _job_payload(ctx, asset, job, url=url))
    await audit.record(
        ctx, "video.import_started", target_type="video", target_id=asset.id, data={"url": url}
    )
    return asset


def job_budget_s(kind: str, duration_s: float | None = None, size_bytes: int | None = None) -> int:
    """How long a video job may run before the worker stops it (and before the alerting calls it
    stuck). Six hours covered the five-minute test clips; a full game of 120 minutes takes about
    2.2 x real time to analyse on a CPU worker (docs/perf/real-videos.md), the ingest of a file of
    many GB on a slow disk about real time per GB of 10 minutes."""
    base = 6 * 3600
    if kind == "analysis" and duration_s:
        return max(base, int(3 * duration_s) + 3600)
    if kind == "ingest" and size_bytes:
        return max(base, int(size_bytes / 1024**3 * 900) + 3600)
    return base


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
    await ctx.enqueue(
        "pipeline",
        INGEST_FUNC,
        str(job.id),
        _job_payload(ctx, asset, job),
        timeout_s=job_budget_s("ingest", size_bytes=asset.size_bytes),
    )
    return job


async def reprocess(ctx: Ctx, asset_id: uuid.UUID) -> ProcessingJob:
    asset = await get_asset(ctx, asset_id, Action.VIDEO_UPLOAD)
    if asset.status == VideoStatus.UPLOADING:
        raise ProblemError(409, "upload-open", "The upload is not finished")
    await audit.record(ctx, "video.reprocess", target_type="video", target_id=asset.id)
    return await start_ingest(ctx, asset)


async def set_offset(ctx: Ctx, asset_id: uuid.UUID, offset_ms: int) -> VideoAsset:
    """Manual sync: time in this video = time in the main video + offset_ms."""
    asset = await get_asset(ctx, asset_id, Action.VIDEO_UPLOAD)
    asset.time_offset_ms = offset_ms
    asset.sync = {**(asset.sync or {}), "offset_ms": offset_ms, "source": "user_correction"}
    return asset


async def start_sync(ctx: Ctx, main: VideoAsset, other: VideoAsset) -> ProcessingJob | None:
    main_key = (main.sync or {}).get("audio_key")
    other_key = (other.sync or {}).get("audio_key")
    if not main_key or not other_key or (other.sync or {}).get("source") == "user_correction":
        return None
    job = await _new_job(ctx, other, "sync")
    await ctx.enqueue(
        "gpu",
        SYNC_FUNC,
        str(job.id),
        {
            "job_id": str(job.id),
            "bucket": ctx.settings.s3_bucket_videos,
            "main_audio_key": main_key,
            "other_audio_key": other_key,
        },
    )
    return job


async def _sync_after_ingest(ctx: Ctx, asset: VideoAsset) -> None:
    others = (
        await ctx.db.scalars(
            select(VideoAsset).where(
                VideoAsset.match_id == asset.match_id,
                VideoAsset.status == VideoStatus.READY,
                VideoAsset.id != asset.id,
            )
        )
    ).all()
    if asset.role == VideoRole.MAIN:
        for other in others:
            await start_sync(ctx, asset, other)
    else:
        main = next((v for v in others if v.role == VideoRole.MAIN), None)
        if main is not None:
            await start_sync(ctx, main, asset)


def _apply_sync_result(asset: VideoAsset, r: dict[str, object]) -> None:
    offset = r.get("offset_ms")
    conf = r.get("confidence")
    if not isinstance(offset, int | float) or not isinstance(conf, int | float):
        return
    applied = conf >= SYNC_MIN_CONFIDENCE
    if applied:
        asset.time_offset_ms = int(offset)
    asset.sync = {
        **(asset.sync or {}),
        "offset_ms": int(offset),
        "confidence": float(conf),
        "source": "audio",
        "applied": applied,
    }


async def read_media(ctx: Ctx, asset_id: uuid.UUID, path: str) -> tuple[bytes, str]:
    try:
        asset = await get_asset(ctx, asset_id)
    except ProblemError:
        # parents: the match video of a match in which their child has scenes (4.7, 4.9)
        guest = await ctx.db.get(VideoAsset, asset_id)
        if guest is None or not await feed.guardian_sees_match(ctx, guest.match_id):
            raise
        asset = guest
    return await read_media_object(ctx, asset, path)


async def read_media_object(ctx: Ctx, asset: VideoAsset, path: str) -> tuple[bytes, str]:
    """One file of a video's player media (HLS, poster, thumbnails) and its content type, for a
    caller that has already checked access. Originals and the analysis proxy are never served.
    A missing object is a 404; any other storage error propagates (a 500 the alerting sees, not a
    silent 404)."""
    if (
        not MEDIA_PATH.match(path)
        or ".." in path
        or path == "proxy.mp4"
        or path.startswith("original")
    ):
        raise ProblemError(404, "not-found", "Not found")
    try:
        data, _ = await ctx.storage.get(ctx.settings.s3_bucket_videos, media_prefix(asset) + path)
    except ObjectNotFoundError as exc:
        raise ProblemError(404, "not-found", "Not found") from exc
    return data, MEDIA_TYPES[path.rsplit(".", 1)[1]]


# ---- signed media links for the native apps (5.5) -------------------------------------------

MEDIA_TOKEN_S = 4 * 3600


def _media_sig(ctx: Ctx, asset_id: uuid.UUID, exp: int) -> str:
    key = ctx.settings.secret_key.get_secret_value().encode()
    return hmac.new(key, f"media:{asset_id}:{exp}".encode(), hashlib.sha256).hexdigest()[:32]


async def media_token(ctx: Ctx, asset_id: uuid.UUID) -> dict[str, object]:
    """A path token for players that cannot send auth headers to HLS segments (native apps).
    Issued only to someone who may watch the video; valid for four hours."""
    asset = await get_asset(ctx, asset_id)
    exp = int(datetime.now(UTC).timestamp()) + MEDIA_TOKEN_S
    token = f"{exp}.{_media_sig(ctx, asset.id, exp)}"
    return {"base": f"/v1/media/{asset.id}/{token}/", "expires_at": exp}


async def read_signed_media(
    ctx: Ctx, asset_id: uuid.UUID, token: str, path: str
) -> tuple[bytes, str]:
    exp_s, _, sig = token.partition(".")
    if not exp_s.isdigit() or int(exp_s) < datetime.now(UTC).timestamp():
        raise ProblemError(404, "not-found", "Not found")
    if not hmac.compare_digest(sig, _media_sig(ctx, asset_id, int(exp_s))):
        raise ProblemError(404, "not-found", "Not found")
    await enable_system_access(ctx.db, reason="signed media")
    asset = await ctx.db.get(VideoAsset, asset_id)
    await disable_system_access(ctx.db)
    if asset is None:
        raise ProblemError(404, "not-found", "Not found")
    return await read_media_object(ctx, asset, path)


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


def _elapsed_seconds(result: dict[str, Any]) -> float:
    """Run time of a job from its result (`elapsed_s`), 0 when missing or not a number."""
    value = result.get("elapsed_s")
    if isinstance(value, bool) or not isinstance(value, int | float):
        return 0.0
    return max(0.0, float(value))


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
    elif job.kind == "analysis" and data.status == JobStatus.SUCCEEDED and data.result:
        # the analysis worker reports its run time as `elapsed_s`; that is what billing counts
        job.gpu_seconds = _elapsed_seconds(data.result)
    if data.cost_chf is not None:
        job.cost_chf = data.cost_chf
    asset = await ctx.db.get(VideoAsset, job.video_asset_id) if job.video_asset_id else None
    match = await ctx.db.get(Match, job.match_id)
    if data.status in (JobStatus.SUCCEEDED, JobStatus.FAILED):
        job.finished_at = now
        job.error = data.error
    if asset is not None and match is not None:
        if data.status == JobStatus.FAILED and job.kind == "analysis":
            # the video stays playable (tagging and imports still work); the match is credited
            match.quota_credit = True
            await _tell_staff(ctx, match, "analysis_failed", {"reason": failure_code(data.error)})
        elif data.status == JobStatus.FAILED and job.kind == "sync":
            pass  # the camera stays usable with a manual offset
        elif data.status == JobStatus.FAILED:
            asset.status = VideoStatus.FAILED
            asset.error = data.error
            match.status = MatchStatus.FAILED
            if job.kind in ("ingest", "import"):
                # what failed, with the match's name and the way out (UX test B29)
                await _tell_staff(ctx, match, "video_failed", {})
        elif data.status == JobStatus.SUCCEEDED and job.kind == "import" and data.result:
            asset.size_bytes = int(data.result.get("size_bytes", 0))
            asset.status = VideoStatus.UPLOADED
            await start_ingest(ctx, asset)
        elif data.status == JobStatus.SUCCEEDED and job.kind == "ingest" and data.result:
            _apply_ingest_result(asset, data.result)
            match.status = MatchStatus.READY
            if asset.role == VideoRole.MAIN:
                await segments.rebuild(ctx, match)
            if (
                asset.role == VideoRole.MAIN
                and asset.proxy_key
                and await billing.analysis_allowed(ctx, match.organization_id)
            ):
                await start_analysis(ctx, asset, match)
            await _sync_after_ingest(ctx, asset)
        elif data.status == JobStatus.SUCCEEDED and job.kind == "analysis" and data.result:
            on_timeline = await _apply_analysis_result(ctx, asset, job, data.result)
            kind, extra = await _ready_note(ctx, match)
            await _tell_staff(ctx, match, kind, extra)
            if on_timeline:
                await feed.generate(ctx, match)  # "Deine Szenen" right after the analysis (4.7)
                from handball_api.services import highlights  # imports this module (media paths)

                await highlights.auto(ctx, match)  # reels right after the analysis (4.3)
        elif data.status == JobStatus.SUCCEEDED and job.kind == "sync" and data.result:
            _apply_sync_result(asset, data.result)
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
    asset.recorded_at = parse_recorded(r.get("recorded_at"))
    report = r.get("quality_report")
    asset.quality_report = report if isinstance(report, dict) else None
    audio = r.get("audio_key")
    asset.sync = {**(asset.sync or {}), "audio_key": str(audio) if audio else None}


# ---- analysis (stages 2 to 5) ---------------------------------------------------------------


async def start_analysis(
    ctx: Ctx,
    asset: VideoAsset,
    match: Match,
    points: list[dict[str, Any]] | None = None,
    space: str = "frame",
    frame_ms: int = 0,
) -> ProcessingJob:
    job = await _new_job(ctx, asset, "analysis")
    meta = dict(asset.analysis or {})
    if points is not None:
        # remembered with the job: stored as the video's court points once the run succeeds
        meta[PENDING] = {
            "job_id": str(job.id),
            "points": points,
            "space": space,
            "frame_ms": frame_ms,
        }
        asset.analysis = meta
    elif isinstance(meta.get(CLICKED), dict):
        # a re-run (reprocess, retry) keeps the court the coach clicked: without it a flat view
        # fails the automatic court again and the run would drop the tracks and identities
        clicked = meta[CLICKED]
        points, space, frame_ms = clicked["points"], clicked["space"], int(clicked["frame_ms"])
    refs: list[dict[str, Any]] = []
    if points is None:
        # the court clicked or confirmed on an earlier video of the same hall: the worker tries
        # to carry it over before the automatic court
        refs = await halls.references(ctx, asset, (await halls.hall_of(ctx, match))[0])
    payload: dict[str, object] = {
        "job_id": str(job.id),
        "organization_id": str(asset.organization_id),
        "match_id": str(asset.match_id),
        "asset_id": str(asset.id),
        "bucket": ctx.settings.s3_bucket_videos,
        "proxy_key": asset.proxy_key,
        "prefix": media_prefix(asset),
        "kits": analysis_kits(
            {
                "own": match.kit_own,
                "own_gk": match.kit_own_gk,
                # only a colour somebody said: the column's default red is no knowledge (E09)
                "opponent": match.opponent_kit,
                "opponent_gk": match.kit_opponent_gk if match.opponent_kit else None,
                "referee": match.kit_referee,
            }
        ),
        "calibration_points": points,
        "calibration_space": space,
        "calibration_frame_ms": frame_ms,
        "own_is_home": match.is_home,  # the overlay shows the home team on the left
    }
    rosters = await _rosters(ctx, match)
    if rosters:
        payload["rosters"] = rosters
    if refs:
        payload["hall_references"] = refs
    await ctx.enqueue(
        "gpu",
        ANALYSIS_FUNC,
        str(job.id),
        payload,
        timeout_s=job_budget_s("analysis", duration_s=asset.duration_s),
    )
    return job


async def _rosters(ctx: Ctx, match: Match) -> dict[str, list[int]]:
    """Shirt numbers per kit label for the number vote of the analysis. The labels follow the
    kits in the job payload, so "home" is always the own kit (match.is_home only moves the
    overlay); the opponent side only when its players were entered. Empty sides are left out."""
    out: dict[str, list[int]] = {}
    own = sorted(await roster_numbers(ctx, match.season_id, match.team_id))
    if own:
        out["home"] = own
    if match.opponent_id is not None:
        opp = sorted(
            (
                await ctx.db.scalars(
                    select(OpponentPlayer.number).where(
                        OpponentPlayer.opponent_id == match.opponent_id
                    )
                )
            ).all()
        )
        if opp:
            out["away"] = opp
    return out


async def _apply_analysis_result(
    ctx: Ctx, asset: VideoAsset, job: ProcessingJob, r: dict[str, object]
) -> bool:
    """Stores the results; True when they are the match's (the video is its timeline video).

    Tracks and the court belong to the video. Events, possessions, the match clock and goal
    candidates are the match's: only the timeline video sets them (a second file of the match, e.g.
    the second half, must not replace the first file's events with times in another video)."""
    timeline = await timeline_video(ctx, asset.match_id)
    on_timeline = asset.role == VideoRole.MAIN and timeline is not None and timeline.id == asset.id
    cal = r.get("calibration")
    before = dict(asset.analysis or {})
    pending = before.get(PENDING) if isinstance(before.get(PENDING), dict) else None
    clicked = before.get(CLICKED) if isinstance(before.get(CLICKED), dict) else None
    if pending is not None and pending.get("job_id") == str(job.id):
        if isinstance(cal, dict) and cal.get("source") == "user_correction":
            clicked = {k: pending[k] for k in ("points", "space", "frame_ms")}
        pending = None
    if isinstance(cal, dict):
        ctx.db.add(
            CameraCalibration(
                organization_id=asset.organization_id,
                video_asset_id=asset.id,
                homography=cal["homography"],
                image_size=cal["image_size"],
                confidence=float(cal["confidence"]),
                reprojection_px=float(cal["reprojection_px"]),
                source=str(cal["source"]),
                points=clicked["points"]
                if clicked and cal.get("source") == "user_correction"
                else None,
                pipeline_version=job.pipeline_version,
            )
        )
    # manual identities survive a re-run: carried over to the new track that covers the same time
    previous = [
        (t.team, t.first_ms, t.last_ms, t.player_id, t.number)
        for t in (
            await ctx.db.scalars(
                select(Track).where(
                    Track.video_asset_id == asset.id, Track.identity_source == "user_correction"
                )
            )
        ).all()
    ]
    await ctx.db.execute(delete(Track).where(Track.video_asset_id == asset.id))
    tracks = r.get("tracks")
    detector = str(r.get("detector") or "heuristic")
    # own players by shirt number (read or recognised by the analysis): "home" is the own kit
    roster: dict[int, uuid.UUID] = {}
    if isinstance(tracks, list) and any(t.get("number") is not None for t in tracks):
        owner = await ctx.db.get(Match, asset.match_id)
        if owner is not None and owner.season_id is not None:
            roster = await roster_numbers(ctx, owner.season_id, owner.team_id)
    if isinstance(tracks, list):
        for t in tracks:
            first, last = int(t["first_ms"]), int(t["last_ms"])
            track = Track(
                organization_id=asset.organization_id,
                match_id=asset.match_id,
                video_asset_id=asset.id,
                track_no=int(t["track_id"]),
                team=t.get("team"),
                team_confidence=t.get("team_confidence"),
                first_ms=first,
                last_ms=last,
                observed_share=float(t["observed_share"]),
                physical=t.get("physical"),
                number=t.get("number"),
                identity_source="model" if t.get("number") is not None else None,
                source=detector,
                pipeline_version=job.pipeline_version,
            )
            if track.number is not None and str(track.team or "").startswith("home"):
                track.player_id = roster.get(track.number)
                if track.player_id is not None:
                    track.player_confidence = float(t.get("number_confidence") or 0.6)
            for team, f0, l0, pid, num in previous:
                shared = min(last, l0) - max(first, f0)
                if team == track.team and shared > 0.8 * max(1, last - first):
                    track.player_id, track.number = pid, num
                    track.identity_source, track.player_confidence = "user_correction", 1.0
                    break
            ctx.db.add(track)
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
            "formations",
            "camera",
            "panorama",
            "needs_calibration",
            "calibration_error",
            "calibration_info",
            "scoreboard",
        )
    }
    if clicked is not None:
        asset.analysis[CLICKED] = clicked
    if pending is not None:  # a newer run with clicked points is still running
        asset.analysis[PENDING] = pending
    auto = r.get("events")
    sb_raw = r.get("scoreboard")
    overlay: dict[str, Any] | None = sb_raw if isinstance(sb_raw, dict) else None
    if isinstance(auto, dict) or overlay:
        auto = auto if isinstance(auto, dict) else {}
        match = await ctx.db.get(Match, asset.match_id)
        if match is not None and on_timeline:
            counts = await auto_events.apply(ctx, match, auto or None, overlay)
            # courtside marks with device time follow the new goals (5.3)
            from handball_api.services import marks

            await marks.sync_match(ctx, match.id, authorised=True)
            # goals marked by hand get their shot position from the tracking
            from handball_api.services import shot_positions

            await shot_positions.fill(ctx, match)
            asset.analysis = {
                **asset.analysis,
                "auto_events": {
                    **counts,
                    "sides": auto.get("sides") or [],
                    "missing": auto.get("missing") or [],
                    "boundaries": [
                        {
                            "t_ms": e["t_ms"],
                            "pause_ms": e.get("pause_ms"),
                            "confidence": e.get("confidence"),
                        }
                        for e in auto.get("events") or []
                        if e.get("type") == "match_boundary"
                    ],
                },
            }
    if "goal_candidates" in r and on_timeline:
        # moments that are probably goals, for the coach to confirm (needs no court, so also
        # when the analysis waits for court points); after the automatic events: their
        # possessions suggest the side
        from handball_api.services import goal_candidates

        owner = await ctx.db.get(Match, asset.match_id)
        found = r.get("goal_candidates")
        if owner is not None:
            counts = await goal_candidates.store(
                ctx, owner, asset, found if isinstance(found, dict) else None, job.pipeline_version
            )
            asset.analysis = {**asset.analysis, "goal_candidates": counts}
    return on_timeline


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
    match = await ctx.db.get(Match, asset.match_id)
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
        "formations": meta.get("formations") or [],
        "auto_events": meta.get("auto_events"),
        "error": job.error if job is not None and job.status == "failed" else None,
        "camera": meta.get("camera"),
        "panorama": meta.get("panorama"),
        "needs_calibration": bool(meta.get("needs_calibration")),
        "calibration_error": meta.get("calibration_error"),
        "calibration_info": meta.get("calibration_info"),
        "hall": await halls.summary(ctx, asset, match) if match is not None else None,
        "error_code": failure_code(job.error)
        if job is not None and job.status == "failed"
        else None,
    }


async def read_panorama(ctx: Ctx, asset_id: uuid.UUID) -> bytes:
    """The hall image of the last analysis (panorama of a moving camera, median frame of a fixed
    one): what users mark court points on."""
    asset = await get_asset(ctx, asset_id)
    if not (asset.analysis or {}).get("panorama"):
        raise ProblemError(404, "not-found", "No hall image for this video")
    try:
        data, _ = await ctx.storage.get(
            ctx.settings.s3_bucket_artifacts, f"{media_prefix(asset)}analysis/panorama.jpg"
        )
    except ObjectNotFoundError as exc:
        raise ProblemError(404, "not-found", "No hall image for this video") from exc
    return data


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
    ctx: Ctx,
    asset_id: uuid.UUID,
    points: list[dict[str, Any]],
    space: str = "frame",
    frame_ms: int = 0,
) -> ProcessingJob:
    """Store clicked correspondences and re-run the analysis with them (source user_correction).

    `space`: "frame" = points in the video frame at `frame_ms`, "panorama" = points on the hall
    image of the last analysis (needed for moving cameras, where one frame shows only part of it).
    """
    asset = await get_asset(ctx, asset_id, Action.VIDEO_UPLOAD)
    if asset.status != VideoStatus.READY or not asset.proxy_key:
        raise ProblemError(409, "video-not-ready", "The video is still being processed")
    if space == "panorama" and not (asset.analysis or {}).get("panorama"):
        raise ProblemError(409, "no-hall-image", "Run the analysis first to get the hall image")
    match = await ctx.db.get(Match, asset.match_id)
    assert match is not None
    await audit.record(
        ctx,
        "video.calibrated_manually",
        target_type="video",
        target_id=asset.id,
        data={"points": len(points), "space": space},
    )
    return await start_analysis(ctx, asset, match, points, space, frame_ms)


async def confirm_calibration(ctx: Ctx, asset_id: uuid.UUID) -> CameraCalibration:
    """A person checked the automatic court on the hall image and it fits: the same homography is
    stored again as a user correction (no re-run needed; analysis results stay valid)."""
    asset = await get_asset(ctx, asset_id, Action.VIDEO_UPLOAD)
    latest = await ctx.db.scalar(
        select(CameraCalibration)
        .where(CameraCalibration.video_asset_id == asset.id)
        .order_by(CameraCalibration.created_at.desc())
        .limit(1)
    )
    if latest is None:
        raise ProblemError(409, "no-calibration", "There is no court to confirm yet")
    if latest.source == "user_correction":
        return latest
    confirmed = CameraCalibration(
        organization_id=asset.organization_id,
        video_asset_id=asset.id,
        homography=latest.homography,
        image_size=latest.image_size,
        confidence=1.0,
        reprojection_px=latest.reprojection_px,
        source="user_correction",
        points=None,
        pipeline_version=latest.pipeline_version,
    )
    ctx.db.add(confirmed)
    await audit.record(ctx, "video.calibration_confirmed", target_type="video", target_id=asset.id)
    await ctx.db.flush()
    return confirmed


# ---- identities and physical load (M5) ------------------------------------------------------


async def set_track_identity(
    ctx: Ctx, asset_id: uuid.UUID, track_no: int, player_id: uuid.UUID | None, number: int | None
) -> Track:
    asset = await get_asset(ctx, asset_id, Action.EVENT_WRITE)
    track = await ctx.db.scalar(
        select(Track).where(Track.video_asset_id == asset.id, Track.track_no == track_no)
    )
    if track is None:
        raise ProblemError(404, "not-found", "Track not found")
    if player_id is not None:
        match = await ctx.db.get(Match, asset.match_id)
        assert match is not None
        entry = await ctx.db.scalar(
            select(RosterEntry).where(
                RosterEntry.season_id == match.season_id, RosterEntry.player_id == player_id
            )
        )
        if entry is None:
            raise ProblemError(422, "validation", "The player is not in this season's roster")
        if number is None:
            number = entry.jersey_number
    track.player_id, track.number = player_id, number
    cleared = player_id is None and number is None
    track.identity_source = None if cleared else "user_correction"
    track.player_confidence = None if cleared else 1.0
    await audit.record(
        ctx,
        "track.identity_set",
        target_type="video",
        target_id=asset.id,
        data={"track": track_no, "player_id": str(player_id) if player_id else None},
    )
    return track


BANDS = ("walk", "jog", "run", "sprint")


def _merge_physical(items: list[dict[str, object]]) -> dict[str, object]:
    """Sum of track fragments of one player (same rules as handball_vision.physical.merge)."""

    def f(d: dict[str, object], k: str) -> float:
        v = d.get(k)
        return float(v) if isinstance(v, int | float) else 0.0

    total = sum(f(p, "duration_s") for p in items) or 1.0
    heat: list[list[float]] = []
    for p in items:
        grid = p.get("heatmap")
        if not isinstance(grid, list) or not grid:
            continue
        w = f(p, "duration_s") / total
        if not heat:
            heat = [[0.0] * len(row) for row in grid]
        for r, row in enumerate(grid):
            for c, v in enumerate(row):
                heat[r][c] += float(v) * w
    bands: dict[str, float] = dict.fromkeys(BANDS, 0.0)
    for p in items:
        b = p.get("band_distance_m")
        if isinstance(b, dict):
            for k in BANDS:
                bands[k] += float(b.get(k, 0.0))
    return {
        "distance_m": round(sum(f(p, "distance_m") for p in items), 1),
        "duration_s": round(sum(f(p, "duration_s") for p in items), 1),
        "max_speed_ms": round(max((f(p, "max_speed_ms") for p in items), default=0.0), 2),
        "sprints": int(sum(f(p, "sprints") for p in items)),
        "band_distance_m": {k: round(v, 1) for k, v in bands.items()},
        "heatmap": [[round(v, 4) for v in row] for row in heat],
    }


async def match_physical(ctx: Ctx, match_id: uuid.UUID) -> dict[str, object]:
    """Physical load per identified player and per unidentified track of the main video."""
    match = await get_match(ctx, match_id)
    main = await ctx.db.scalar(
        select(VideoAsset).where(
            VideoAsset.match_id == match.id,
            VideoAsset.role == VideoRole.MAIN,
            VideoAsset.status == VideoStatus.READY,
        )
    )
    if main is None:
        return {"video_id": None, "players": [], "tracks": [], "estimated": True}
    tracks = (
        await ctx.db.scalars(
            select(Track).where(Track.video_asset_id == main.id).order_by(Track.track_no)
        )
    ).all()
    by_player: dict[uuid.UUID, list[Track]] = {}
    loose = []
    for t in tracks:
        if t.team == "referee" or not t.physical:
            continue
        if t.player_id is not None:
            by_player.setdefault(t.player_id, []).append(t)
        else:
            loose.append(t)
    players = [
        {
            "player_id": str(pid),
            "number": ts[0].number,
            "team": ts[0].team,
            "tracks": [t.track_no for t in ts],
            **_merge_physical([t.physical for t in ts if t.physical]),
        }
        for pid, ts in by_player.items()
    ]
    players.sort(key=lambda p: -float(p["distance_m"]))  # type: ignore[arg-type]
    return {
        "video_id": str(main.id),
        "players": players,
        "tracks": [
            {
                "track_no": t.track_no,
                "team": t.team,
                "number": t.number,
                "first_ms": t.first_ms,
                "last_ms": t.last_ms,
                **_merge_physical([t.physical] if t.physical else []),
            }
            for t in loose
        ],
        "estimated": True,
    }
