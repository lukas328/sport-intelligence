"""Operations and measurement (addendum 01, 4.12): alerts, AI quality per week, status page feed,
storage policy for original videos."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from sqlalchemy import func, select

from handball_api.core.logging import get_logger
from handball_api.integrations.support import ExternalStatusPage
from handball_api.models import Correction, Event, OrgMembership, ProcessingJob, VideoAsset
from handball_api.models.enums import JobStatus, OrgRole
from handball_api.services import training
from handball_api.services.context import Ctx
from handball_api.services.health import default_checks, run_checks

log = get_logger("handball_api.monitoring")
AUTO_SOURCES = ("heuristic", "model")
NOTICE_DAYS = 7


async def ops_metrics(ctx: Ctx, now: datetime | None = None) -> dict[str, Any]:
    """Error rate (24 h), analysis duration p95 and cost per analysed match (7 days)."""
    now = now or datetime.now(UTC)
    finished = (
        await ctx.db.execute(
            select(ProcessingJob.status, func.count(ProcessingJob.id))
            .where(ProcessingJob.finished_at >= now - timedelta(hours=24))
            .group_by(ProcessingJob.status)
        )
    ).all()
    counts = {str(s): int(n) for s, n in finished}
    total = sum(counts.values())
    durations = sorted(
        (f - s).total_seconds() / 60
        for s, f in (
            await ctx.db.execute(
                select(ProcessingJob.started_at, ProcessingJob.finished_at).where(
                    ProcessingJob.kind == "analysis",
                    ProcessingJob.status == JobStatus.SUCCEEDED,
                    ProcessingJob.finished_at >= now - timedelta(days=7),
                    ProcessingJob.started_at.is_not(None),
                )
            )
        ).all()
        if s and f
    )
    cost = await ctx.db.scalar(
        select(func.avg(ProcessingJob.cost_chf)).where(
            ProcessingJob.kind == "analysis",
            ProcessingJob.status == JobStatus.SUCCEEDED,
            ProcessingJob.finished_at >= now - timedelta(days=7),
        )
    )
    p95 = durations[min(len(durations) - 1, int(len(durations) * 0.95))] if durations else None
    return {
        "jobs_24h": total,
        "error_rate_24h": round(counts.get(JobStatus.FAILED.value, 0) / total, 3) if total else 0.0,
        "analysis_p95_min": round(p95, 1) if p95 is not None else None,
        "analyses_7d": len(durations),
        "cost_chf_per_match": round(float(cost), 2) if cost is not None else None,
    }


async def quality_weeks(
    ctx: Ctx, weeks: int = 8, now: datetime | None = None
) -> list[dict[str, Any]]:
    """Per ISO week: automatic events, mean confidence, share below 0.6, correction rate."""
    now = now or datetime.now(UTC)
    since = now - timedelta(weeks=weeks)
    events = (
        await ctx.db.execute(
            select(Event.created_at, Event.confidence).where(
                Event.source.in_(AUTO_SOURCES), Event.created_at >= since
            )
        )
    ).all()
    corrections = (
        await ctx.db.execute(
            select(Correction.created_at, Correction.before).where(Correction.created_at >= since)
        )
    ).all()
    per: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"events": 0, "conf_sum": 0.0, "low": 0, "corrected": 0}
    )
    for created, conf in events:
        w = per[f"{created.isocalendar().year}-W{created.isocalendar().week:02d}"]
        w["events"] += 1
        w["conf_sum"] += float(conf)
        w["low"] += 1 if conf < 0.6 else 0
    for created, before in corrections:
        if isinstance(before, dict) and before.get("source") in AUTO_SOURCES:
            per[f"{created.isocalendar().year}-W{created.isocalendar().week:02d}"]["corrected"] += 1
    out = []
    for week in sorted(per):
        w = per[week]
        n = w["events"]  # automatic events still unchanged
        total = n + w["corrected"]  # corrected ones were automatic too
        out.append(
            {
                "week": week,
                "events": total,
                "mean_confidence": round(w["conf_sum"] / n, 3) if n else None,
                "low_confidence_share": round(w["low"] / n, 3) if n else None,
                "correction_rate": round(w["corrected"] / total, 3) if total else None,
            }
        )
    return out


def quality_alert(weeks: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Alarm when the latest week is clearly worse than the four before (new customer videos)."""
    rated = [w for w in weeks if w["events"] >= 20]
    if len(rated) < 3:
        return None
    last, before = rated[-1], rated[-5:-1]
    avg_corr = sum(w["correction_rate"] for w in before) / len(before)
    avg_conf = sum(w["mean_confidence"] for w in before) / len(before)
    if last["correction_rate"] > max(0.1, 1.5 * avg_corr):
        return {
            "key": "ai_corrections",
            "week": last["week"],
            "value": last["correction_rate"],
            "baseline": round(avg_corr, 3),
        }
    if avg_conf - last["mean_confidence"] > 0.1:
        return {
            "key": "ai_confidence",
            "week": last["week"],
            "value": last["mean_confidence"],
            "baseline": round(avg_conf, 3),
        }
    return None


async def alerts(ctx: Ctx) -> list[dict[str, Any]]:
    m = await ops_metrics(ctx)
    s = ctx.settings
    out = []
    if m["jobs_24h"] >= 10 and m["error_rate_24h"] > 0.1:
        out.append({"key": "error_rate", "value": m["error_rate_24h"], "threshold": 0.1})
    if m["analysis_p95_min"] is not None and m["analysis_p95_min"] > s.alert_analysis_minutes:
        out.append(
            {
                "key": "analysis_duration",
                "value": m["analysis_p95_min"],
                "threshold": s.alert_analysis_minutes,
            }
        )
    if m["cost_chf_per_match"] is not None and m["cost_chf_per_match"] > s.alert_cost_chf_per_match:
        out.append(
            {
                "key": "cost_per_match",
                "value": m["cost_chf_per_match"],
                "threshold": s.alert_cost_chf_per_match,
            }
        )
    q = quality_alert(await quality_weeks(ctx))
    if q:
        out.append(q)
    return out


async def push_status(ctx: Ctx, client: httpx.AsyncClient | None = None) -> list[dict[str, str]]:
    """Health checks to the external status page (adapter); no-op without configuration."""
    results = await run_checks(default_checks(ctx.settings), 3.0)
    page = ExternalStatusPage(ctx.settings.status_page_url or "")
    report = [
        {"component": c.component, "status": c.status}
        for c in page.report({r.name: r.status == "ok" for r in results})
    ]
    url = ctx.settings.status_page_push_url
    if url:
        token = ctx.settings.status_page_token
        headers = {"authorization": f"Bearer {token.get_secret_value()}"} if token else {}
        http = client or httpx.AsyncClient(timeout=10)
        try:
            r = await http.post(url, json={"components": report}, headers=headers)
            r.raise_for_status()
        except httpx.HTTPError as exc:
            log.warning("status_push_failed", error=str(exc))
    return report


async def retention(ctx: Ctx, now: datetime | None = None) -> dict[str, int]:
    """Originals older than the configured days are deleted once the compressed versions exist;
    the club admins are told a week before (needs system access)."""
    now = now or datetime.now(UTC)
    days = ctx.settings.raw_video_days
    out = {"notified": 0, "purged": 0}
    soon = (
        await ctx.db.scalars(
            select(VideoAsset).where(
                VideoAsset.created_at <= now - timedelta(days=days - NOTICE_DAYS),
                VideoAsset.purge_notified_at.is_(None),
                VideoAsset.original_purged_at.is_(None),
                VideoAsset.proxy_key.is_not(None),
            )
        )
    ).all()
    by_org: dict[Any, list[VideoAsset]] = defaultdict(list)
    for v in soon:
        by_org[v.organization_id].append(v)
    for org_id, vids in by_org.items():
        admins = list(
            (
                await ctx.db.scalars(
                    select(OrgMembership.user_id).where(
                        OrgMembership.organization_id == org_id,
                        OrgMembership.role == OrgRole.ORG_ADMIN,
                    )
                )
            ).all()
        )
        await training.notify(
            ctx, org_id, admins, "originals_purge", {"count": len(vids), "days": NOTICE_DAYS}, None
        )
        for v in vids:
            v.purge_notified_at = now
        out["notified"] += len(vids)
    due = (
        await ctx.db.scalars(
            select(VideoAsset).where(
                VideoAsset.created_at <= now - timedelta(days=days),
                VideoAsset.purge_notified_at <= now - timedelta(days=NOTICE_DAYS),
                VideoAsset.original_purged_at.is_(None),
                VideoAsset.proxy_key.is_not(None),
                VideoAsset.hls_prefix.is_not(None),
            )
        )
    ).all()
    for v in due:
        try:
            await ctx.storage.delete(ctx.settings.s3_bucket_videos, v.storage_key)
        except Exception as exc:  # already gone: still mark, the compressed versions remain
            log.info("original_missing", video=str(v.id), error=str(exc))
        v.original_purged_at = now
        out["purged"] += 1
    await ctx.db.flush()
    return out
