"""Stages 2 to 5 as one streaming pass (BRIEF 6.3): calibration, detection, tracking, teams.

The proxy video is decoded as a stream (PyAV), frames never touch the disk. Calibration and the
background model use frames sampled across the whole video (first, seek-based pass). The second
pass detects on every `detect_every`-th frame and lets the tracker predict in between (cascade).
Results are tables (Arrow/Parquet) with pipeline and model versions; timings are recorded per stage.

Moving cameras (pan, tilt, zoom; detected by `camera_moves`) get an extra pass first: the camera
motion is estimated (`motion.py`), a panorama of the hall is built and calibrated once, and every
frame gets its own court homography and a background rendered from the panorama. Detection,
tracking and teams then run unchanged in court coordinates.
"""

from __future__ import annotations

import time
from collections import defaultdict
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import av
import cv2
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from numpy.typing import NDArray

from handball_vision import __version__
from handball_vision.calibration import Calibration, CalibrationError, calibrate_frames
from handball_vision.detection import (
    BackgroundDetector,
    Detection,
    Detector,
    MovingBackgroundDetector,
    court_mask,
    foot_positions,
)
from handball_vision.motion import CameraMotion, estimate_motion
from handball_vision.physical import physical
from handball_vision.teams import TeamAssigner
from handball_vision.tracking import CourtTracker, TrackPoint, stitch

U8 = NDArray[Any]  # images (OpenCV returns loosely typed arrays)
Progress = Callable[[str, float], None]


@dataclass
class AnalysisResult:
    calibration: Calibration
    fps: float
    frames: int
    points: list[TrackPoint]
    teams: dict[int, dict[str, Any]]
    timings_s: dict[str, float]
    detector_source: str
    version: str = __version__
    detections_per_frame: float = 0.0
    extra: dict[str, Any] = field(default_factory=dict)

    def tracks_table(self) -> pa.Table:
        p = self.points
        return pa.table(
            {
                "frame": pa.array([x.frame for x in p], pa.int32()),
                "t_ms": pa.array([round(x.frame * 1000 / self.fps) for x in p], pa.int32()),
                "track_id": pa.array([x.track_id for x in p], pa.int32()),
                "x": pa.array([x.x for x in p], pa.float32()),
                "y": pa.array([x.y for x in p], pa.float32()),
                "vx": pa.array([x.vx for x in p], pa.float32()),
                "vy": pa.array([x.vy for x in p], pa.float32()),
                "observed": pa.array([x.observed for x in p], pa.bool_()),
            }
        )

    def write_parquet(self, path: Path) -> None:
        table = self.tracks_table().replace_schema_metadata(
            {
                b"pipeline": f"handball_vision {self.version}".encode(),
                b"detector": self.detector_source.encode(),
            }
        )
        pq.write_table(table, path, compression="zstd")

    def summary(self) -> list[dict[str, Any]]:
        by_track: dict[int, list[TrackPoint]] = defaultdict(list)
        for pt in self.points:
            by_track[pt.track_id].append(pt)
        out = []
        for tid, pts in sorted(by_track.items()):
            team = self.teams.get(tid, {})
            out.append(
                {
                    "track_id": tid,
                    "first_ms": round(pts[0].frame * 1000 / self.fps),
                    "last_ms": round(pts[-1].frame * 1000 / self.fps),
                    "points": len(pts),
                    "observed_share": round(sum(p.observed for p in pts) / len(pts), 3),
                    "team": team.get("label"),
                    "team_confidence": team.get("confidence"),
                    "physical": physical(
                        np.array([p.frame * 1000 / self.fps for p in pts]),
                        np.array([p.x for p in pts]),
                        np.array([p.y for p in pts]),
                    ).to_dict(),
                }
            )
        return out


def _open(path: Path) -> tuple[Any, Any, float, int]:
    container = av.open(str(path))
    stream = container.streams.video[0]
    stream.thread_type = "AUTO"
    fps = float(stream.average_rate or 25)
    total = int(stream.frames or 0) or int(
        (float(stream.duration or 0) * float(stream.time_base or 0)) * fps
    )
    return container, stream, fps, total


def iter_frames(path: Path) -> Iterator[U8]:
    container, stream, _, _ = _open(path)
    try:
        for frame in container.decode(stream):
            yield frame.to_ndarray(format="bgr24")
    finally:
        container.close()


def sample_frames(path: Path, count: int) -> list[U8]:
    """Frames spread across the video via seeking (fast, no full decode)."""
    container, stream, _, _ = _open(path)
    try:
        duration = float(container.duration or 0) / av.time_base
        out: list[U8] = []
        for k in range(count):
            target = duration * (k + 0.5) / count
            container.seek(
                int(target / float(stream.time_base)), stream=stream, any_frame=False, backward=True
            )
            for frame in container.decode(stream):
                if frame.time is not None and frame.time >= target - 0.05:
                    out.append(frame.to_ndarray(format="bgr24"))
                    break
        return out
    finally:
        container.close()


def camera_moves(path: Path, probes: int = 16, threshold_px: float = 1.5) -> bool:
    """Cheap check before the motion pass: feature shift over 5 frames at a few places.

    An operator only pans when play moves, so the camera is still at many probes; two probes with
    a clear shift of the background (median over features, players are a minority) are enough.
    """
    container, stream, _, _ = _open(path)
    try:
        duration = float(container.duration or 0) / av.time_base
        shifts: list[float] = []
        for k in range(probes):
            target = duration * (k + 0.5) / probes
            container.seek(
                int(target / float(stream.time_base)), stream=stream, any_frame=False, backward=True
            )
            grabbed: list[U8] = []
            for frame in container.decode(stream):
                if frame.time is None or frame.time < target - 0.05:
                    continue
                img = frame.to_ndarray(format="gray")
                grabbed.append(cv2.resize(img, (480, round(img.shape[0] * 480 / img.shape[1]))))
                if len(grabbed) == 6:
                    break
            if len(grabbed) < 6:
                continue
            pts = cv2.goodFeaturesToTrack(grabbed[0], 200, 0.01, 8)
            if pts is None:
                continue
            nxt, st, _ = cv2.calcOpticalFlowPyrLK(grabbed[0], grabbed[5], pts, None)  # type: ignore[call-overload]
            ok = st.ravel() == 1
            if ok.sum() >= 10:
                shifts.append(
                    float(np.median(np.linalg.norm((nxt - pts)[ok].reshape(-1, 2), axis=1)))
                )
        return sum(s > threshold_px for s in shifts) >= 2
    finally:
        container.close()


def prepare_view(path: Path, max_frames: int | None = None) -> CameraMotion:
    """Camera motion and the hall image (panorama, or the median frame of a fixed camera).

    The hall image is what the user clicks court points on; `motion.background()` returns it.
    """
    if camera_moves(path):
        _, _, _, total = _open(path)
        if max_frames is not None:
            total = min(total, max_frames) if total else max_frames
        motion = estimate_motion(_frames(path, max_frames), expected_frames=total)
        if motion.moving:
            motion.background()
            return motion
    container, stream, _, total = _open(path)
    size = (stream.codec_context.width, stream.codec_context.height)
    container.close()
    fixed = CameraMotion.fixed(size, total or 1)
    fixed.panorama = np.median(np.stack(sample_frames(path, 48)[::2]), axis=0).astype(np.uint8)
    return fixed


def _confident_label(
    teams: TeamAssigner, colour: NDArray[np.float64], min_conf: float = 0.25
) -> str | None:
    label, conf = teams.classify(colour)
    return label if conf >= min_conf else None


def analyse_video(
    path: Path,
    kits: dict[str, tuple[int, int, int]],
    detect_every: int = 1,
    detector: Detector | None = None,
    calibration: Calibration | None = None,
    progress: Progress | None = None,
    max_frames: int | None = None,
    calibration_frame: int = 0,
    motion: CameraMotion | bool | None = None,
    calibration_space: Literal["frame", "panorama"] = "frame",
) -> AnalysisResult:
    """Analyse a match video.

    `calibration` (e.g. from clicked points) refers to frame `calibration_frame`, or with
    `calibration_space="panorama"` to the hall image (`prepare_view`); for a fixed camera both are
    the same. `motion`: None = detect, False = treat as fixed camera, True = estimate, or a
    precomputed `CameraMotion` (fixed or moving).
    """
    hall: U8 | None = None
    if isinstance(motion, CameraMotion) and not motion.moving:
        hall = motion.panorama
        motion = False
    if motion is None:
        motion = camera_moves(path)
    if motion is not False:
        return _analyse_moving(
            path,
            kits,
            detect_every,
            detector,
            calibration,
            calibration_frame,
            progress,
            max_frames,
            motion if isinstance(motion, CameraMotion) else None,
            calibration_space,
        )
    timings: dict[str, float] = defaultdict(float)
    t0 = time.perf_counter()
    samples = sample_frames(path, 48)
    timings["sample"] += time.perf_counter() - t0
    if progress:
        progress("calibration", 0.0)
    t0 = time.perf_counter()
    calib = calibration or calibrate_frames([hall] if hall is not None else samples[::2])
    timings["calibration"] += time.perf_counter() - t0

    det = detector or BackgroundDetector(calib)
    if isinstance(det, BackgroundDetector):
        det.warm_up(samples)
    floor = (
        det.background.reshape(-1, 3).astype(np.float64).mean(axis=0)
        if isinstance(det, BackgroundDetector) and det.background is not None
        else None
    )
    teams = TeamAssigner(kits, floor_lab=floor)
    _, _, fps, total = _open(path)
    tracker = CourtTracker(fps=fps)
    points: list[TrackPoint] = []
    n = 0
    n_dets = 0
    for frame in iter_frames(path):
        if max_frames is not None and n >= max_frames:
            break
        dets: list[Detection] = []
        if n % detect_every == 0:
            t0 = time.perf_counter()
            dets = [d for d in det.detect([frame])[0] if d.cls != "ball"]
            timings["detection"] += time.perf_counter() - t0
        n_dets += len(dets)
        t0 = time.perf_counter()
        feats = np.array(
            [c if (c := teams.torso_colour(frame, d)) is not None else [np.nan] * 3 for d in dets]
        ).reshape(-1, 3)
        timings["appearance"] += time.perf_counter() - t0
        t0 = time.perf_counter()
        pos = foot_positions(calib, dets)
        labels = [None if np.isnan(f).any() else _confident_label(teams, f) for f in feats]
        step = tracker.step(pos, np.array([d.score for d in dets]), None, labels)
        timings["tracking"] += time.perf_counter() - t0
        for tp in step:
            if tp.det_index is not None and not np.isnan(feats[tp.det_index]).any():
                teams.samples[tp.track_id].append(feats[tp.det_index])
        points += step
        n += 1
        if progress and total and n % 100 == 0:
            progress("tracking", min(1.0, n / total))
    return _finish(points, teams, fps, calib, n, n_dets, timings, det.source, {"camera": "fixed"})


def _finish(
    points: list[TrackPoint],
    teams: TeamAssigner,
    fps: float,
    calib: Calibration,
    n: int,
    n_dets: int,
    timings: dict[str, float],
    source: str,
    extra: dict[str, Any],
) -> AnalysisResult:
    t0 = time.perf_counter()
    colours = {tid: np.median(np.stack(v), axis=0) for tid, v in teams.samples.items() if v}
    raw_tracks = len({p.track_id for p in points})
    points, mapping = stitch(points, fps, colours=colours)
    stitched: dict[int, list[NDArray[Any]]] = defaultdict(list)
    for old, samples in teams.samples.items():
        stitched[mapping.get(old, old)].extend(samples)
    teams.samples = stitched
    timings["stitching"] += time.perf_counter() - t0
    team_out = {}
    for tid in {p.track_id for p in points}:
        r = teams.result(tid)
        if r:
            team_out[tid] = {"label": r.label, "confidence": r.confidence, "samples": r.samples}
    return AnalysisResult(
        calib,
        fps,
        n,
        points,
        team_out,
        dict(timings),
        source,
        detections_per_frame=n_dets / max(1, n),
        extra={"raw_tracks": raw_tracks, "tracks": len(team_out), **extra},
    )


def _frames(path: Path, max_frames: int | None) -> Iterator[U8]:
    for n, frame in enumerate(iter_frames(path)):
        if max_frames is not None and n >= max_frames:
            return
        yield frame


def _analyse_moving(
    path: Path,
    kits: dict[str, tuple[int, int, int]],
    detect_every: int,
    detector: Detector | None,
    calibration: Calibration | None,
    calibration_frame: int,
    progress: Progress | None,
    max_frames: int | None,
    motion: CameraMotion | None,
    calibration_space: Literal["frame", "panorama"] = "frame",
) -> AnalysisResult:
    timings: dict[str, float] = defaultdict(float)
    _, _, fps, total = _open(path)
    if max_frames is not None:
        total = min(total, max_frames) if total else max_frames
    if progress:
        progress("calibration", 0.0)
    t0 = time.perf_counter()
    if motion is None:
        motion = estimate_motion(_frames(path, max_frames), expected_frames=total)
    timings["camera_motion"] += time.perf_counter() - t0
    t0 = time.perf_counter()
    canvas_bg = motion.background()
    timings["panorama"] += time.perf_counter() - t0
    t0 = time.perf_counter()
    if calibration is not None and calibration_space == "panorama":
        calib = Calibration(
            calibration.homography,
            calibration.confidence,
            calibration.reprojection_px,
            calibration.source,
            motion.canvas_size,
        )
    elif calibration is not None:
        to_canvas = motion.frame_to_canvas(calibration_frame)
        if to_canvas is None:
            raise CalibrationError("the calibrated frame could not be placed on the panorama")
        calib = Calibration(
            to_canvas @ calibration.homography,
            calibration.confidence,
            calibration.reprojection_px,
            calibration.source,
            motion.canvas_size,
        )
    else:
        calib = calibrate_frames(
            [canvas_bg],
            seen=motion.seen(),
            intrinsics=motion.canvas_intrinsics() if motion.moving else None,
        )
    timings["calibration"] += time.perf_counter() - t0

    moving_det = MovingBackgroundDetector(calib, canvas_bg, motion)
    det = detector or moving_det
    court = court_mask(calib) > 0
    floor = (
        cv2.cvtColor(canvas_bg, cv2.COLOR_BGR2LAB)[court]
        .reshape(-1, 3)
        .astype(np.float64)
        .mean(axis=0)
        if court.any()
        else None
    )
    teams = TeamAssigner(kits, floor_lab=floor)
    tracker = CourtTracker(fps=fps)
    points: list[TrackPoint] = []
    n = n_dets = n_lost = 0
    for frame in _frames(path, max_frames):
        t0 = time.perf_counter()
        frame_calib = moving_det.set_frame(n)
        timings["view"] += time.perf_counter() - t0
        dets: list[Detection] = []
        if frame_calib is None:
            n_lost += 1
        elif n % detect_every == 0:
            t0 = time.perf_counter()
            dets = [d for d in det.detect([frame])[0] if d.cls != "ball"]
            timings["detection"] += time.perf_counter() - t0
        n_dets += len(dets)
        t0 = time.perf_counter()
        feats = np.array(
            [c if (c := teams.torso_colour(frame, d)) is not None else [np.nan] * 3 for d in dets]
        ).reshape(-1, 3)
        timings["appearance"] += time.perf_counter() - t0
        t0 = time.perf_counter()
        pos = foot_positions(frame_calib, dets) if frame_calib is not None else np.zeros((0, 2))
        labels = [None if np.isnan(f).any() else _confident_label(teams, f) for f in feats]
        step = tracker.step(pos, np.array([d.score for d in dets]), None, labels)
        timings["tracking"] += time.perf_counter() - t0
        for tp in step:
            if tp.det_index is not None and not np.isnan(feats[tp.det_index]).any():
                teams.samples[tp.track_id].append(feats[tp.det_index])
        points += step
        n += 1
        if progress and total and n % 100 == 0:
            progress("tracking", min(1.0, n / total))
    return _finish(
        points,
        teams,
        fps,
        calib,
        n,
        n_dets,
        timings,
        det.source,
        {
            "camera": "moving",
            "motion": {k: round(v, 3) for k, v in motion.stats.items()},
            "frames_without_view": n_lost,
        },
    )
