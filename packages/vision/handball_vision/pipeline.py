"""Stages 2 to 5 as one streaming pass (BRIEF 6.3): calibration, detection, tracking, teams.

The proxy video is decoded as a stream (PyAV), frames never touch the disk. Calibration and the
background model use frames sampled across the whole video (first, seek-based pass). The second
pass detects on every `detect_every`-th frame and lets the tracker predict in between (cascade).
Results are tables (Arrow/Parquet) with pipeline and model versions; timings are recorded per stage.
"""

from __future__ import annotations

import time
from collections import defaultdict
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import av
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from numpy.typing import NDArray

from handball_vision import __version__
from handball_vision.calibration import Calibration, calibrate_frames
from handball_vision.detection import BackgroundDetector, Detection, Detector, foot_positions
from handball_vision.events import EventResult, refine_teams
from handball_vision.events import detect as detect_events
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

    def detect_events(self) -> EventResult:
        """Automatic event baseline from the tracks (throw-offs, goals, possession, sides)."""
        labels = {tid: str(v["label"]) for tid, v in self.teams.items()}
        pts = [(round(p.frame * 1000 / self.fps), p.track_id, p.x, p.y) for p in self.points]
        return detect_events(pts, labels)

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
) -> AnalysisResult:
    timings: dict[str, float] = defaultdict(float)
    t0 = time.perf_counter()
    samples = sample_frames(path, 48)
    timings["sample"] += time.perf_counter() - t0
    if progress:
        progress("calibration", 0.0)
    t0 = time.perf_counter()
    calib = calibration or calibrate_frames(samples[::2])
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
    t0 = time.perf_counter()
    colours = {tid: np.median(np.stack(v), axis=0) for tid, v in teams.samples.items() if v}
    raw_tracks = len({p.track_id for p in points})
    points, mapping = stitch(points, fps, colours=colours)
    stitched: dict[int, list[NDArray[Any]]] = defaultdict(list)
    for old, samples in teams.samples.items():
        stitched[mapping.get(old, old)].extend(samples)
    teams.samples = stitched
    timings["stitching"] += time.perf_counter() - t0
    team_out: dict[int, dict[str, Any]] = {}
    for tid in {p.track_id for p in points}:
        r = teams.result(tid)
        if r:
            team_out[tid] = {"label": r.label, "confidence": r.confidence, "samples": r.samples}
    # second signal besides the kit colour: throw-off formations (addendum 01, 4.8)
    pts = [(round(p.frame * 1000 / fps), p.track_id, p.x, p.y) for p in points]
    refined = refine_teams(
        pts,
        {t: str(v["label"]) for t, v in team_out.items()},
        {t: float(v["confidence"]) for t, v in team_out.items()},
    )
    for tid, label in refined.items():
        if label != team_out[tid]["label"]:
            team_out[tid]["label"] = label
            team_out[tid]["label_source"] = "formation"
    return AnalysisResult(
        calib,
        fps,
        n,
        points,
        team_out,
        dict(timings),
        det.source,
        detections_per_frame=n_dets / max(1, n),
        extra={"raw_tracks": raw_tracks, "tracks": len(team_out)},
    )
