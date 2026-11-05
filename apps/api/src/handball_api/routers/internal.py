"""Internal endpoints for workers. Not under /v1, never proxied by the web origin."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Header
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from handball_api.core.db import enable_system_access
from handball_api.core.errors import ProblemError
from handball_api.core.security import constant_time_equals
from handball_api.models import ProcessingJob, VideoAsset
from handball_api.models.enums import JobStatus
from handball_api.routers.deps import CtxDep
from handball_api.schemas.matches import JobOut, JobUpdate
from handball_api.services import (
    highlights,
    invoices,
    monitoring,
    official,
    presentations,
    scouting,
    support,
    videos,
)

router = APIRouter(prefix="/internal", include_in_schema=False)


@router.post("/jobs/{job_id}", response_model=JobOut)
async def job_update(
    job_id: uuid.UUID, data: JobUpdate, ctx: CtxDep, x_internal_token: Annotated[str, Header()] = ""
) -> JobOut:
    if not constant_time_equals(x_internal_token, ctx.settings.internal_token.get_secret_value()):
        raise ProblemError(403, "forbidden", "Invalid internal token")
    return JobOut.model_validate(await videos.apply_job_update(ctx, job_id, data))


@router.get("/stats")
async def stats(ctx: CtxDep, x_internal_token: Annotated[str, Header()] = "") -> dict[str, Any]:
    """Operational numbers for alerting probes (queue depths, failed and stuck jobs)."""
    if not constant_time_equals(x_internal_token, ctx.settings.internal_token.get_secret_value()):
        raise ProblemError(403, "forbidden", "Invalid internal token")
    await enable_system_access(ctx.db, reason="alerting probe")
    now = datetime.now(UTC)
    failed = await ctx.db.scalar(
        select(func.count(ProcessingJob.id)).where(
            ProcessingJob.status == JobStatus.FAILED,
            ProcessingJob.finished_at >= now - timedelta(hours=1),
        )
    )
    long_running = (
        await ctx.db.execute(
            select(ProcessingJob, VideoAsset.duration_s, VideoAsset.size_bytes)
            .outerjoin(VideoAsset, VideoAsset.id == ProcessingJob.video_asset_id)
            .where(
                ProcessingJob.status == JobStatus.RUNNING,
                ProcessingJob.started_at < now - timedelta(hours=3),
            )
        )
    ).all()
    stuck = len(long_running)
    # a full game's analysis runs longer than three hours on a CPU worker: stuck only once a job
    # is past the time its worker has for it
    over_budget = sum(
        1
        for job, duration_s, size in long_running
        if job.started_at is not None
        and (now - job.started_at).total_seconds()
        > videos.job_budget_s(job.kind, duration_s=duration_s, size_bytes=size)
    )
    oldest = await ctx.db.scalar(
        select(func.min(ProcessingJob.created_at)).where(ProcessingJob.status == JobStatus.QUEUED)
    )
    return {
        "queues": ctx.require_jobs().depths(),
        "failed_last_hour": int(failed or 0),
        "running_over_3h": stuck,
        "running_over_budget": over_budget,
        "oldest_queued_s": int((now - oldest).total_seconds()) if oldest else 0,
        "metrics": await monitoring.ops_metrics(ctx, now),
        "alerts": await monitoring.alerts(ctx),
    }


@router.post("/scouting/due")
async def scouting_due(
    ctx: CtxDep, x_internal_token: Annotated[str, Header()] = ""
) -> dict[str, int]:
    """Worker tick (hourly): preparation reports 72 h before matches (addendum 01, 4.6)."""
    if not constant_time_equals(x_internal_token, ctx.settings.internal_token.get_secret_value()):
        raise ProblemError(403, "forbidden", "Invalid internal token")
    return {"created": await scouting.run_due(ctx)}


class ExportDone(BaseModel):
    status: str = Field(pattern="^(ready|failed|running)$")
    key: str | None = None
    error: str | None = None


@router.post("/presentations/{pres_id}/export", status_code=204)
async def presentation_export_done(
    pres_id: uuid.UUID,
    data: ExportDone,
    ctx: CtxDep,
    x_internal_token: Annotated[str, Header()] = "",
) -> None:
    if not constant_time_equals(x_internal_token, ctx.settings.internal_token.get_secret_value()):
        raise ProblemError(403, "forbidden", "Invalid internal token")
    await enable_system_access(ctx.db, reason="presentation export callback")
    await presentations.export_done(ctx, pres_id, data.status, data.key, data.error)


class ReelDone(BaseModel):
    status: str = Field(pattern="^(ready|failed|rendering)$")
    key: str | None = None
    error: str | None = None


@router.post("/highlights/{reel_id}", status_code=204)
async def highlight_done(
    reel_id: uuid.UUID, data: ReelDone, ctx: CtxDep, x_internal_token: Annotated[str, Header()] = ""
) -> None:
    if not constant_time_equals(x_internal_token, ctx.settings.internal_token.get_secret_value()):
        raise ProblemError(403, "forbidden", "Invalid internal token")
    await enable_system_access(ctx.db, reason="highlight render callback")
    await highlights.done(ctx, reel_id, data.status, data.key, data.error)


@router.post("/billing/dunning")
async def dunning(ctx: CtxDep, x_internal_token: Annotated[str, Header()] = "") -> dict[str, int]:
    """Worker tick: invoice reminders and final notices (addendum 01, 4.10)."""
    if not constant_time_equals(x_internal_token, ctx.settings.internal_token.get_secret_value()):
        raise ProblemError(403, "forbidden", "Invalid internal token")
    await enable_system_access(ctx.db, reason="dunning run")
    return await invoices.run_dunning(ctx)


@router.post("/onboarding/run")
async def onboarding_run(
    ctx: CtxDep, x_internal_token: Annotated[str, Header()] = ""
) -> dict[str, int]:
    """Worker tick: onboarding e-mail series (addendum 01, 4.11)."""
    if not constant_time_equals(x_internal_token, ctx.settings.internal_token.get_secret_value()):
        raise ProblemError(403, "forbidden", "Invalid internal token")
    await enable_system_access(ctx.db, reason="onboarding e-mail series")
    return {"sent": await support.run_series(ctx)}


@router.post("/ops/tick")
async def ops_tick(ctx: CtxDep, x_internal_token: Annotated[str, Header()] = "") -> dict[str, Any]:
    """Worker tick: status page feed and storage policy for original videos (4.12)."""
    if not constant_time_equals(x_internal_token, ctx.settings.internal_token.get_secret_value()):
        raise ProblemError(403, "forbidden", "Invalid internal token")
    status = await monitoring.push_status(ctx)
    await enable_system_access(ctx.db, reason="storage policy")
    return {
        "status": status,
        "retention": await monitoring.retention(ctx),
        "abandoned_uploads": await monitoring.abandoned_uploads(ctx),
    }


@router.post("/official/sync")
async def official_sync(
    ctx: CtxDep, x_internal_token: Annotated[str, Header()] = ""
) -> dict[str, int]:
    """Worker tick (hourly): each linked team once a day, official reports after the games."""
    if not constant_time_equals(x_internal_token, ctx.settings.internal_token.get_secret_value()):
        raise ProblemError(403, "forbidden", "Invalid internal token")
    return await official.run_due(ctx)
