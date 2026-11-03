"""Operator backoffice (M8): platform-wide overview, organisations, failed jobs, support actions.

Operators are configured by e-mail (`HB_OPERATOR_EMAILS`). Every read bypasses tenant isolation on
purpose, so each call is audited; support actions are audited with their before/after values.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select

from handball_api.core.db import enable_system_access
from handball_api.core.errors import ProblemError
from handball_api.models import (
    Match,
    Organization,
    OrgMembership,
    ProcessingJob,
    Team,
    User,
    VideoAsset,
)
from handball_api.models.enums import JobStatus, Plan
from handball_api.services import audit, videos
from handball_api.services.context import Ctx


def is_operator(ctx: Ctx, user: User) -> bool:
    allowed = {e.strip().lower() for e in ctx.settings.operator_emails if e.strip()}
    email = user.email.lower()
    domain = "@" + email.rsplit("@", 1)[-1]
    # entries are full addresses or a whole domain ("@example.ch")
    if email not in allowed and domain not in allowed:
        return False
    # operators must use two-factor sign-in outside development
    return ctx.settings.env not in ("staging", "production") or user.totp_secret_enc is not None


async def _system(ctx: Ctx, reason: str) -> None:
    await enable_system_access(ctx.db, reason=reason)
    await audit.record(ctx, "ops.access", data={"reason": reason})


async def overview(ctx: Ctx) -> dict[str, Any]:
    await _system(ctx, "ops overview")
    since = datetime.now(UTC) - timedelta(hours=24)

    async def count(model: Any) -> int:
        return int(await ctx.db.scalar(select(func.count(model.id))) or 0)

    jobs = (
        await ctx.db.execute(
            select(ProcessingJob.kind, ProcessingJob.status, func.count(ProcessingJob.id))
            .where(ProcessingJob.created_at >= since)
            .group_by(ProcessingJob.kind, ProcessingJob.status)
        )
    ).all()
    plans = (
        await ctx.db.execute(
            select(Organization.plan, func.count(Organization.id)).group_by(Organization.plan)
        )
    ).all()
    gpu = await ctx.db.scalar(
        select(func.coalesce(func.sum(ProcessingJob.gpu_seconds), 0)).where(
            ProcessingJob.created_at >= since
        )
    )
    return {
        "organizations": await count(Organization),
        "users": await count(User),
        "teams": await count(Team),
        "matches": await count(Match),
        "videos": await count(VideoAsset),
        "storage_bytes": int(
            await ctx.db.scalar(select(func.coalesce(func.sum(VideoAsset.size_bytes), 0))) or 0
        ),
        "jobs_24h": [{"kind": k, "status": s.value, "count": n} for k, s, n in jobs],
        "gpu_minutes_24h": round(float(gpu or 0) / 60, 1),
        "plans": {p.value: n for p, n in plans},
        "failed_jobs": await failed_jobs(ctx, limit=20, audited=False),
    }


async def failed_jobs(ctx: Ctx, limit: int = 50, audited: bool = True) -> list[dict[str, Any]]:
    if audited:
        await _system(ctx, "ops failed jobs")
    rows = (
        await ctx.db.execute(
            select(ProcessingJob, Organization.name)
            .join(Organization, Organization.id == ProcessingJob.organization_id)
            .where(ProcessingJob.status == JobStatus.FAILED)
            .order_by(ProcessingJob.created_at.desc())
            .limit(limit)
        )
    ).all()
    return [
        {
            "id": str(j.id),
            "kind": j.kind,
            "organization": name,
            "organization_id": str(j.organization_id),
            "match_id": str(j.match_id),
            "video_asset_id": str(j.video_asset_id) if j.video_asset_id else None,
            "error": j.error,
            "created_at": j.created_at.isoformat(),
            "pipeline_version": j.pipeline_version,
        }
        for j, name in rows
    ]


async def organizations(ctx: Ctx, q: str | None) -> list[dict[str, Any]]:
    await _system(ctx, "ops organisations")
    stmt = select(Organization).order_by(Organization.created_at.desc()).limit(200)
    if q:
        stmt = stmt.where(Organization.name.ilike(f"%{q}%"))
    orgs = list((await ctx.db.scalars(stmt)).all())
    ids = [o.id for o in orgs]

    async def per_org(model: Any, col: Any = None) -> dict[uuid.UUID, int]:
        expr = func.count(model.id) if col is None else func.coalesce(func.sum(col), 0)
        rows = (
            await ctx.db.execute(
                select(model.organization_id, expr)
                .where(model.organization_id.in_(ids))
                .group_by(model.organization_id)
            )
        ).all()
        return {o: int(n) for o, n in rows}

    teams = await per_org(Team)
    members = await per_org(OrgMembership)
    matches = await per_org(Match)
    storage = await per_org(VideoAsset, VideoAsset.size_bytes)
    return [
        {
            "id": str(o.id),
            "name": o.name,
            "plan": o.plan.value,
            "status": o.subscription_status,
            "trial_ends_at": o.trial_ends_at.isoformat() if o.trial_ends_at else None,
            "created_at": o.created_at.isoformat(),
            "teams": teams.get(o.id, 0),
            "members": members.get(o.id, 0),
            "matches": matches.get(o.id, 0),
            "storage_bytes": storage.get(o.id, 0),
        }
        for o in orgs
    ]


async def extend_trial(ctx: Ctx, org_id: uuid.UUID, plan: Plan, days: int) -> dict[str, Any]:
    """Support action: grant or extend a trial of a paid plan."""
    await _system(ctx, "ops extend trial")
    org = await ctx.db.get(Organization, org_id)
    if org is None:
        raise ProblemError(404, "not-found", "Organisation not found")
    before = {"plan": org.plan.value, "trial_ends_at": str(org.trial_ends_at)}
    start = max(datetime.now(UTC), org.trial_ends_at or datetime.now(UTC))
    org.plan = plan
    org.trial_ends_at = start + timedelta(days=days)
    org.trial_used = True
    await audit.record(
        ctx,
        "ops.trial_extended",
        org_id=org.id,
        target_type="organization",
        target_id=org.id,
        data={"before": before, "plan": plan.value, "days": days},
    )
    return {"plan": org.plan.value, "trial_ends_at": org.trial_ends_at.isoformat()}


async def retry_job(ctx: Ctx, job_id: uuid.UUID) -> dict[str, str]:
    await _system(ctx, "ops retry job")
    job = await ctx.db.get(ProcessingJob, job_id)
    if (
        job is None
        or job.video_asset_id is None
        or job.status != JobStatus.FAILED
        or "retried_as" in (job.stages or {})
    ):
        raise ProblemError(409, "not-retryable", "Only failed video jobs can be retried")
    asset = await ctx.db.get(VideoAsset, job.video_asset_id)
    match = await ctx.db.get(Match, job.match_id)
    if asset is None or match is None:
        raise ProblemError(404, "not-found", "Video not found")
    if job.kind == "analysis":
        new = await videos.start_analysis(ctx, asset, match)
    else:
        new = await videos.start_ingest(ctx, asset)
    job.stages = {**(job.stages or {}), "retried_as": str(new.id)}
    await audit.record(
        ctx, "ops.job_retried", org_id=job.organization_id, target_type="job", target_id=job.id
    )
    return {"job_id": str(new.id), "kind": new.kind}
