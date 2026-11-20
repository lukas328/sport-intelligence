"""Video jobs: ingest, sync of further cameras and their budgets; the results of ingest and sync."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select

from handball_api.core.errors import ProblemError
from handball_api.models import Match, ProcessingJob, VideoAsset
from handball_api.models.enums import JobStatus, MatchStatus, VideoRole, VideoStatus
from handball_api.services import audit
from handball_api.services.context import Ctx
from handball_api.services.policies import Action
from handball_api.services.segments import parse_recorded
from handball_api.services.video_base import (
    INGEST_FUNC,
    PIPELINE_VERSION,
    SYNC_FUNC,
    SYNC_MIN_CONFIDENCE,
    get_asset,
)
from handball_api.services.video_media import media_prefix


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
        # another main file is a further part of the match (Q-VIDEO-PARTS), placed one after the
        # other, not a second camera of the same minutes: no sound sync between them
        for other in others:
            if other.role != VideoRole.MAIN:
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


async def _same_file(ctx: Ctx, asset: VideoAsset) -> uuid.UUID | None:
    """Another file of the match with the same content (checksum), not failed."""
    if not asset.checksum_sha256:
        return None
    twin: uuid.UUID | None = await ctx.db.scalar(
        select(VideoAsset.id)
        .where(
            VideoAsset.match_id == asset.match_id,
            VideoAsset.id != asset.id,
            VideoAsset.checksum_sha256 == asset.checksum_sha256,
            VideoAsset.status != VideoStatus.FAILED,
        )
        .order_by(VideoAsset.created_at)
        .limit(1)
    )
    return twin


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
