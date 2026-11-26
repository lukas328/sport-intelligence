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

import hashlib
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
from handball_vision import formation, goalcandidates, hallmatch, scoreboard
from handball_vision import observe as learned
from handball_vision.ballnet import BallNet
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


def _entries(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def resolve_models(
    value: str, sha256: str, settings: JobSettings, s3: Any = None
) -> tuple[list[Path], str]:
    """Local files for a model setting (comma-separated local paths or artifacts-bucket keys,
    their SHA-256 in the same order) and a status: "off" (not set), "ok", "missing" (no such
    file or bucket key), "sha_mismatch", "sha_missing" (a bucket key without its checksum).
    Bucket keys are fetched once into `ball_cache_dir` (the model cache; a cached file is reused
    after its checksum matched); local paths are checked against their checksum when one is
    given."""
    names = _entries(value)
    if not names:
        return [], "off"
    shas = _entries(sha256)
    cache = Path(settings.ball_cache_dir)
    paths: list[Path] = []
    for k, name in enumerate(names):
        sha = shas[k].lower() if k < len(shas) else ""
        local = Path(name)
        if not local.is_file():
            if s3 is None:
                return [], "missing"
            if not sha:
                return [], "sha_missing"
            local = cache / f"{sha[:12]}-{Path(name).name}"
            if not local.is_file():
                cache.mkdir(parents=True, exist_ok=True)
                part = local.with_suffix(".part")
                try:
                    s3.download_file(settings.s3_bucket_artifacts, name, str(part), Config=TRANSFER)
                except Exception as exc:  # no such key or storage error: the old path runs
                    log.warning("model_download_failed", key=name, error=str(exc))
                    part.unlink(missing_ok=True)
                    return [], "missing"
                if _sha256(part) != sha:
                    part.unlink(missing_ok=True)
                    return [], "sha_mismatch"
                part.rename(local)
        if sha and _sha256(local) != sha:
            return [], "sha_mismatch"
        paths.append(local)
    return paths, "ok"


def resolve_ball_models(settings: JobSettings, s3: Any = None) -> tuple[list[Path], str]:
    """`resolve_models` for `HB_BALL_MODEL` / `HB_BALL_MODEL_SHA256`."""
    return resolve_models(settings.ball_model, settings.ball_model_sha256, settings, s3)


def _has_cuda() -> bool:
    import onnxruntime as ort

    return "CUDAExecutionProvider" in ort.get_available_providers()


def _cpu_gate(settings: JobSettings, video_s: float | None) -> str | None:
    """Why a GPU-only model may not run here, or None: "no_gpu" without CUDA unless
    `ball_allow_cpu`; "too_long_for_cpu" on a CPU for a video longer than `ball_max_minutes`
    (or of unknown length)."""
    if _has_cuda():
        return None
    if not settings.ball_allow_cpu:
        return "no_gpu"
    if video_s is None or video_s > 60 * settings.ball_max_minutes:
        return "too_long_for_cpu"
    return None


class TooLongError(ValueError):
    """The video is longer than `analysis_max_minutes` (the API reports «too_long»)."""


def _check_length(settings: JobSettings, video_s: float | None) -> None:
    limit = settings.analysis_max_minutes
    if limit > 0 and video_s is not None and video_s > 60 * limit:
        raise TooLongError(
            f"too long for this environment: {video_s / 60:.1f} min, limit {limit:g} min"
        )


def load_ball_net(
    settings: JobSettings, s3: Any = None, video_s: float | None = None
) -> tuple[BallNet | None, str]:
    """The 3-frame ball net(s) of `HB_BALL_MODEL` and the status of `resolve_ball_models`; None
    (the YOLOX ball path stays) unless all files are there with the right checksum and ONNX
    Runtime can use CUDA (`_cpu_gate`: on a CPU only with `ball_allow_cpu` and a short video).
    Test phase:
    the nets contain DeepSport data, see ballnet.py."""
    paths, status = resolve_ball_models(settings, s3)
    if status != "ok":
        if status != "off":
            log.warning("ball_model_unavailable", status=status, model=settings.ball_model)
        return None, status
    gate = _cpu_gate(settings, video_s)
    if gate is not None:
        log.warning("ball_model_needs_gpu", model=settings.ball_model, status=gate)
        return None, gate
    return (
        BallNet(paths, threads=settings.detector_threads or None, width=settings.ball_width),
        status,
    )


def _ball_version(obs: learned.Observations, settings: JobSettings) -> str:
    """Which ball path the result used: the ball net files' names, or the YOLOX boxes."""
    if not getattr(obs, "ball_cands", None):
        return "yolox"
    names = [Path(p).stem for p in _entries(settings.ball_model)]
    return "+".join(names) or "ballnet"


def load_number_reader(settings: JobSettings) -> NumberReader | None:
    det, rec = Path(settings.number_det_model), Path(settings.number_rec_model)
    if not (det.is_file() and rec.is_file()):
        return None
    return NumberReader(det, rec, threads=settings.detector_threads or None)


def load_role_classifier(
    settings: JobSettings, s3: Any = None
) -> tuple[RoleClassifier | None, str]:
    """Player / goalkeeper / referee from appearance (ml/roles), when `HB_ROLE_MODEL` is a local
    file or a bucket key with its checksum (`HB_ROLE_MODEL_SHA256`); and the status of
    `resolve_models` ("missing" for the image default without the file is the normal case)."""
    paths, status = resolve_models(settings.role_model, settings.role_model_sha256, settings, s3)
    if status != "ok":
        return None, status
    return RoleClassifier(paths[0], threads=settings.detector_threads or None), status


def load_embedder(
    settings: JobSettings, s3: Any = None, video_s: float | None = None
) -> tuple[Embedder | None, str]:
    """Person re-identification (`HB_REID_MODEL`, local file or bucket key with
    `HB_REID_MODEL_SHA256`) and the status of `resolve_models`. TEST PHASE: the FastReID weights
    were trained on MSMT17 (non-commercial research only, ml/models/reid-fastreid.md, Q-ML-5);
    not for a real go-live."""
    paths, status = resolve_models(settings.reid_model, settings.reid_model_sha256, settings, s3)
    if status != "ok":
        return None, status
    gate = _cpu_gate(settings, video_s)
    if gate is not None:
        log.warning("reid_model_needs_gpu", model=settings.reid_model, status=gate)
        return None, gate
    return Embedder(paths[0], threads=settings.detector_threads or None), status


CHUNK_MS = 30_000


def write_ball_path(result: AnalysisResult, out: Path) -> int:
    """The ball net's path as `ball.bin` (little-endian float32 rows t_ms, x, y in proxy frame
    pixels, confidence); the number of rows (0: no ball net path, no file)."""
    rows = result.ball_rows
    if rows is None or not len(rows):
        return 0
    (out / "ball.bin").write_bytes(np.asarray(rows, "<f4").tobytes())
    return len(rows)


def video_frames(obs: learned.Observations) -> int:
    """The video's length in frames: `obs.total`, at least one past the last observed frame
    (observations stored before 2026-11-25 kept the last frame index there, one less)."""
    last = obs.frames[-1].index + 1 if obs.frames else 0
    return max(int(getattr(obs, "total", 0) or 0), last)


def ball_summary(
    ball_status: str, ball_rows: int, frames: int, play: dict[str, Any] | None
) -> dict[str, Any]:
    """Short ball figures for the job log and the stats, to judge a test run without reading
    `ball.bin`: the model status, the share of frames with a ball point and how much of the video
    the match clock counted as play (None without clock readings)."""
    in_play = None
    if play and play.get("intervals_ms"):
        in_play = sum(b - a for a, b in play["intervals_ms"]) / 1000
    return {
        "ball_model_status": ball_status,
        "ball_path_points": ball_rows,
        "ball_path_coverage": round(ball_rows / frames, 3) if frames else None,
        "clock_play_s": round(in_play, 1) if in_play is not None else None,
        "clock_readings": (play or {}).get("clock_readings"),
    }


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


def write_view_chunks(motion: CameraMotion, fps: float, out: Path) -> int:
    """Where the moving camera looked, frame by frame (ADR 020 follow-up): `view_NNNNN.bin` per
    CHUNK_MS, little-endian float32 rows [t_ms, h00 .. h22], the homography hall image (panorama)
    px -> proxy frame px, scaled so h22 = 1. The web player composes it with the court calibration
    (court -> panorama) to draw on the moving picture. Frames the motion pass could not place are
    left out (the player hides its drawing there). A fixed camera writes nothing: its calibration
    already refers to the frame. Returns the number of files (0: none)."""
    if not motion.moving or not len(motion) or fps <= 0:
        return 0
    rows: list[list[float]] = []
    for i in range(len(motion)):
        h = motion.canvas_to_frame(i)
        if h is None or not np.isfinite(h).all() or abs(h[2, 2]) < 1e-12:
            continue
        rows.append([round(i * 1000 / fps), *(h / h[2, 2]).ravel().tolist()])
    if not rows:
        return 0
    arr = np.asarray(rows, np.float64)
    last = int(arr[:, 0].max()) // CHUNK_MS
    for n in range(last + 1):
        sel = arr[(arr[:, 0] >= n * CHUNK_MS) & (arr[:, 0] < (n + 1) * CHUNK_MS)]
        (out / f"view_{n:05d}.bin").write_bytes(sel.astype("<f4").tobytes())
    return last + 1


def _view_meta(views: int, motion: CameraMotion) -> dict[str, Any]:
    """`view_chunks` and the proxy frame size they map into, only when there are any."""
    if not views:
        return {}
    return {
        "view_chunks": views,
        "frame_size": [int(motion.frame_size[0]), int(motion.frame_size[1])],
    }


def events_payload(result: AnalysisResult, side_hint: str | None = None) -> dict[str, Any]:
    """Automatic events and possession phases (addendum 01, A3) for the API. `side_hint`: the
    side the home team defends at the start, known beforehand (a second half in its own file)."""
    found = result.detect_events(side_hint)
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
    hall_references: list[dict[str, Any]] | None = None,
    side_hint: str | None = None,
) -> dict[str, Any]:
    """`side_hint` ("left"/"right", optional): the side the home team defends at the start of
    this file when the API knows it (the second half in a file of its own). `rosters` (kit label
    "home"/"away" -> shirt numbers, optional in the job payload) keeps the voted shirt numbers on
    the teams' rosters (learned path only). `hall_references` (earlier videos of the same hall
    with a court a person clicked or confirmed: `video_id`, `panorama_key` in the artifacts
    bucket, `homography` court -> that hall image) are tried before the automatic court (learned
    path only)."""
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
            hall_references,
            side_hint,
        )
        if learned_result is not None:
            return learned_result
        # the detector saw (almost) nobody, e.g. unusual footage: the classical path decides;
        # the API is told, so Prüfen asks nothing and says why (services/checks)
        few_people = True
    else:
        few_people = False
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
        # a kit the API does not know (e.g. the referee's) is left out, not guessed
        bgr = {k: hex_to_bgr(v) for k, v in kits.items() if v}
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
                "calibration_info": {
                    "reason": "few_people" if few_people else getattr(exc, "reason", "court")
                },
                "detector_few_people": few_people,
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
        views = write_view_chunks(motion, result.fps, out)
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
            **_view_meta(views, motion),
            "detector": result.detector_source,
            "versions": {"vision": vision_version},
            "timings_s": {k: round(v, 2) for k, v in result.timings_s.items()},
            "elapsed_s": round(elapsed, 1),
            "stats": result.extra,
            "formations": detect_formations(result),
            "events": events_payload(result, side_hint),
            "scoreboard": None,
            "detector_few_people": few_people,
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


def _hall_calibration(
    s3: Any,
    bucket: str,
    hall: Any,
    references: list[dict[str, Any]],
    work: Path,
    tried: list[dict[str, Any]],
) -> tuple[Calibration, dict[str, Any]] | None:
    """The court of an earlier video of the same hall, carried over by matching the two hall
    images (`hallmatch.register`); the reference with most floor matches wins. None when no
    reference fits (another camera position, another hall, a missing image): each attempt is
    recorded in `tried` and the automatic court takes over."""
    best: tuple[hallmatch.HallMatch, dict[str, Any]] | None = None
    for ref in references[:3]:
        video_id = str(ref.get("video_id") or "")
        path = work / f"hall-{len(tried)}.jpg"
        try:
            s3.download_file(bucket, str(ref["panorama_key"]), str(path), Config=TRANSFER)
            image = cv2.imread(str(path))
            if image is None:
                raise CalibrationError("the earlier hall image is unreadable")
            found = hallmatch.register(image, np.asarray(ref["homography"], dtype=np.float64), hall)
        except CalibrationError as exc:
            tried.append({"video_id": video_id, "error": str(exc)})
            continue
        except Exception as exc:  # a missing image must not stop the analysis
            log.info("hall_reference_unavailable", video_id=video_id, error=str(exc))
            tried.append({"video_id": video_id, "error": "the earlier hall image is missing"})
            continue
        tried.append({"video_id": video_id, "floor_inliers": found.floor_inliers})
        if best is None or found.floor_inliers > best[0].floor_inliers:
            best = (found, ref)
    if best is None:
        return None
    found, ref = best
    info = {
        **found.info(),
        "reference_video_id": str(ref.get("video_id") or ""),
        "hall": ref.get("hall"),
    }
    log.info("hall_calibration", **info)
    return found.calibration, info


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


def goal_candidates(
    obs: learned.Observations, play: dict[str, Any] | None = None
) -> dict[str, Any] | None:
    """Moments that are probably goals, from the camera motion and the people of the observation
    pass (no court needed; the match clock, if read, marks the warm-up): the coach confirms or
    rejects each. Never fails the analysis."""
    try:
        return goalcandidates.from_observations(obs, play=play_intervals(play))
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


def clock_play(
    reader: scoreboard.Reader | None,
    board: HallBoardReader | None,
    duration_ms: int | None = None,
) -> dict[str, Any] | None:
    """Where the match clock runs, from the overlay clock or else the hall scoreboard's: the ball
    analysis counts only there (warm-up balls, ball racks and loose balls in breaks and timeouts
    are not the game ball). None without clock readings: then every ball counts."""
    if reader is not None:
        source, clocks = "overlay", list(reader.clocks)
    elif board is not None:
        source = "hall_scoreboard"
        clocks = [(r.t_ms, r.clock_s) for r in board.readings if r.clock_s is not None]
    else:
        return None
    if not clocks:
        return None
    intervals = scoreboard.play_intervals(clocks, end_ms=duration_ms)
    log.info(
        "clock_play",
        source=source,
        readings=len(clocks),
        intervals=len(intervals),
        in_play_s=round(scoreboard.in_play_ms(intervals) / 1000, 1),
    )
    return {
        "source": source,
        "clock_readings": len(clocks),
        "intervals_ms": [list(iv) for iv in intervals],
    }


def play_intervals(play: dict[str, Any] | None) -> list[tuple[int, int]] | None:
    """The stretches of `clock_play` for the tracking, or None (no running clock: no gating)."""
    found = [(int(a), int(b)) for a, b in (play or {}).get("intervals_ms") or []]
    return found or None


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
    hall_references: list[dict[str, Any]] | None = None,
    side_hint: str | None = None,
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
        # "cached": a re-run on stored observations (their ball candidates, if any, are reused)
        ball_status = reid_status = role_status = "cached"
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
            _check_length(settings, total / fps if fps and total else None)
            reader = _overlay_reader(spread, fps, total / fps if fps else 0.0)
            del spread
            numbers = load_number_reader(settings)
            video_s = total / fps if fps and total else None
            ball_net, ball_status = load_ball_net(settings, s3, video_s)
            embedder, reid_status = load_embedder(settings, s3, video_s)
            roles, role_status = load_role_classifier(settings, s3)
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
                number_gate=settings.number_gate,
                number_budget=settings.number_budget,
                embedder=embedder,
                embed_every=max(1, settings.reid_every),
                roles=roles,
                role_every=max(1, settings.role_every),
                ball_net=ball_net,
                ball_every=max(1, settings.ball_every),
                ball_batch=max(1, settings.ball_batch),
            )
            overlay = _overlay_summary(reader)
            play = clock_play(reader, board, round(1000 * total / fps) if fps and total else None)
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
            (work / "play.json").write_text(json.dumps(play))
            upload_dir_files(
                s3,
                settings.s3_bucket_artifacts,
                work,
                ["observations.npz", "scoreboard.json", "play.json"],
                prefix + "analysis/",
            )
        else:
            overlay = _cached_overlay(s3, settings.s3_bucket_artifacts, prefix, work)
            play = _cached_json(s3, settings.s3_bucket_artifacts, prefix, work, "play.json")
        hall = obs.motion.background()
        view = {
            "camera": "moving" if obs.motion.moving else "fixed",
            "panorama": {"width": int(hall.shape[1]), "height": int(hall.shape[0])},
        }
        rep.stage("calibration")
        info: dict[str, Any] = {}
        tried: list[dict[str, Any]] = []
        try:
            if calibration_points:
                calib = _points_calibration(
                    obs, hall, calibration_points, calibration_space, calibration_frame_ms
                )
            else:
                found = _hall_calibration(
                    s3, settings.s3_bucket_artifacts, hall, hall_references or [], work, tried
                )
                calib, info = found if found is not None else learned.auto_calibrate(obs, hall)
                if found is None and tried:
                    info = {**info, "hall_tried": tried}
        except CalibrationError as exc:
            if calibration_points:
                raise
            _store_view(s3, settings.s3_bucket_artifacts, prefix, work, obs.motion)
            pending: dict[str, Any] = {
                **view,
                "needs_calibration": True,
                "calibration_error": str(exc),
                # why: camera_motion, no_floor, flat_view, few_people or court (ADR 025)
                "calibration_info": {
                    "reason": getattr(exc, "reason", "court"),
                    **({"hall_tried": tried} if tried else {}),
                },
                "calibration": None,
                "tracks": [],
                "fps": obs.fps,
                "frames": 0,
                "chunks": 0,
                "chunk_ms": CHUNK_MS,
                "detector": "model",
                "versions": {
                    "vision": vision_version,
                    "detector": detector.model,
                    "ball": _ball_version(obs, settings),
                },
                "timings_s": {k: round(v, 2) for k, v in obs.timings_s.items()},
                "elapsed_s": round(time.perf_counter() - started, 1),
                "stats": {
                    "camera": view["camera"],
                    "motion": obs.motion.stats,
                    "ball_model_status": ball_status,
                    "reid_model_status": reid_status,
                    "role_model_status": role_status,
                    "observe_counters": getattr(obs, "counters", {}),
                },
                "formations": [],
                "scoreboard": overlay,
                "goal_candidates": goal_candidates(obs, play),
            }
            rep.succeed(pending)
            log.info(
                "analysis_needs_calibration",
                job_id=job_id,
                reason=str(exc),
                # no ball path without the court: only the model status and the clock
                **ball_summary(ball_status, 0, 0, play),
            )
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
            play=play_intervals(play),
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
        views = write_view_chunks(obs.motion, result.fps, out)
        ball_rows = write_ball_path(result, out)
        # ball rows are per video frame; result.frames counts the detection frames only
        ball_info = ball_summary(ball_status, ball_rows, video_frames(obs), play)
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
            **_view_meta(views, obs.motion),
            "detector": result.detector_source,
            "versions": {
                "vision": vision_version,
                "detector": detector.model,
                "ball": _ball_version(obs, settings),
            },
            "timings_s": {k: round(v, 2) for k, v in result.timings_s.items()},
            "elapsed_s": round(time.perf_counter() - started, 1),
            "stats": {
                **result.extra,
                "ball_model_status": ball_status,
                "reid_model_status": reid_status,
                "role_model_status": role_status,
                "observe_counters": getattr(obs, "counters", {}),
                "ball_summary": ball_info,
            },
            "formations": detect_formations(result),
            "events": events_payload(result, side_hint),
            "scoreboard": overlay,
            "goal_candidates": goals,
            "ball_path": {"file": "ball.bin", "rows": ball_rows} if ball_rows else None,
        }
        rep.succeed(payload)
        log.info(
            "analysis_done",
            job_id=job_id,
            tracks=len(payload["tracks"]),
            elapsed_s=payload["elapsed_s"],
            reid_model_status=reid_status,
            **ball_info,
            **getattr(obs, "counters", {}),
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
    return _cached_json(s3, bucket, prefix, work, "scoreboard.json")


def _cached_json(s3: Any, bucket: str, prefix: str, work: Path, name: str) -> dict[str, Any] | None:
    path = work / name
    try:
        s3.download_file(bucket, prefix + "analysis/" + name, str(path), Config=TRANSFER)
        data = json.loads(path.read_text())
        return data if isinstance(data, dict) else None
    except Exception:  # an earlier run without overlay or clock reading
        return None


def upload_dir_files(s3: Any, bucket: str, root: Path, names: list[str], prefix: str) -> None:
    for name in names:
        s3.upload_file(str(root / name), bucket, prefix + name, Config=TRANSFER)
