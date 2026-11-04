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
from handball_vision import formation
from handball_vision import observe as learned
from handball_vision.calibration import (
    Calibration,
    CalibrationError,
    calibrate_points,
    calibrate_pose,
)
from handball_vision.detection import YoloxDetector
from handball_vision.motion import CameraMotion
from handball_vision.pipeline import AnalysisResult, _open, analyse_video, prepare_view
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
) -> dict[str, Any]:
    settings = settings or JobSettings()
    detector = load_detector(settings)
    rep = reporter or Reporter(
        settings.api_internal_url,
        settings.internal_token,
        job_id,
        STAGES_LEARNED if detector is not None else STAGES,
    )
    if detector is not None:
        return _run_learned(
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
        )
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
) -> dict[str, Any]:
    """Learned detector path (ADR 025): one observation pass, automatic calibration, tracking.
    A re-run with clicked points reuses the stored observations and takes seconds."""
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
            obs = learned.observe(
                video,
                detector,
                detect_every=max(1, settings.detect_every),
                progress=lambda _stage, f: rep.fraction(f),
            )
            learned.save_observations(obs, work / "observations.npz")
            upload_dir_files(
                s3, settings.s3_bucket_artifacts, work, ["observations.npz"], prefix + "analysis/"
            )
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
            }
            rep.succeed(pending)
            log.info("analysis_needs_calibration", job_id=job_id, reason=str(exc))
            return pending
        # the motion is saved after calibration (a fixed camera's focal length is set there)
        _store_view(s3, settings.s3_bucket_artifacts, prefix, work, obs.motion)
        rep.stage("tracking")
        bgr = {k: hex_to_bgr(v) for k, v in kits.items() if v}
        result = learned.track(obs, calib, bgr, hall, progress=lambda _stage, f: rep.fraction(f))
        rep.stage("upload")
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


def upload_dir_files(s3: Any, bucket: str, root: Path, names: list[str], prefix: str) -> None:
    for name in names:
        s3.upload_file(str(root / name), bucket, prefix + name, Config=TRANSFER)
