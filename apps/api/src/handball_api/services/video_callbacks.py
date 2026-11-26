"""Worker callbacks (internal): the job's progress and its end, handled per job kind."""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select

from handball_api.core.db import set_tenant, system_access
from handball_api.core.email import try_send
from handball_api.core.errors import ProblemError
from handball_api.core.logging import get_logger
from handball_api.models import Event, Match, Opponent, ProcessingJob, Team, User, VideoAsset
from handball_api.models.enums import JobStatus, MatchStatus, VideoRole, VideoStatus
from handball_api.schemas.matches import JobUpdate
from handball_api.services import billing, feed, highlights, progress, timeline, training
from handball_api.services.context import Ctx
from handball_api.services.graphics import open_checks
from handball_api.services.mail_templates import render
from handball_api.services.matches import DUPLICATE, parts_of
from handball_api.services.support import failure_code
from handball_api.services.video_analysis import (
    _apply_analysis_result,
    start_analysis,
    start_waiting,
    store_view,
)
from handball_api.services.video_base import PENDING
from handball_api.services.video_jobs import (
    _apply_ingest_result,
    _apply_sync_result,
    _elapsed_seconds,
    _same_file,
    _sync_after_ingest,
    job_event,
    start_ingest,
)

THREE_THINGS_MIN_GOALS = 3  # fewer goals in the video carry no three things

log = get_logger("handball_api.jobs")


async def _tell_staff(ctx: Ctx, match: Match, kind: str, extra: dict[str, Any]) -> None:
    """A note in the bell and an e-mail to the team's coaches and analysts, naming the match
    (UX test H06, B29): on the phone the bell alone is easy to miss."""
    team = await ctx.db.get(Team, match.team_id)
    opp = await ctx.db.get(Opponent, match.opponent_id) if match.opponent_id else None
    opponent = opp.name if opp else "Training"
    link = f"/app/{match.organization_id}/matches/{match.id}"
    # the link leads to the next step: questions wait in Prüfen (real-video test, second round)
    if kind == "analysis_questions":
        link += "/check"
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
                **{k: v for k, v in extra.items() if k in ("questions", "more_moments")},
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
    # the budget of the main round only (second round A6): «Mehr prüfen» is never promised
    questions = len(await open_checks(ctx, match))
    more = 0
    return ("analysis_questions" if questions else "analysis_no_goals"), {
        "questions": questions,
        "more_moments": more,
    }


async def apply_job_update(ctx: Ctx, job_id: uuid.UUID, data: JobUpdate) -> ProcessingJob:
    async with system_access(ctx.db, reason="worker job callback"):
        # locked: court points marked while it runs are handed over against its court stage
        job = await ctx.db.get(ProcessingJob, job_id, with_for_update=True)
    if job is None:
        raise ProblemError(404, "not-found", "Job not found")
    await set_tenant(ctx.db, job.organization_id)
    now = datetime.now(UTC)
    if job.status in (JobStatus.SUCCEEDED, JobStatus.CANCELLED):
        return job  # late or duplicate callbacks are ignored (idempotent)
    if (
        data.status == JobStatus.FAILED
        and (data.error or "").startswith(progress.WORKER_LOST)
        and job.status == JobStatus.RUNNING
    ):
        # the worker reports a killed work horse (out of memory): restarted once at once,
        # ended as failed the second time, not left «running» until the watchdog notices
        await progress.restart_or_fail(ctx, job, datetime.now(UTC), f"({data.error})")
        return job
    if job.started_at is None and data.status != JobStatus.QUEUED:
        job.started_at = now
    # every report (progress, heartbeat, the end) says the worker is still on it
    job.heartbeat_at = now
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
    if data.status == JobStatus.FAILED:
        # one line per failed job: the alert «job failures» (infra/terraform/azure) counts it
        log.warning("job_failed", job=str(job.id), kind=job.kind, reason=failure_code(data.error))
    if (
        asset is not None
        and data.view is not None
        and job.kind == "analysis"
        and data.status == JobStatus.RUNNING
    ):
        store_view(asset, job, data.view)
    if asset is not None and match is not None:
        if data.status == JobStatus.FAILED:
            await ON_FAILED.get(job.kind, _file_failed)(ctx, job, asset, match, data.error)
        elif data.status == JobStatus.SUCCEEDED and data.result:
            succeeded = ON_SUCCEEDED.get(job.kind)
            if succeeded is not None:
                await succeeded(ctx, job, asset, match, data.result)
    if (
        match is not None
        and job.kind == "analysis"
        and data.status in (JobStatus.SUCCEEDED, JobStatus.FAILED)
    ):
        await ctx.db.flush()
        await start_waiting(ctx, match)
    await ctx.db.flush()
    await ctx.require_events().publish(f"match:{job.match_id}", job_event(job))
    return job


# ---- the end of a job, per job kind ----------------------------------------------------------


async def _analysis_failed(
    ctx: Ctx, job: ProcessingJob, asset: VideoAsset, match: Match, error: str | None
) -> None:
    # the video stays playable (tagging and imports still work); the match is credited
    match.quota_credit = True
    await _tell_staff(ctx, match, "analysis_failed", {"reason": failure_code(error)})


async def _sync_failed(
    ctx: Ctx, job: ProcessingJob, asset: VideoAsset, match: Match, error: str | None
) -> None:
    pass  # the camera stays usable with a manual offset


async def _file_failed(
    ctx: Ctx, job: ProcessingJob, asset: VideoAsset, match: Match, error: str | None
) -> None:
    """Any other job kind (ingest, import): the file failed."""
    before = await parts_of(ctx, match.id)
    asset.status = VideoStatus.FAILED
    asset.error = error
    if any(p.video_id == asset.id for p in before):
        await ctx.db.flush()
        await timeline.settle(ctx, match, before)
    # another part still plays: the match stays usable
    match.status = (
        MatchStatus.READY
        if before and any(p.video_id != asset.id and p.status == VideoStatus.READY for p in before)
        else MatchStatus.FAILED
    )
    if job.kind in ("ingest", "import"):
        # what failed, with the match's name and the way out (UX test B29)
        await _tell_staff(ctx, match, "video_failed", {})


async def _import_succeeded(
    ctx: Ctx, job: ProcessingJob, asset: VideoAsset, match: Match, r: dict[str, Any]
) -> None:
    asset.size_bytes = int(r.get("size_bytes", 0))
    asset.status = VideoStatus.UPLOADED
    await start_ingest(ctx, asset)


async def _ingest_succeeded(
    ctx: Ctx, job: ProcessingJob, asset: VideoAsset, match: Match, r: dict[str, Any]
) -> None:
    before = await parts_of(ctx, match.id)
    _apply_ingest_result(asset, r)
    twin = await _same_file(ctx, asset)
    if twin is not None:
        # the same file a second time (another name, a copy): not a part of the match
        asset.status = VideoStatus.FAILED
        asset.error = f"{DUPLICATE}{twin}"
        await ctx.db.flush()
        if any(p.video_id == asset.id for p in before):
            await timeline.settle(ctx, match, before)
        return
    match.status = MatchStatus.READY
    if asset.role == VideoRole.MAIN:
        await ctx.db.flush()
        await timeline.settle(ctx, match, before)
    if (
        asset.role == VideoRole.MAIN
        and asset.proxy_key
        and await billing.analysis_allowed(ctx, match.organization_id)
    ):
        await start_analysis(ctx, asset, match)
    await _sync_after_ingest(ctx, asset)


async def _analysis_succeeded(
    ctx: Ctx, job: ProcessingJob, asset: VideoAsset, match: Match, r: dict[str, Any]
) -> None:
    # the run after a court the coach corrected in Prüfen: Prüfen waits for it and asks
    # anew, no second mail and no notice (third real-video test G4)
    raw = (asset.analysis or {}).get(PENDING)
    pending: dict[str, Any] = raw if isinstance(raw, dict) else {}
    mine = pending.get("job_id") == str(job.id)
    cal = r.get("calibration")
    clicked = isinstance(cal, dict) and cal.get("source") == "user_correction"
    # points marked while this run went on: it is still the first analysis (the coach hears
    # about it); a run that did not take them (an older worker, the classical path, points that
    # came as its court stage began) is followed by a run with them on its stored observations
    while_running = mine and bool(pending.get("while_running"))
    corrected = mine and not while_running
    on_timeline = await _apply_analysis_result(ctx, asset, job, r)
    if while_running and not clicked:
        await start_analysis(
            ctx,
            asset,
            match,
            pending["points"],
            str(pending.get("space") or "panorama"),
            int(pending.get("frame_ms") or 0),
        )
    if not corrected:
        kind, extra = await _ready_note(ctx, match)
        await _tell_staff(ctx, match, kind, extra)
    if on_timeline:
        await feed.generate(ctx, match)  # "Deine Szenen" right after the analysis (4.7)
        await highlights.auto(ctx, match)  # reels right after the analysis (4.3)


async def _sync_succeeded(
    ctx: Ctx, job: ProcessingJob, asset: VideoAsset, match: Match, r: dict[str, Any]
) -> None:
    _apply_sync_result(asset, r)


Failed = Callable[[Ctx, ProcessingJob, VideoAsset, Match, str | None], Awaitable[None]]
Succeeded = Callable[[Ctx, ProcessingJob, VideoAsset, Match, dict[str, Any]], Awaitable[None]]
# a failed job of another kind fails its file (_file_failed); a finished job of another kind (or
# one without a result) changes nothing on the file
ON_FAILED: dict[str, Failed] = {"analysis": _analysis_failed, "sync": _sync_failed}
ON_SUCCEEDED: dict[str, Succeeded] = {
    "import": _import_succeeded,
    "ingest": _ingest_succeeded,
    "analysis": _analysis_succeeded,
    "sync": _sync_succeeded,
}
