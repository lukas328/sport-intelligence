"""The analysis of a video (stages 2 to 5): start, the parts waiting for each other, the result,
the court (calibration) and what the analysis shows."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import delete, select

from handball_api.core.colors import analysis_kits
from handball_api.core.errors import ProblemError
from handball_api.core.storage import ObjectNotFoundError
from handball_api.models import (
    CameraCalibration,
    Match,
    Opponent,
    OpponentPlayer,
    ProcessingJob,
    Track,
    VideoAsset,
)
from handball_api.models.enums import JobStatus, VideoRole, VideoStatus
from handball_api.services import (
    audit,
    auto_events,
    checks,
    goal_candidates,
    halls,
    marks,
    shot_positions,
    timeline,
)
from handball_api.services.context import Ctx
from handball_api.services.matches import Part, parts_of
from handball_api.services.policies import Action
from handball_api.services.roster import numbers as roster_numbers
from handball_api.services.support import failure_code
from handball_api.services.video_base import (
    ANALYSIS_FUNC,
    CLICKED,
    LINE_CLICKS,
    PENDING,
    UNDETERMINABLE,
    WAITING,
    get_asset,
)
from handball_api.services.video_jobs import _new_job, job_budget_s
from handball_api.services.video_media import media_prefix


async def start_analysis(
    ctx: Ctx,
    asset: VideoAsset,
    match: Match,
    points: list[dict[str, Any]] | None = None,
    space: str = "frame",
    frame_ms: int = 0,
    references: list[dict[str, Any]] | None = None,
) -> ProcessingJob:
    job = await _new_job(ctx, asset, "analysis")
    meta = dict(asset.analysis or {})
    if points is not None or references is not None:
        meta.pop(UNDETERMINABLE, None)  # a court is set after all
        asset.analysis = meta
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
    elif references is None and await _earlier_part_busy(ctx, asset):
        # the second half uploaded together with the first: it waits until the first half is
        # analysed (or failed), so its job gets the first half's sides and court (Echtlauf 5 P3)
        asset.analysis = {**meta, WAITING: str(job.id)}
        return job
    await _enqueue_analysis(ctx, asset, match, job, points, space, frame_ms, references)
    return job


async def _earlier_part_busy(ctx: Ctx, asset: VideoAsset) -> bool:
    """A second half whose earlier part is still being analysed."""
    parts = await parts_of(ctx, asset.match_id)
    part = next((p for p in parts if p.video_id == asset.id), None)
    if part is None or not timeline.is_second_half(parts, part):
        return False
    earlier = [p.video_id for p in parts[: part.position]]
    busy = await ctx.db.scalar(
        select(ProcessingJob.id)
        .where(
            ProcessingJob.video_asset_id.in_(earlier),
            ProcessingJob.kind == "analysis",
            ProcessingJob.status.in_((JobStatus.QUEUED, JobStatus.RUNNING)),
        )
        .limit(1)
    )
    return busy is not None


async def start_waiting(ctx: Ctx, match: Match) -> None:
    """The analyses that waited for an earlier part: started once it is no longer busy (done,
    failed or gone), never blocked by its failure."""
    assets = (
        await ctx.db.scalars(
            select(VideoAsset).where(
                VideoAsset.match_id == match.id, VideoAsset.role == VideoRole.MAIN
            )
        )
    ).all()
    for a in assets:
        waiting = (a.analysis or {}).get(WAITING)
        if not waiting or await _earlier_part_busy(ctx, a):
            continue
        a.analysis = {k: v for k, v in (a.analysis or {}).items() if k != WAITING}
        job = await ctx.db.get(ProcessingJob, uuid.UUID(str(waiting)))
        if job is None or job.status != JobStatus.QUEUED:
            continue
        await _enqueue_analysis(ctx, a, match, job, None, "frame", 0, None)


async def _enqueue_analysis(
    ctx: Ctx,
    asset: VideoAsset,
    match: Match,
    job: ProcessingJob,
    points: list[dict[str, Any]] | None,
    space: str,
    frame_ms: int,
    references: list[dict[str, Any]] | None,
) -> None:
    opp = await ctx.db.get(Opponent, match.opponent_id) if match.opponent_id else None
    opponent_kit = match.opponent_kit or (opp.primary_color if opp is not None else None)
    refs: list[dict[str, Any]] = list(references or [])
    if points is None and references is None:
        # the court of the match's other half first (the camera often stands where it stood),
        # then the court clicked or confirmed on an earlier video of the same hall: the worker
        # tries to carry it over before the automatic court
        refs = await halls.match_references(ctx, asset)
        seen = {r["video_id"] for r in refs}
        refs += [
            r
            for r in await halls.references(ctx, asset, (await halls.hall_of(ctx, match))[0])
            if r["video_id"] not in seen
        ][: max(0, halls.MAX_REFERENCES - len(refs))]
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
                # only a colour somebody said, for this match or remembered for the opponent
                # (third real-video test G5): the column's default red is no knowledge (E09)
                "opponent": opponent_kit,
                "opponent_gk": match.kit_opponent_gk if opponent_kit else None,
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
    hint = await timeline.side_hint_for(ctx, asset)
    if hint is not None:
        # the second half in a file of its own: the teams changed ends (Q-VIDEO-PARTS)
        payload["side_hint"] = hint
    await ctx.enqueue(
        "gpu",
        ANALYSIS_FUNC,
        str(job.id),
        payload,
        timeout_s=job_budget_s("analysis", duration_s=asset.duration_s),
    )


async def _rosters(ctx: Ctx, match: Match) -> dict[str, list[int]]:
    """Shirt numbers per kit label for the number vote of the analysis. The labels follow the
    kits in the job payload, so "home" is always the own kit (match.is_home only moves the
    overlay); the opponent side only when its players were entered. Empty sides are left out."""
    out: dict[str, list[int]] = {}
    # a scouting match: the own side is the opponent's opponent, not our roster (K3)
    own = (
        sorted(await roster_numbers(ctx, match.season_id, match.team_id))
        if match.kind != "scouting"
        else []
    )
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
    """Stores the results; True when they are the match's (the video is a part of its timeline).

    Tracks and the court belong to the video (times in the file). Events, possessions, the match
    clock and goal candidates are the match's: they are placed on the match timeline at the part's
    start and replace only what an earlier run found in this part. A part whose place is not known
    yet (a part before it has no length) keeps its results to itself."""
    part = await _part_of(ctx, asset)
    on_timeline = asset.role == VideoRole.MAIN and part is not None and part.offset_ms is not None
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
        # a scouting match: the "home" kit is another team, never our players (K3)
        if owner is not None and owner.season_id is not None and owner.kind != "scouting":
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
            "ball_path",
        )
    }
    # how much the analysis found (play time, people seen): Prüfen asks nothing when it is too
    # little and says why instead (services/checks)
    asset.analysis["signals"] = checks.signals(r)
    if clicked is not None:
        asset.analysis[CLICKED] = clicked
    for key in (LINE_CLICKS, UNDETERMINABLE):
        if isinstance(before.get(key), dict):
            asset.analysis[key] = before[key]
    if pending is not None:  # a newer run with clicked points is still running
        asset.analysis[PENDING] = pending
    auto = r.get("events")
    sb_raw = r.get("scoreboard")
    overlay: dict[str, Any] | None = sb_raw if isinstance(sb_raw, dict) else None
    if isinstance(auto, dict) or overlay:
        auto = auto if isinstance(auto, dict) else {}
        match = await ctx.db.get(Match, asset.match_id)
        if match is not None and on_timeline and part is not None:
            offset = int(part.offset_ms or 0)
            layout = await parts_of(ctx, asset.match_id)
            # the first part also owns the times before it, the last one those after it (one
            # file: the whole match is this run's)
            window = (
                None if part.position == 0 else offset,
                None if part.position == len(layout) - 1 else part.end_ms,
            )
            counts = await auto_events.apply(
                ctx,
                match,
                timeline.shift_times(auto, offset, timeline.EVENT_TIMES) or None,
                timeline.shift_times(overlay, offset, timeline.OVERLAY_TIMES),
                window=window,
                second_half=timeline.is_second_half(layout, part),
            )
            # courtside marks with device time follow the new goals (5.3)
            await marks.sync_match(ctx, match.id, authorised=True)
            # goals marked by hand get their shot position from the tracking
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
    if "goal_candidates" in r and on_timeline and part is not None:
        # moments that are probably goals, for the coach to confirm (needs no court, so also
        # when the analysis waits for court points); after the automatic events: their
        # possessions suggest the side
        owner = await ctx.db.get(Match, asset.match_id)
        found = timeline.shift_times(
            r.get("goal_candidates"), int(part.offset_ms or 0), timeline.CANDIDATE_TIMES
        )
        if owner is not None:
            counts = await goal_candidates.store(
                ctx, owner, asset, found if isinstance(found, dict) else None, job.pipeline_version
            )
            # report goals that match a candidate unambiguously on the overlay clock (L1)
            counts["auto_confirmed"] = await goal_candidates.auto_accept(ctx, owner)
            asset.analysis = {**asset.analysis, "goal_candidates": counts}
    return on_timeline


async def _part_of(ctx: Ctx, asset: VideoAsset) -> Part | None:
    return next((p for p in await parts_of(ctx, asset.match_id) if p.video_id == asset.id), None)


def _with_sure(asset: VideoAsset, info: Any) -> Any:
    """A court carried over from the hall says whether the hall images matched well enough not
    to ask about it (services/checks.hall_court_sure)."""
    if not isinstance(info, dict) or info.get("method") != "hall":
        return info
    return {**info, "sure": checks.hall_court_sure(asset)}


async def calibration_state(
    ctx: Ctx, asset: VideoAsset, cal: CameraCalibration | None, job: ProcessingJob | None
) -> str:
    """Where the court of this file stands, for the calibration dialog:

    - "updating": a court the coach clicked is being applied (its analysis runs);
    - "confirmed": a person set or confirmed it, or it was carried over from a court a person set
      with a sure hall match (same rule as graphics._court_ok: positions are drawn);
    - "suggested": the automatic court, or one carried over without a sure match: shown as a
      proposal to confirm (POST .../calibration/confirm) or to click anew;
    - "missing": no court (needs_calibration);
    - "undeterminable": the coach said the court cannot be set on this video."""
    meta = asset.analysis or {}
    pending = meta.get(PENDING)
    if (
        isinstance(pending, dict)
        and job is not None
        and pending.get("job_id") == str(job.id)
        and job.status in (JobStatus.QUEUED, JobStatus.RUNNING)
    ):
        return "updating"
    if (
        cal is not None
        and not meta.get("needs_calibration")
        and (cal.source == "user_correction" or checks.hall_court_sure(asset))
    ):
        return "confirmed"
    if checks.court_undeterminable(asset):
        return "undeterminable"
    if cal is None or meta.get("needs_calibration"):
        return "missing"
    info = meta.get("calibration_info")
    if isinstance(info, dict) and info.get("method") == "hall":
        ref = str(info.get("reference_video_id") or "")
        siblings = {str(p.video_id) for p in await parts_of(ctx, asset.match_id)}
        if ref and ref in siblings - {str(asset.id)}:
            return "confirmed"  # the court a person set on another part of this match
    return "suggested"


async def _hall_reference(
    ctx: Ctx, asset: VideoAsset, info: dict[str, Any]
) -> tuple[uuid.UUID, uuid.UUID, datetime, str | None] | None:
    """The earlier video a hall court was carried over from (calibration_info
    reference_video_id), in this organisation: its id, its match, that match's kickoff and
    venue. One query."""
    try:
        ref_id = uuid.UUID(str(info.get("reference_video_id")))
    except ValueError:
        return None
    row = (
        await ctx.db.execute(
            select(VideoAsset.id, VideoAsset.match_id, Match.kickoff_at, Match.venue)
            .join(Match, Match.id == VideoAsset.match_id)
            .where(VideoAsset.id == ref_id, VideoAsset.organization_id == asset.organization_id)
        )
    ).first()
    return (row[0], row[1], row[2], row[3]) if row is not None else None


async def calibration_suggestion(
    ctx: Ctx, asset: VideoAsset, cal: CameraCalibration | None, state: str
) -> dict[str, Any] | None:
    """The court shown as a proposal while the state is "suggested": carried over from an
    earlier video of the hall (source "hall", with that video and its match's kickoff for the
    label) or the automatic court. On the hall image (the analysis' image size)."""
    if state != "suggested" or cal is None:
        return None
    info = (asset.analysis or {}).get("calibration_info")
    out: dict[str, Any] = {
        "source": "auto",
        "homography": cal.homography,
        "image_size": cal.image_size,
        "space": "panorama",
        "from_video_id": None,
        "from_kickoff_at": None,
    }
    if isinstance(info, dict) and info.get("method") == "hall":
        out["source"] = "hall"
        ref = await _hall_reference(ctx, asset, info)
        if ref is not None:
            out["from_video_id"], _, out["from_kickoff_at"], _ = ref
    return out


async def calibration_origin(
    ctx: Ctx, asset: VideoAsset, cal: CameraCalibration | None, state: str
) -> dict[str, Any] | None:
    """Where a confirmed court came from when nobody set it on this video: carried over from an
    earlier video of the same hall (source "hall"), so the app can say so and offer to click it
    anew. None for a court a person clicked or confirmed on this video, an automatic court
    (a suggestion: calibration_suggestion) and no court."""
    if state != "confirmed" or cal is None or cal.source == "user_correction":
        return None
    info = (asset.analysis or {}).get("calibration_info")
    if not isinstance(info, dict) or info.get("method") != "hall":
        return None
    hall = info.get("hall")
    out: dict[str, Any] = {
        "source": "hall",
        "hall": hall if isinstance(hall, str) and hall.strip() else None,
        "reference_video_id": None,
        "reference_match_id": None,
        "reference_kickoff_at": None,
    }
    ref = await _hall_reference(ctx, asset, info)
    if ref is not None:
        video_id, match_id, kickoff_at, venue = ref
        if match_id == asset.match_id:
            # carried over from another part of this same match: not «from an earlier match»
            return None
        out["reference_video_id"] = video_id
        out["reference_match_id"] = match_id
        out["reference_kickoff_at"] = kickoff_at
        if out["hall"] is None and venue and venue.strip():
            out["hall"] = venue.strip()
    return out


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
        "calibration_info": _with_sure(asset, meta.get("calibration_info")),
        "hall": await halls.summary(ctx, asset, match) if match is not None else None,
        "court_clicks": meta.get(LINE_CLICKS) if isinstance(meta.get(LINE_CLICKS), dict) else None,
        "calibration_state": (state := await calibration_state(ctx, asset, cal, job)),
        "calibration_suggestion": await calibration_suggestion(ctx, asset, cal, state),
        "calibration_origin": await calibration_origin(ctx, asset, cal, state),
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


async def retry_analysis(ctx: Ctx, asset_id: uuid.UUID) -> ProcessingJob:
    """The analysis of one file again (a part whose analysis failed, or one analysed before
    parts were placed on the match timeline): the other parts keep theirs."""
    asset = await get_asset(ctx, asset_id, Action.VIDEO_UPLOAD)
    if asset.status != VideoStatus.READY or not asset.proxy_key:
        raise ProblemError(409, "video-not-ready", "The video is still being processed")
    running = await ctx.db.scalar(
        select(ProcessingJob.id).where(
            ProcessingJob.video_asset_id == asset.id,
            ProcessingJob.kind == "analysis",
            ProcessingJob.status.in_((JobStatus.QUEUED, JobStatus.RUNNING)),
        )
    )
    if running is not None:
        raise ProblemError(409, "analysis-running", "The analysis is already running")
    match = await ctx.db.get(Match, asset.match_id)
    assert match is not None
    await audit.record(ctx, "video.analysis_retried", target_type="video", target_id=asset.id)
    return await start_analysis(ctx, asset, match)


async def court_from_part(ctx: Ctx, asset_id: uuid.UUID, source_id: uuid.UUID) -> ProcessingJob:
    """The court of the match's other part for this part (the camera stood where it stood): its
    clicked frame points as they are, or its confirmed court carried over by matching the hall
    images. The analysis of this part runs again with it."""
    asset = await get_asset(ctx, asset_id, Action.VIDEO_UPLOAD)
    source = await get_asset(ctx, source_id)
    if source.match_id != asset.match_id or source.id == asset.id:
        raise ProblemError(422, "validation", "Give another file of the same match")
    if asset.status != VideoStatus.READY or not asset.proxy_key:
        raise ProblemError(409, "video-not-ready", "The video is still being processed")
    match = await ctx.db.get(Match, asset.match_id)
    assert match is not None
    clicked = (source.analysis or {}).get(CLICKED)
    await audit.record(
        ctx,
        "video.court_from_part",
        target_type="video",
        target_id=asset.id,
        data={"from": str(source.id)},
    )
    if isinstance(clicked, dict) and clicked.get("space") == "frame":
        return await start_analysis(
            ctx, asset, match, clicked["points"], "frame", int(clicked.get("frame_ms") or 0)
        )
    refs = await halls.match_references(ctx, asset, only=source.id)
    if not refs:
        raise ProblemError(409, "no-calibration", "The other part has no confirmed court yet")
    return await start_analysis(ctx, asset, match, references=refs)


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
