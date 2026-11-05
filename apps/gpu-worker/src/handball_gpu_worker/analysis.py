"""Pipeline stages 2 to 5 on the analysis proxy (BRIEF 7.2).

Runs on the `gpu` queue (local backend on CPU until a GPU provider is configured). Writes:
- `analysis/tracks.parquet`: all track points (pipeline and detector version in the metadata)
- `analysis/chunk_NNNNN.bin`: 30 s chunks for the browser, packed little-endian float32 rows
  [t_ms, track_id, x, y] (BRIEF 6.4: compact binary instead of JSON)
- `analysis/panorama.jpg`: the hall image users click court points on (panorama of a moving
  camera, median frame of a fixed one) and `analysis/motion.npz`: camera motion + panorama, reused
  when the analysis re-runs with clicked points (same panorama coordinates, no second motion pass)
and reports calibration, per-track summary, timings and cost to the API. If the court cannot be
found automatically, the job still succeeds with `needs_calibration` and the hall image, so the user
can mark the court instead of seeing an error.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import structlog

from handball_jobkit import TRANSFER, JobSettings, Reporter, s3_client, upload_dir
from handball_vision import __version__ as vision_version
from handball_vision import formation, goalcandidates, scoreboard
from handball_vision import observe as learned
from handball_vision.calibration import (
    Calibration,
    CalibrationError,
    calibrate_points,
    calibrate_pose,
)
from handball_vision.detection import YoloxDetector
from handball_vision.hallboard import HallBoardReader
from handball_vision.motion import CameraMotion
from handball_vision.numbers import NumberReader
from handball_vision.pipeline import (
    AnalysisResult,
    _open,
    analyse_video,
    prepare_view,
    sample_frames,
)
from handball_vision.reid import Embedder
from handball_vision.roles import RoleClassifier
from handball_vision.shots import locate_goal_shots
from handball_vision.teams import hex_to_bgr

log = structlog.get_logger("gpu.analysis")

STAGES = {"download": 0.05, "calibration": 0.1, "tracking": 0.75, "upload": 0.1}
# with the learned detector the single observation pass dominates (ADR 025)
STAGES_LEARNED = {
    "download": 0.03,
    "observe": 0.72,
    "calibration": 0.12,
    "tracking": 0.05,
    "upload": 0.08,
}


def load_detector(settings: JobSettings) -> YoloxDetector | None:
    """The learned person detector if its weights are installed, else None (classical path)."""
    path = Path(settings.detector_model)
    if not path.is_file():
        return None
    return YoloxDetector(path, threads=settings.detector_threads or None)


def load_number_reader(settings: JobSettings) -> NumberReader | None:
    det, rec = Path(settings.number_det_model), Path(settings.number_rec_model)
    if not (det.is_file() and rec.is_file()):
        return None
    return NumberReader(det, rec, threads=settings.detector_threads or None)


def load_role_classifier(settings: JobSettings) -> RoleClassifier | None:
    """Player / goalkeeper / referee from appearance, when the model is installed (ml/roles)."""
    path = Path(settings.role_model)
    return (
        RoleClassifier(path, threads=settings.detector_threads or None) if path.is_file() else None
    )


def load_embedder(settings: JobSettings) -> Embedder | None:
    path = Path(settings.reid_model)
    return Embedder(path, threads=settings.detector_threads or None) if path.is_file() else None


CHUNK_MS = 30_000


def write_chunks(result: AnalysisResult, out: Path) -> int:
    rows = np.array(
        [[round(p.frame * 1000 / result.fps), p.track_id, p.x, p.y] for p in result.points],
        dtype=np.float32,
    ).reshape(-1, 4)
    count = 0
    if len(rows) == 0:
        return 0
    last = int(rows[:, 0].max()) // CHUNK_MS
    for n in range(last + 1):
        sel = rows[(rows[:, 0] >= n * CHUNK_MS) & (rows[:, 0] < (n + 1) * CHUNK_MS)]
        (out / f"chunk_{n:05d}.bin").write_bytes(sel.astype("<f4").tobytes())
        count += 1
    return count


def events_payload(result: AnalysisResult) -> dict[str, Any]:
    """Automatic events and possession phases (addendum 01, A3) for the API."""
    found = result.detect_events()
    return {
        "events": [
            {
                "t_ms": e.t_ms,
                "type": e.type,
                "team": e.team,
                "confidence": e.confidence,
                **e.attributes,
            }
            for e in found.events
        ],
        "possessions": [
            {
                "team": p.team,
                "start_ms": p.start_ms,
                "end_ms": p.end_ms,
                "confidence": p.confidence,
                "outcome": p.outcome,
                "phase": p.phase,
            }
            for p in found.possessions
        ],
        "sides": [{"from_ms": t, "home_defends": side} for t, side in found.sides],
        "missing": found.missing,
    }


def detect_formations(result: AnalysisResult) -> list[dict[str, Any]]:
    labels = {tid: str(v.get("label")) for tid, v in result.teams.items() if v.get("label")}
    samples = [
        formation.Sample(
            round(p.frame * 1000 / result.fps), p.track_id, labels[p.track_id], p.x, p.y
        )
        for p in result.points
        if p.track_id in labels
    ]
    return [s.to_dict() for s in formation.detect(samples)]


def _load_motion(
    s3: Any, bucket: str, prefix: str, work: Path, points: list[Any] | None
) -> CameraMotion | None:
    """Camera motion of an earlier run (only when re-running with clicked points)."""
    if not points:
        return None
    path = work / "motion.npz"
    try:
        s3.download_file(bucket, prefix + "analysis/motion.npz", str(path), Config=TRANSFER)
        return CameraMotion.load(path)
    except Exception as exc:  # missing or unreadable: estimate again
        log.info("motion_cache_miss", error=str(exc))
        return None


def _store_view(s3: Any, bucket: str, prefix: str, work: Path, motion: CameraMotion) -> None:
    out = work / "view"
    out.mkdir(exist_ok=True)
    hall = motion.background()
    cv2.imwrite(str(out / "panorama.jpg"), hall, [cv2.IMWRITE_JPEG_QUALITY, 85])
    motion.save(out / "motion.npz")
    upload_dir(s3, bucket, out, prefix + "analysis/")


def run_analysis(
    job_id: str,
    organization_id: str,
    match_id: str,
    asset_id: str,
    bucket: str,
    proxy_key: str,
    prefix: str,
    kits: dict[str, str],
    calibration_points: list[dict[str, Any]] | None = None,
    calibration_space: str = "frame",
    calibration_frame_ms: int = 0,
    settings: JobSettings | None = None,
    reporter: Reporter | None = None,
    own_is_home: bool = True,
    rosters: dict[str, list[int]] | None = None,
) -> dict[str, Any]:
    """`rosters` (kit label "home"/"away" -> shirt numbers, optional in the job payload) keeps
    the voted shirt numbers on the teams' rosters (learned path only)."""
    settings = settings or JobSettings()
    detector = load_detector(settings)
    rep = reporter or Reporter(
        settings.api_internal_url,
        settings.internal_token,
        job_id,
        STAGES_LEARNED if detector is not None else STAGES,
    )
    if detector is not None:
        learned_result = _run_learned(
            detector,
            job_id,
            bucket,
            proxy_key,
            prefix,
            kits,
            calibration_points,
            calibration_space,
            calibration_frame_ms,
            settings,
            rep,
            own_is_home,
            rosters,
        )
        if learned_result is not None:
            return learned_result
        # the detector saw (almost) nobody, e.g. unusual footage: the classical path decides
    Path(settings.work_dir).mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix=f"analysis-{asset_id}-", dir=settings.work_dir))
    started = time.perf_counter()
    try:
        s3 = s3_client(
            settings.s3_endpoint_url,
            settings.s3_region,
            settings.s3_access_key,
            settings.s3_secret_key,
        )
        rep.stage("download")
        video = work / "proxy.mp4"
        s3.download_file(bucket, proxy_key, str(video), Config=TRANSFER)

        rep.stage("calibration")
        motion = _load_motion(s3, settings.s3_bucket_artifacts, prefix, work, calibration_points)
        if motion is None:
            motion = prepare_view(video)
            _store_view(s3, settings.s3_bucket_artifacts, prefix, work, motion)
        hall = motion.background()
        view = {
            "camera": "moving" if motion.moving else "fixed",
            "panorama": {"width": int(hall.shape[1]), "height": int(hall.shape[0])},
        }
        _, _, fps, _ = _open(video)
        calib = None
        space = "panorama" if calibration_space == "panorama" else "frame"
        if calibration_points:
            size = (hall.shape[1], hall.shape[0]) if space == "panorama" else motion.frame_size
            calib = calibrate_points(
                [(p["image"][0], p["image"][1]) for p in calibration_points],
                [(p["court"][0], p["court"][1]) for p in calibration_points],
                size,
            )
        bgr = {k: hex_to_bgr(v) for k, v in kits.items()}
        rep.stage("tracking")
        try:
            result = analyse_video(
                video,
                bgr,
                calibration=calib,
                calibration_frame=round(calibration_frame_ms * fps / 1000),
                calibration_space=space,  # type: ignore[arg-type]
                motion=motion,
                progress=lambda stage, f: rep.fraction(f) if stage == "tracking" else None,
            )
        except CalibrationError as exc:
            if calib is not None:
                raise
            # automatic calibration failed: not an error for the user, they mark the court
            pending: dict[str, Any] = {
                **view,
                "needs_calibration": True,
                "calibration_error": str(exc),
                "calibration": None,
                "tracks": [],
                "fps": fps,
                "frames": 0,
                "chunks": 0,
                "chunk_ms": CHUNK_MS,
                "detector": "heuristic",
                "versions": {"vision": vision_version},
                "timings_s": {},
                "elapsed_s": round(time.perf_counter() - started, 1),
                "stats": {"camera": view["camera"], "motion": motion.stats},
                "formations": [],
            }
            rep.succeed(pending)
            log.info("analysis_needs_calibration", job_id=job_id, reason=str(exc))
            return pending

        rep.stage("upload")
        out = work / "analysis"
        out.mkdir()
        result.write_parquet(out / "tracks.parquet")
        chunks = write_chunks(result, out)
        upload_dir(s3, settings.s3_bucket_artifacts, out, prefix + "analysis/")
        elapsed = time.perf_counter() - started
        tracks = result.summary()
        payload: dict[str, Any] = {
            **view,
            "needs_calibration": False,
            "calibration": result.calibration.to_dict(),
            "tracks": tracks,
            "fps": result.fps,
            "frames": result.frames,
            "chunks": chunks,
            "chunk_ms": CHUNK_MS,
            "detector": result.detector_source,
            "versions": {"vision": vision_version},
            "timings_s": {k: round(v, 2) for k, v in result.timings_s.items()},
            "elapsed_s": round(elapsed, 1),
            "stats": result.extra,
            "formations": detect_formations(result),
            "events": events_payload(result),
            "scoreboard": None,
        }
        rep.succeed(payload)
        log.info(
            "analysis_done",
            job_id=job_id,
            tracks=len(payload["tracks"]),
            elapsed_s=payload["elapsed_s"],
        )
        return payload
    except CalibrationError as exc:
        rep.fail(f"calibration: {exc}")
        raise
    except Exception as exc:
        rep.fail(f"{type(exc).__name__}: {exc}")
        raise
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _points_calibration(
    obs: learned.Observations,
    hall: Any,
    points: list[dict[str, Any]],
    space: str,
    frame_ms: int,
) -> Calibration:
    """Calibration from clicked points, in hall-image (panorama) coordinates.

    With a known camera (focal length from the motion) only the pose is fitted, which needs fewer
    and less spread points (the four goal-post feet are enough; crossbar points carry z = 2 m);
    without it, or if the pose fit fails, a plain homography."""
    motion = obs.motion
    image = [(float(p["image"][0]), float(p["image"][1])) for p in points]
    court3 = [
        (float(p["court"][0]), float(p["court"][1]), float(p.get("height_m", 0.0) or 0.0))
        for p in points
    ]
    if space != "panorama" and motion.moving:
        index = round(frame_ms * obs.fps / 1000)
        to_canvas = motion.frame_to_canvas(index)
        if to_canvas is None:
            raise CalibrationError("the calibrated frame could not be placed on the panorama")
        pts = cv2.perspectiveTransform(np.array(image, np.float64).reshape(-1, 1, 2), to_canvas)
        image = [(float(x), float(y)) for x, y in pts.reshape(-1, 2)]
    size = (int(hall.shape[1]), int(hall.shape[0]))
    if motion.moving and len(points) >= 4:
        try:
            return calibrate_pose(image, court3, motion.canvas_intrinsics(), size)
        except CalibrationError as exc:
            log.info("pose_calibration_failed", error=str(exc))
    flat = [(x, y) for x, y, z in court3 if z == 0.0]
    flat_img = [im for im, c in zip(image, court3, strict=True) if c[2] == 0.0]
    return calibrate_points(flat_img, flat, size)


def _cached_observations(
    s3: Any, bucket: str, prefix: str, work: Path
) -> learned.Observations | None:
    try:
        s3.download_file(
            bucket, prefix + "analysis/motion.npz", str(work / "motion.npz"), Config=TRANSFER
        )
        s3.download_file(
            bucket,
            prefix + "analysis/observations.npz",
            str(work / "observations.npz"),
            Config=TRANSFER,
        )
        return learned.load_observations(
            work / "observations.npz", CameraMotion.load(work / "motion.npz")
        )
    except Exception as exc:  # missing or unreadable: observe again
        log.info("observation_cache_miss", error=str(exc))
        return None


def goal_candidates(obs: learned.Observations) -> dict[str, Any] | None:
    """Moments that are probably goals, from the camera motion and the people of the observation
    pass (no court needed): the coach confirms or rejects each. Never fails the analysis."""
    try:
        return goalcandidates.from_observations(obs)
    except Exception as exc:  # pragma: no cover - defensive
        log.warning("goal_candidates_failed", error=str(exc))
        return None


def _people(found: list[Any]) -> list[Any]:
    return [d for d in found if d.cls != "ball"]


def _overlay_reader(frames: list[Any], fps: float, duration_s: float) -> scoreboard.Reader | None:
    """A reader for a broadcast score overlay, or None (no overlay, no Tesseract). Never fails
    the analysis: the overlay is an extra source."""
    if not scoreboard.available() or not frames:
        return None
    try:
        boxes = scoreboard.find_overlay(frames)
        if not boxes:
            return None
        h, w = frames[0].shape[:2]
        x, y, bw, bh = scoreboard._union(boxes, 6, (w, h))
        n = len(frames)
        crops = [
            (duration_s * (k + 0.5) / n, frames[k][y : y + bh, x : x + bw])
            for k in range(0, n, max(1, n // 8))
        ]
        fields = scoreboard.find_fields(crops, (x, y))
        if not any(f.kind == "score" for f in fields):
            return None
        log.info("score_overlay_found", fields=[(f.kind, f.box) for f in fields])
        return scoreboard.Reader(fields, fps)
    except Exception as exc:  # pragma: no cover - defensive
        log.warning("score_overlay_failed", error=str(exc))
        return None


def _overlay_summary(reader: scoreboard.Reader | None) -> dict[str, Any] | None:
    if reader is None:
        return None
    summary = scoreboard.read_overlay_summary(reader)
    return summary if summary["first_score"] is not None else None


def _run_learned(
    detector: YoloxDetector,
    job_id: str,
    bucket: str,
    proxy_key: str,
    prefix: str,
    kits: dict[str, str],
    calibration_points: list[dict[str, Any]] | None,
    calibration_space: str,
    calibration_frame_ms: int,
    settings: JobSettings,
    rep: Reporter,
    own_is_home: bool = True,
    rosters: dict[str, list[int]] | None = None,
) -> dict[str, Any] | None:
    """Learned detector path (ADR 025): one observation pass, automatic calibration, tracking.
    A re-run with clicked points reuses the stored observations and takes seconds. Returns None
    when the detector finds (almost) no people, so the classical path can take over."""
    Path(settings.work_dir).mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="analysis-", dir=settings.work_dir))
    started = time.perf_counter()
    try:
        s3 = s3_client(
            settings.s3_endpoint_url,
            settings.s3_region,
            settings.s3_access_key,
            settings.s3_secret_key,
        )
        rep.stage("download")
        obs = (
            _cached_observations(s3, settings.s3_bucket_artifacts, prefix, work)
            if calibration_points
            else None
        )
        rep.stage("observe")
        if obs is None:
            video = work / "proxy.mp4"
            s3.download_file(bucket, proxy_key, str(video), Config=TRANSFER)
            # a quick look first: a detector that sees nobody on a dozen frames spread over the
            # video would not see more in a full pass (unusual footage, drawn test videos)
            spread = sample_frames(video, 36)
            seen = sorted(len(_people(d)) for d in detector.detect(spread[::3]))
            if not seen or seen[len(seen) // 2] < 3:
                log.info("detector_sees_few_people", median=seen[len(seen) // 2] if seen else 0)
                return None
            _, _, fps, total = _open(video)
            reader = _overlay_reader(spread, fps, total / fps if fps else 0.0)
            del spread
            numbers = load_number_reader(settings)
            # no overlay: the hall's own scoreboard, when the camera shows it (raw recordings)
            board = (
                HallBoardReader(
                    numbers,
                    fps,
                    every_s=settings.hallboard_every_s,
                    full_every_s=settings.hallboard_full_every_s,
                    probe_every_s=settings.hallboard_probe_every_s,
                )
                if reader is None and numbers is not None and fps
                else None
            )
            obs = learned.observe(
                video,
                detector,
                detect_every=max(1, settings.detect_every),
                progress=lambda _stage, f: rep.fraction(f),
                on_frame=reader.add if reader else (board.add if board else None),
                numbers=numbers,
                number_every=max(1, settings.number_every),
                embedder=load_embedder(settings),
                embed_every=max(1, settings.reid_every),
                roles=load_role_classifier(settings),
                role_every=max(1, settings.role_every),
            )
            overlay = _overlay_summary(reader)
            if overlay is None and board is not None:
                board_summary = board.summary()
                overlay = board_summary if board_summary["goals"] else None
                log.info(
                    "hall_scoreboard",
                    readings=board_summary["readings"],
                    goals=len(board_summary["goals"]),
                )
            counts = sorted(len(fo.people) for fo in obs.frames)
            if not counts or counts[len(counts) // 2] < 3:
                log.info(
                    "detector_sees_few_people", median=counts[len(counts) // 2] if counts else 0
                )
                return None
            learned.save_observations(obs, work / "observations.npz")
            (work / "scoreboard.json").write_text(json.dumps(overlay))
            upload_dir_files(
                s3,
                settings.s3_bucket_artifacts,
                work,
                ["observations.npz", "scoreboard.json"],
                prefix + "analysis/",
            )
        else:
            overlay = _cached_overlay(s3, settings.s3_bucket_artifacts, prefix, work)
        hall = obs.motion.background()
        view = {
            "camera": "moving" if obs.motion.moving else "fixed",
            "panorama": {"width": int(hall.shape[1]), "height": int(hall.shape[0])},
        }
        rep.stage("calibration")
        info: dict[str, Any] = {}
        try:
            if calibration_points:
                calib = _points_calibration(
                    obs, hall, calibration_points, calibration_space, calibration_frame_ms
                )
            else:
                calib, info = learned.auto_calibrate(obs, hall)
        except CalibrationError as exc:
            if calibration_points:
                raise
            _store_view(s3, settings.s3_bucket_artifacts, prefix, work, obs.motion)
            pending: dict[str, Any] = {
                **view,
                "needs_calibration": True,
                "calibration_error": str(exc),
                "calibration": None,
                "tracks": [],
                "fps": obs.fps,
                "frames": 0,
                "chunks": 0,
                "chunk_ms": CHUNK_MS,
                "detector": "model",
                "versions": {"vision": vision_version, "detector": detector.model},
                "timings_s": {k: round(v, 2) for k, v in obs.timings_s.items()},
                "elapsed_s": round(time.perf_counter() - started, 1),
                "stats": {"camera": view["camera"], "motion": obs.motion.stats},
                "formations": [],
                "scoreboard": overlay,
                "goal_candidates": goal_candidates(obs),
            }
            rep.succeed(pending)
            log.info("analysis_needs_calibration", job_id=job_id, reason=str(exc))
            return pending
        # the motion is saved after calibration (a fixed camera's focal length is set there)
        _store_view(s3, settings.s3_bucket_artifacts, prefix, work, obs.motion)
        rep.stage("tracking")
        bgr = {k: hex_to_bgr(v) for k, v in kits.items() if v}
        numbers_on = {k: set(v) for k, v in (rosters or {}).items() if v}
        result = learned.track(
            obs,
            calib,
            bgr,
            hall,
            progress=lambda _stage, f: rep.fraction(f),
            rosters=numbers_on or None,
        )
        if overlay and overlay.get("goals"):
            # where the goals were scored from: the scorer's track, else the nearest attacker
            overlay = {
                **overlay,
                "goals": locate_goal_shots(
                    result.points, result.teams, result.fps, overlay["goals"], own_is_home
                ),
            }
        rep.stage("upload")
        # computed by the tracking stage from the observations; sent on its own, not as a stat
        goals = result.extra.pop("goal_candidates", None)
        out = work / "analysis"
        out.mkdir()
        result.write_parquet(out / "tracks.parquet")
        chunks = write_chunks(result, out)
        upload_dir(s3, settings.s3_bucket_artifacts, out, prefix + "analysis/")
        payload: dict[str, Any] = {
            **view,
            "needs_calibration": False,
            "calibration": result.calibration.to_dict(),
            "calibration_info": info,
            "tracks": result.summary(),
            "fps": result.fps,
            "frames": result.frames,
            "chunks": chunks,
            "chunk_ms": CHUNK_MS,
            "detector": result.detector_source,
            "versions": {"vision": vision_version, "detector": detector.model},
            "timings_s": {k: round(v, 2) for k, v in result.timings_s.items()},
            "elapsed_s": round(time.perf_counter() - started, 1),
            "stats": result.extra,
            "formations": detect_formations(result),
            "events": events_payload(result),
            "scoreboard": overlay,
            "goal_candidates": goals,
        }
        rep.succeed(payload)
        log.info(
            "analysis_done",
            job_id=job_id,
            tracks=len(payload["tracks"]),
            elapsed_s=payload["elapsed_s"],
        )
        return payload
    except CalibrationError as exc:
        rep.fail(f"calibration: {exc}")
        raise
    except Exception as exc:
        rep.fail(f"{type(exc).__name__}: {exc}")
        raise
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _cached_overlay(s3: Any, bucket: str, prefix: str, work: Path) -> dict[str, Any] | None:
    path = work / "scoreboard.json"
    try:
        s3.download_file(bucket, prefix + "analysis/scoreboard.json", str(path), Config=TRANSFER)
        data = json.loads(path.read_text())
        return data if isinstance(data, dict) else None
    except Exception:  # an earlier run without overlay reading
        return None


def upload_dir_files(s3: Any, bucket: str, root: Path, names: list[str], prefix: str) -> None:
    for name in names:
        s3.upload_file(str(root / name), bucket, prefix + name, Config=TRANSFER)
