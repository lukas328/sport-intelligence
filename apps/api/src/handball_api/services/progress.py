"""How far the uploads and the processing of a match are, honestly (K6, K13, B4).

Per file and step in the coach's words: hochladen (upload), einlesen (ingest: converting for
playback and the analysis), analysieren (analysis), fertig. Each step says how far it is where that
is known, how long it probably still takes and whether it still moves:

- the time left is measured from the pace of the running step once it has gone a little way, and
  before that estimated from the video (length, size) and the pace of the latest finished runs on
  the workers (`throughput`); without either it stays unknown (the UI then names the step only);
- a running job reports progress and a heartbeat every minute (handball_jobkit.Reporter): silent
  for STALL_S it is «stalled», and the watchdog (`watchdog`, ticked every few minutes) restarts it
  once after RESTART_AFTER_S, or ends it as failed the second time (the coach can try again);
- an upload goes from the browser straight to storage: its parts tell how far it is and when the
  last one arrived; no new part for UPLOAD_IDLE_S and it is «interrupted» (closed tab, lost
  connection), the same file chosen again continues it. No new part for ABANDON_UPLOAD_S and it
  is abandoned: shown as failed, and the watchdog ends it (`abandon_uploads`), so the yellow line
  goes by itself and the file can be removed (second round A4, A9);
- a failed step says whether starting it again can help (`retry`): not after a timeout on the
  same file (it would run out of time again), nor for a file that cannot be read or is too short
  (second round A3).

Two files of one match run one after the other: the second half's analysis waits for the first
(services/videos.WAITING), so its finish counts from the first one's.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from statistics import median
from typing import Any

from sqlalchemy import or_, select

from handball_api.core.db import (
    disable_system_access,
    enable_system_access,
    set_tenant,
    system_access,
)
from handball_api.core.logging import get_logger
from handball_api.models import Match, Opponent, ProcessingJob, VideoAsset
from handball_api.models.enums import JobStatus, VideoRole, VideoStatus
from handball_api.schemas.matches import FileProgressOut, MatchProgressOut, ProgressStage
from handball_api.services.context import Ctx
from handball_api.services.matches import DUPLICATE, halves, parts_of
from handball_api.services.policies import Action, can, visible_team_ids
from handball_api.services.support import failure_code
from handball_api.services.video_jobs import job_budget_s

log = get_logger("handball_api.progress")

STAGES: tuple[ProgressStage, ...] = ("upload", "ingest", "analysis")
# the share of each step in the whole way of a file (the bar), a main file and another camera
WEIGHTS: dict[str, float] = {"upload": 0.1, "ingest": 0.3, "analysis": 0.6}
WEIGHTS_NO_ANALYSIS: dict[str, float] = {"upload": 0.25, "ingest": 0.75}

UPLOAD_IDLE_S = 5 * 60  # no new part for this long: the upload stopped
ABANDON_UPLOAD_S = 6 * 3600  # no new part for this long: the upload is given up
ABANDONED_ERROR = "upload abandoned"
NO_RETRY = (
    "timeout",
    "unreadable",
    "too_short",
    "too_long",
)  # starting the same file again fails again
STALL_S = 10 * 60  # a running job silent this long (it reports at least once a minute)
STALL_S_OLD = 45 * 60  # a job of a worker without heartbeat (before the heartbeat existed)
RESTART_AFTER_S = 30 * 60  # the watchdog restarts a job silent this long, once
WATCHDOG_EVERY_S = 10 * 60  # how often the worker ticks the watchdog
QUEUE_LONG_S = 15 * 60  # waiting for a worker this long is said with the minutes
RECENT_S = 20 * 60  # a match whose processing ended this recently still shows («fertig»)
UPLOAD_LOOK_S = 3 * 86400  # uploads older than this are abandoned (monitoring.abandoned_uploads)
STALLED_ERROR = "stalled: no report from the worker"
# a job still waiting after this long is looked up in the queue; gone from it (Redis restarted
# without persistence, on staging with every deploy), it is enqueued again
QUEUED_CHECK_S = 5 * 60
LOST_ERROR = "lost from the queue"
# a worker reports a job whose work horse was killed (out of memory) with this prefix
# (handball_jobkit.rqworker.WORKER_LOST): restarted once at once, not after RESTART_AFTER_S
WORKER_LOST = "worker lost"

# measured: only once the step has gone this far and run this long (an early pace misleads)
MEASURED_MIN = {"ingest": (0.05, 60.0), "analysis": (0.1, 120.0)}
GB = 1024**3


@dataclass(frozen=True)
class Throughput:
    """Pace of the latest finished runs: analysis seconds per second of video, ingest seconds per
    GB of original. None while there are too few runs to tell."""

    analysis_per_video_s: float | None = None
    ingest_per_gb: float | None = None


@dataclass(frozen=True)
class UploadParts:
    uploaded_bytes: int
    last_part_at: datetime | None


_cache: dict[str, tuple[float, Throughput]] = {}
THROUGHPUT_TTL_S = 600.0
HISTORY_RUNS = 12


def reset_cache() -> None:
    _cache.clear()


def _elapsed(job: ProcessingJob) -> float | None:
    if job.started_at is None or job.finished_at is None:
        return None
    return (job.finished_at - job.started_at).total_seconds()


async def throughput(ctx: Ctx, now: datetime | None = None) -> Throughput:
    """Median pace of the latest finished analyses and ingests on the workers (all clubs: only
    run times and video lengths are read, nothing of a club's content). Cached for ten minutes."""
    hit = _cache.get("all")
    if hit is not None and time.monotonic() - hit[0] < THROUGHPUT_TTL_S:
        return hit[1]
    now = now or datetime.now(UTC)
    await enable_system_access(ctx.db, reason="progress estimate from the pace of finished runs")
    try:
        rows = (
            await ctx.db.execute(
                select(ProcessingJob, VideoAsset.duration_s, VideoAsset.size_bytes)
                .join(VideoAsset, VideoAsset.id == ProcessingJob.video_asset_id)
                .where(
                    ProcessingJob.status == JobStatus.SUCCEEDED,
                    ProcessingJob.kind.in_(("ingest", "analysis")),
                    ProcessingJob.finished_at >= now - timedelta(days=30),
                    ProcessingJob.started_at.is_not(None),
                )
                .order_by(ProcessingJob.finished_at.desc())
                .limit(HISTORY_RUNS * 4)
            )
        ).all()
    finally:
        await disable_system_access(ctx.db)
    analysis: list[float] = []
    ingest: list[float] = []
    for job, duration_s, size in rows:
        took = _elapsed(job)
        if took is None or took < 30:
            continue  # a re-run from cached observations says nothing about the pace
        if job.kind == "analysis" and duration_s and duration_s >= 60:
            analysis.append(took / duration_s)
        elif job.kind == "ingest" and size and size >= 50 * 1024**2:
            ingest.append(took / (size / GB))
    out = Throughput(
        analysis_per_video_s=median(analysis[:HISTORY_RUNS]) if len(analysis) >= 2 else None,
        ingest_per_gb=median(ingest[:HISTORY_RUNS]) if len(ingest) >= 2 else None,
    )
    _cache["all"] = (time.monotonic(), out)
    return out


def _latest(jobs: list[ProcessingJob], kind: str) -> ProcessingJob | None:
    """The newest job of a kind (a job the watchdog replaced is cancelled and skipped)."""
    mine = [j for j in jobs if j.kind == kind and j.status != JobStatus.CANCELLED]
    return max(mine, key=lambda j: j.created_at, default=None)


def _restarted(jobs: list[ProcessingJob], kind: str) -> bool:
    return any(
        j.kind == kind
        and j.status == JobStatus.CANCELLED
        and (j.error or "").startswith(STALLED_ERROR)
        for j in jobs
    )


def last_report(job: ProcessingJob) -> datetime | None:
    return job.heartbeat_at or job.started_at or job.updated_at


def stall_after_s(job: ProcessingJob) -> int:
    return STALL_S if job.heartbeat_at is not None else STALL_S_OLD


def _remaining(
    kind: str, job: ProcessingJob | None, now: datetime, history_total: float | None
) -> tuple[int | None, str | None]:
    """Seconds left in a job's step and how it was estimated."""
    p = job.progress if job is not None and job.status == JobStatus.RUNNING else 0.0
    started = job.started_at if job is not None and job.status == JobStatus.RUNNING else None
    elapsed = (now - started).total_seconds() if started else 0.0
    least, after = MEASURED_MIN[kind]
    if started and p >= least and elapsed >= after:
        return max(0, int(elapsed * (1 - p) / p)), "measured"
    if history_total is not None:
        # the step's run time from the history, less what already ran (never below a minute)
        return max(60, int(history_total - elapsed)), "history"
    if started and p >= 0.03 and elapsed >= after:
        return max(0, int(elapsed * (1 - p) / p)), "measured"
    return None, None


def file_progress(
    asset: VideoAsset,
    jobs: list[ProcessingJob],
    now: datetime,
    pace: Throughput,
    parts: UploadParts | None = None,
    part: int | None = None,
    half: int | None = None,
) -> FileProgressOut | None:
    """The progress of one file, None for a file that is not part of the work (the same file a
    second time)."""
    if asset.status == VideoStatus.FAILED and (asset.error or "").startswith(DUPLICATE):
        return None
    analysed = asset.role == VideoRole.MAIN
    weights = WEIGHTS if analysed else WEIGHTS_NO_ANALYSIS
    size_gb = asset.size_bytes / GB if asset.size_bytes else None
    hist_ingest = pace.ingest_per_gb * size_gb if pace.ingest_per_gb and size_gb else None
    hist_analysis = (
        pace.analysis_per_video_s * asset.duration_s
        if pace.analysis_per_video_s and asset.duration_s
        else None
    )
    base: dict[str, Any] = {
        "video_id": asset.id,
        "filename": asset.filename,
        "role": asset.role,
        "part": part,
        "half": half,
        "size_bytes": asset.size_bytes or None,
        "duration_s": asset.duration_s,
    }

    def overall(stage: str, fraction: float) -> float:
        order = ("upload", "ingest", "analysis", "done")
        done = sum(w for s, w in weights.items() if order.index(s) < order.index(stage))
        return round(min(1.0, done + weights.get(stage, 0.0) * fraction), 4)

    ingest = _latest(jobs, "ingest")
    imp = _latest(jobs, "import")
    analysis = _latest(jobs, "analysis")

    # ---- hochladen ------------------------------------------------------------------------
    if asset.status == VideoStatus.UPLOADING:
        if asset.source_url:  # a link import: the worker downloads it
            link = imp.progress if imp is not None else 0.0
            return FileProgressOut(
                **base,
                stage="upload",
                state=(
                    "running" if imp is not None and imp.status == JobStatus.RUNNING else "queued"
                ),
                step="link",
                fraction=link,
                overall=overall("upload", link),
                stage_started_at=imp.started_at if imp else asset.created_at,
                last_activity_at=last_report(imp) if imp else None,
            )
        uploaded = parts.uploaded_bytes if parts else None
        last = (parts.last_part_at if parts else None) or asset.created_at
        idle = (now - last).total_seconds()
        frac = min(1.0, uploaded / asset.size_bytes) if uploaded and asset.size_bytes else None
        eta: int | None = None
        if uploaded and parts and parts.last_part_at and frac and frac >= 0.01:
            took = (parts.last_part_at - asset.created_at).total_seconds()
            if took >= 10:
                eta = int((asset.size_bytes - uploaded) / (uploaded / took))
        interrupted = idle >= UPLOAD_IDLE_S
        if idle >= ABANDON_UPLOAD_S:
            # given up (the watchdog ends it): nothing goes on by itself, the file can go
            return FileProgressOut(
                **base,
                stage="upload",
                state="failed",
                fraction=frac,
                overall=overall("upload", frac or 0.0),
                stage_started_at=asset.created_at,
                last_activity_at=parts.last_part_at if parts else None,
                uploaded_bytes=uploaded,
                idle_s=int(idle),
                error="abandoned",
                retry=False,
            )
        return FileProgressOut(
            **base,
            stage="upload",
            state="interrupted" if interrupted else "running",
            fraction=frac,
            overall=overall("upload", frac or 0.0),
            stage_started_at=asset.created_at,
            last_activity_at=parts.last_part_at if parts else None,
            eta_s=None if interrupted else eta,
            eta_basis="measured" if eta is not None and not interrupted else None,
            uploaded_bytes=uploaded,
            idle_s=int(idle) if interrupted else None,
        )

    # ---- einlesen ---------------------------------------------------------------------------
    ingest_open = ingest is None or ingest.status != JobStatus.SUCCEEDED
    if asset.status in (VideoStatus.UPLOADED, VideoStatus.PROCESSING) or (
        asset.status == VideoStatus.FAILED and ingest_open
    ):
        if asset.status == VideoStatus.FAILED:
            code = (
                ("abandoned" if (asset.error or "") == ABANDONED_ERROR else "upload")
                if ingest is None
                else failure_code(asset.error)
            )
            return FileProgressOut(
                **base,
                stage="upload" if ingest is None else "ingest",
                state="failed",
                overall=overall("ingest", 0.0),
                error=code,
                retry=ingest is not None and code not in NO_RETRY,
            )
        return _job_file(
            base, "ingest", ingest, jobs, now, hist_ingest, overall, after=hist_analysis
        )

    # ---- analysieren ------------------------------------------------------------------------
    if analysed and analysis is not None and analysis.status != JobStatus.SUCCEEDED:
        waiting = bool((asset.analysis or {}).get("waiting_job")) and (
            analysis.status == JobStatus.QUEUED
        )
        return _job_file(
            base, "analysis", analysis, jobs, now, hist_analysis, overall, waiting=waiting
        )

    # ---- fertig ------------------------------------------------------------------------------
    ended = [
        j.finished_at for j in (ingest, analysis) if j is not None and j.finished_at is not None
    ]
    return FileProgressOut(
        **base,
        stage="done",
        state="done",
        fraction=1.0,
        overall=1.0,
        last_activity_at=max(ended) if ended else None,
    )


def _job_file(
    base: dict[str, Any],
    kind: str,
    job: ProcessingJob | None,
    jobs: list[ProcessingJob],
    now: datetime,
    history_total: float | None,
    overall: Any,
    after: float | None = None,
    waiting: bool = False,
) -> FileProgressOut:
    """A file in a worker step (ingest or analysis): queued, waiting, running, stalled, failed."""
    stage: ProgressStage = "ingest" if kind == "ingest" else "analysis"
    restarted = _restarted(jobs, kind)
    if job is not None and job.status == JobStatus.FAILED:
        code = failure_code(job.error)
        return FileProgressOut(
            **base,
            stage=stage,
            state="failed",
            fraction=job.progress,
            overall=overall(stage, job.progress),
            stage_started_at=job.started_at,
            last_activity_at=job.finished_at,
            restarted=restarted,
            error=code,
            retry=code not in NO_RETRY,
            limit_s=(
                job_budget_s(kind, base.get("duration_s"), base.get("size_bytes"))
                if code == "timeout"
                else None
            ),
        )
    eta, basis = _remaining(kind, job, now, history_total)
    # the analysis after the ingest: only once the video's length is known (never before)
    finish = eta + int(after) if eta is not None and after is not None else None
    if kind == "analysis":
        finish = eta
    if job is None or job.status == JobStatus.QUEUED:
        queued_since = job.created_at if job is not None else None
        idle = int((now - queued_since).total_seconds()) if queued_since else None
        return FileProgressOut(
            **base,
            stage=stage,
            state="waiting" if waiting else "queued",
            fraction=0.0,
            overall=overall(stage, 0.0),
            eta_s=eta,
            finish_s=finish,
            eta_basis=basis,
            idle_s=idle if idle is not None and idle >= QUEUE_LONG_S and not waiting else None,
            restarted=restarted,
        )
    stages = job.stages or {}
    step = next(
        (k for k, v in stages.items() if isinstance(v, dict) and v.get("status") == "running"),
        None,
    )
    last = last_report(job)
    silent = (now - last).total_seconds() if last else 0.0
    stalled = silent >= stall_after_s(job)
    restart_at = None
    if stalled and last is not None:
        # the watchdog looks every few minutes: at the latest one round after the limit
        restart_at = last + timedelta(seconds=RESTART_AFTER_S + WATCHDOG_EVERY_S)
    return FileProgressOut(
        **base,
        stage=stage,
        state="stalled" if stalled else "running",
        step=step,
        fraction=job.progress,
        overall=overall(stage, job.progress),
        stage_started_at=job.started_at,
        last_activity_at=last,
        eta_s=None if stalled else eta,
        finish_s=None if stalled else finish,
        eta_basis=None if stalled else basis,
        idle_s=int(silent) if stalled else None,
        restart_at=restart_at,
        restarted=restarted,
    )


ORDER = {"upload": 0, "ingest": 1, "analysis": 2, "done": 3}
ACTIVE = ("running", "queued", "waiting", "stalled", "interrupted")


def match_summary(
    match: Match,
    opponent_name: str,
    files: list[FileProgressOut],
    jobs: list[ProcessingJob],
    now: datetime,
    keep_failed: bool = False,
) -> MatchProgressOut | None:
    """The files together: the step of the file furthest behind, the worst state, and the time
    until everything is done (a waiting second half counts from the first one's finish).
    `keep_failed` (the match's own page): a failed file stays shown however long ago it failed,
    so it can be removed or started again there (second round A1)."""
    if not files:
        return None
    active = [f for f in files if f.state in ACTIVE]
    failed = [f for f in files if f.state == "failed"]
    ended = [j.finished_at for j in jobs if j.finished_at is not None]
    finished_at = max(ended) if ended else None
    # nothing runs: shown a while after the end («fertig», or what failed)
    old = finished_at is None or (now - finished_at).total_seconds() > RECENT_S
    if not active and old and not (keep_failed and failed):
        return None
    # the finish of each file: a part that waits starts after the parts before it
    finish: list[int | None] = []
    before = 0
    for f in sorted(active, key=lambda x: x.part or 99):
        if f.state == "waiting":
            own = f.finish_s
            finish.append(before + own if own is not None and before is not None else None)
        else:
            finish.append(f.finish_s)
        if finish[-1] is not None:
            before = max(before, int(finish[-1] or 0))
    eta = (
        max((x for x in finish if x is not None), default=None)
        if all(x is not None for x in finish) and finish
        else None
    )
    if any(f.state == "stalled" for f in active):
        state = "stalled"
    elif any(f.state == "interrupted" for f in active):
        state = "interrupted"
    elif active:
        state = "running"
    elif failed:
        state = "failed"
    else:
        state = "done"
    stage = min((f.stage for f in active), key=lambda s: ORDER[s], default="done")
    weights = [f.overall for f in files]
    return MatchProgressOut(
        match_id=match.id,
        team_id=match.team_id,
        kind=match.kind,
        opponent_name=opponent_name,
        scouting_other=match.scouting_other,
        kickoff_at=match.kickoff_at,
        is_home=match.is_home,
        stage=stage,
        state=state,
        overall=round(sum(weights) / len(weights), 4),
        eta_s=eta if active else None,
        finished_at=finished_at if not active else None,
        files=files,
    )


async def _upload_parts(ctx: Ctx, asset: VideoAsset, now: datetime) -> UploadParts | None:
    if not asset.upload_id or (now - asset.created_at).total_seconds() > UPLOAD_LOOK_S:
        return None
    try:
        parts = await ctx.storage.list_parts(
            ctx.settings.s3_bucket_videos, asset.storage_key, asset.upload_id
        )
    except Exception as exc:  # expired or storage hiccup: the progress stands without it
        log.info("progress_parts_unavailable", video=str(asset.id), error=str(exc))
        return None
    stamps = [p.last_modified for p in parts if p.last_modified is not None]
    return UploadParts(sum(p.size for p in parts), max(stamps) if stamps else None)


async def for_match(
    ctx: Ctx,
    match: Match,
    now: datetime | None = None,
    pace: Throughput | None = None,
    keep_failed: bool = False,
) -> MatchProgressOut | None:
    now = now or datetime.now(UTC)
    if match.is_demo:
        return None
    assets = (
        await ctx.db.scalars(
            select(VideoAsset)
            .where(VideoAsset.match_id == match.id)
            .order_by(VideoAsset.created_at)
        )
    ).all()
    if not assets:
        return None
    jobs = list(
        (
            await ctx.db.scalars(
                select(ProcessingJob)
                .where(ProcessingJob.match_id == match.id)
                .order_by(ProcessingJob.created_at.desc())
                .limit(60)
            )
        ).all()
    )
    layout = await parts_of(ctx, match.id)
    numbers = {p.video_id: p.position + 1 for p in layout}
    half = halves(layout)
    pace = pace or await throughput(ctx, now)
    files: list[FileProgressOut] = []
    for a in assets:
        mine = [j for j in jobs if j.video_asset_id == a.id]
        parts = (
            await _upload_parts(ctx, a, now)
            if a.status == VideoStatus.UPLOADING and not a.source_url
            else None
        )
        f = file_progress(a, mine, now, pace, parts, numbers.get(a.id), half.get(a.id))
        if f is not None:
            files.append(f)
    # the files in the order of the match: parts first, then the others as uploaded
    files.sort(key=lambda f: (f.part is None, f.part or 0))
    opp = await ctx.db.get(Opponent, match.opponent_id) if match.opponent_id else None
    return match_summary(match, opp.name if opp else "", files, jobs, now, keep_failed)


async def for_org(ctx: Ctx, now: datetime | None = None) -> list[MatchProgressOut]:
    """The matches of the teams the person sees with an upload or processing running, or ended
    within RECENT_S: the progress in the head of every page and on Spiele."""
    now = now or datetime.now(UTC)
    actor = ctx.require_actor()
    busy_jobs = select(ProcessingJob.match_id).where(
        or_(
            ProcessingJob.status.in_((JobStatus.QUEUED, JobStatus.RUNNING)),
            ProcessingJob.finished_at >= now - timedelta(seconds=RECENT_S),
        )
    )
    busy_videos = select(VideoAsset.match_id).where(
        VideoAsset.status.in_(
            (VideoStatus.UPLOADING, VideoStatus.UPLOADED, VideoStatus.PROCESSING)
        ),
        VideoAsset.created_at >= now - timedelta(seconds=UPLOAD_LOOK_S),
    )
    q = select(Match).where(
        Match.is_demo.is_(False),
        or_(Match.id.in_(busy_jobs), Match.id.in_(busy_videos)),
    )
    visible = visible_team_ids(actor)
    if visible is not None:
        q = q.where(Match.team_id.in_(visible))
    matches = (await ctx.db.scalars(q.order_by(Match.kickoff_at.desc()).limit(20))).all()
    pace = await throughput(ctx, now)
    out: list[MatchProgressOut] = []
    for m in matches:
        if not can(actor, Action.MATCH_READ, m.team_id):
            continue
        p = await for_match(ctx, m, now, pace)
        if p is not None:
            out.append(p)
    # running first, then by kickoff
    out.sort(key=lambda p: (p.state not in ACTIVE, -p.kickoff_at.timestamp()))
    return out


# ---- watchdog -------------------------------------------------------------------------------


async def watchdog(ctx: Ctx, now: datetime | None = None) -> dict[str, int]:
    """Jobs that went silent (their worker is gone: restarted, out of memory): restarted once,
    the second time ended as failed so the coach sees it and can try again. The worker ticks it
    every few minutes; each job is handled within its own club (RLS)."""
    now = now or datetime.now(UTC)
    async with system_access(ctx.db, reason="job watchdog: running jobs of all clubs"):
        found = (
            await ctx.db.execute(
                select(ProcessingJob.id, ProcessingJob.organization_id).where(
                    ProcessingJob.status == JobStatus.RUNNING,
                    ProcessingJob.kind.in_(("ingest", "analysis", "import")),
                )
            )
        ).all()
    restarted = failed = 0
    for job_id, org_id in found:
        await disable_system_access(ctx.db)
        await set_tenant(ctx.db, org_id)
        job = await ctx.db.get(ProcessingJob, job_id)
        if job is None or job.status != JobStatus.RUNNING:
            continue
        last = last_report(job)
        if last is None:
            continue
        limit = RESTART_AFTER_S if job.heartbeat_at is not None else _old_limit(job)
        if (now - last).total_seconds() < limit:
            continue
        outcome = await restart_or_fail(ctx, job, now, f"since {last.isoformat()}")
        restarted += outcome == "restarted"
        failed += outcome == "failed"
    await ctx.db.flush()
    requeued = await requeue_lost(ctx, now)
    abandoned = await abandon_uploads(ctx, now)
    return {"restarted": restarted, "failed": failed, "requeued": requeued, "abandoned": abandoned}


async def restart_or_fail(ctx: Ctx, job: ProcessingJob, now: datetime, why: str) -> str | None:
    """A running job whose worker is gone (silent, or its work horse was killed): an ingest or
    analysis job is started again the first time (a new job; the old one cancelled with
    STALLED_ERROR, so `_restarted` sees it), the second time, and for other kinds, it ends as
    failed («stalled»: the coach can try again). "restarted", "failed", or None when the job has
    no file or match. Runs within the job's club (the caller set the tenant)."""
    from handball_api.schemas.matches import JobUpdate
    from handball_api.services import videos  # imports this module

    asset = await ctx.db.get(VideoAsset, job.video_asset_id) if job.video_asset_id else None
    match = await ctx.db.get(Match, job.match_id)
    if asset is None or match is None:
        return None
    siblings = list(
        (
            await ctx.db.scalars(
                select(ProcessingJob).where(ProcessingJob.video_asset_id == asset.id)
            )
        ).all()
    )
    if not _restarted(siblings, job.kind) and job.kind in ("ingest", "analysis"):
        job.status = JobStatus.CANCELLED
        job.finished_at = now
        job.error = f"{STALLED_ERROR} {why}"
        await ctx.db.flush()
        if job.kind == "ingest":
            await videos.start_ingest(ctx, asset)
        else:
            await videos.start_analysis(ctx, asset, match)
        log.warning("job_restarted", job=str(job.id), kind=job.kind, why=why)
        return "restarted"
    await videos.apply_job_update(
        ctx,
        job.id,
        JobUpdate(
            status=JobStatus.FAILED,
            progress=job.progress,
            error=f"{STALLED_ERROR} (timeout) {why}",
        ),
    )
    log.warning("job_failed_silent", job=str(job.id), kind=job.kind, why=why)
    return "failed"


async def requeue_lost(ctx: Ctx, now: datetime | None = None) -> int:
    """Jobs that wait for a worker but are no longer in the queue: Redis runs without
    persistence, and a restart (on staging with every deploy, 17.11.) wipes out what was only
    waiting; the job would show "in der Warteschlange" forever. Such a job is ended and the step
    started again (a new job, as the restart of a silent job does). Each club on its own (RLS)."""
    import asyncio

    from handball_api.services import videos  # imports this module

    if ctx.jobs is None:
        return 0
    now = now or datetime.now(UTC)
    async with system_access(ctx.db, reason="job watchdog: waiting jobs of all clubs"):
        found = (
            await ctx.db.execute(
                select(ProcessingJob.id, ProcessingJob.organization_id).where(
                    ProcessingJob.status == JobStatus.QUEUED,
                    ProcessingJob.kind.in_(("ingest", "analysis")),
                    ProcessingJob.created_at <= now - timedelta(seconds=QUEUED_CHECK_S),
                )
            )
        ).all()
    requeued = 0
    for job_id, org_id in found:
        if await asyncio.to_thread(ctx.jobs.exists, str(job_id)) is not False:
            continue  # still waiting in the queue, or the queue cannot be asked
        await set_tenant(ctx.db, org_id)
        job = await ctx.db.get(ProcessingJob, job_id)
        if job is None or job.status != JobStatus.QUEUED or job.video_asset_id is None:
            continue
        asset = await ctx.db.get(VideoAsset, job.video_asset_id)
        match = await ctx.db.get(Match, job.match_id)
        if asset is None or match is None:
            continue
        job.status = JobStatus.CANCELLED
        job.finished_at = now
        job.error = LOST_ERROR
        await ctx.db.flush()
        if job.kind == "ingest":
            await videos.start_ingest(ctx, asset)
        else:
            await videos.start_analysis(ctx, asset, match)
        log.warning("job_requeued", job=str(job.id), kind=job.kind)
        requeued += 1
    await ctx.db.flush()
    return requeued


async def abandon_uploads(ctx: Ctx, now: datetime | None = None) -> int:
    """Uploads without a new part for ABANDON_UPLOAD_S are given up: the parts in storage go,
    the file is marked failed («Der Upload wurde nicht fertig»), the yellow line of the
    interrupted upload ends by itself and the file can be removed (second round A4, A9). Each
    upload is handled within its own club (RLS)."""
    from handball_api.services import videos  # imports this module

    now = now or datetime.now(UTC)
    async with system_access(ctx.db, reason="watchdog: uploads nobody continues"):
        found = (
            await ctx.db.execute(
                select(VideoAsset.id, VideoAsset.organization_id).where(
                    VideoAsset.status == VideoStatus.UPLOADING,
                    VideoAsset.source_url.is_(None),
                    VideoAsset.created_at <= now - timedelta(seconds=ABANDON_UPLOAD_S),
                )
            )
        ).all()
    gone = 0
    for asset_id, org_id in found:
        await disable_system_access(ctx.db)
        await set_tenant(ctx.db, org_id)
        asset = await ctx.db.get(VideoAsset, asset_id)
        if asset is None or asset.status != VideoStatus.UPLOADING:
            continue
        parts = await _upload_parts(ctx, asset, now) if asset.upload_id else None
        last = (parts.last_part_at if parts else None) or asset.created_at
        if (now - last).total_seconds() < ABANDON_UPLOAD_S:
            continue
        if asset.upload_id:
            try:
                await ctx.storage.abort_multipart(
                    ctx.settings.s3_bucket_videos, asset.storage_key, asset.upload_id
                )
            except Exception as exc:  # already gone
                log.info("abort_multipart_failed", video=str(asset.id), error=str(exc))
        asset.status = VideoStatus.FAILED
        asset.error = ABANDONED_ERROR
        asset.upload_id = None
        match = await ctx.db.get(Match, asset.match_id)
        if match is not None:
            await ctx.db.flush()
            await videos.settle_status(ctx, match)
        log.warning("upload_abandoned", video=str(asset.id), last_part=str(last))
        gone += 1
    await ctx.db.flush()
    return gone


def _old_limit(job: ProcessingJob) -> float:
    """A job of a worker without heartbeat: only once it is past the time its worker has."""
    return float(max(RESTART_AFTER_S, job_budget_s(job.kind)))
