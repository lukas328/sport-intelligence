"""Internal endpoints for workers. Not under /v1, never proxied by the web origin."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Header
from sqlalchemy import func, select

from handball_api.core.db import enable_system_access
from handball_api.core.errors import ProblemError
from handball_api.core.security import constant_time_equals
from handball_api.models import ProcessingJob
from handball_api.models.enums import JobStatus
from handball_api.routers.deps import CtxDep
from handball_api.schemas.matches import JobOut, JobUpdate
from handball_api.services import scouting, videos

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
    stuck = await ctx.db.scalar(
        select(func.count(ProcessingJob.id)).where(
            ProcessingJob.status == JobStatus.RUNNING,
            ProcessingJob.started_at < now - timedelta(hours=3),
        )
    )
    oldest = await ctx.db.scalar(
        select(func.min(ProcessingJob.created_at)).where(ProcessingJob.status == JobStatus.QUEUED)
    )
    return {
        "queues": ctx.require_jobs().depths(),
        "failed_last_hour": int(failed or 0),
        "running_over_3h": int(stuck or 0),
        "oldest_queued_s": int((now - oldest).total_seconds()) if oldest else 0,
    }


@router.post("/scouting/due")
async def scouting_due(
    ctx: CtxDep, x_internal_token: Annotated[str, Header()] = ""
) -> dict[str, int]:
    """Worker tick (hourly): preparation reports 72 h before matches (addendum 01, 4.6)."""
    if not constant_time_equals(x_internal_token, ctx.settings.internal_token.get_secret_value()):
        raise ProblemError(403, "forbidden", "Invalid internal token")
    return {"created": await scouting.run_due(ctx)}
