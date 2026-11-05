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
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field, replace
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
    filter_on_court,
    foot_positions,
)
from handball_vision.events import EventResult, assign_goalkeepers, refine_teams
from handball_vision.events import detect as detect_events
from handball_vision.motion import CameraMotion, estimate_motion
from handball_vision.numbers import MIN_CONFIDENCE, Reading, split_points, vote
from handball_vision.physical import physical
from handball_vision.reid import Fragment, assign
from handball_vision.teams import TeamAssigner, relabel_by_clusters
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
                    "number": team.get("number"),
                    "number_confidence": team.get("number_confidence"),
                    "number_source": team.get(
                        "number_source", "read" if team.get("number") is not None else None
                    ),
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


def _people(det: Detector, frame: U8, calib: Calibration) -> list[Detection]:
    """People on the court in one frame. A learned detector finds everyone in the hall (bench,
    spectators, people behind the railing); only those standing on the court are kept."""
    found = det.detect([frame])[0]
    if det.source == "model":
        return filter_on_court(calib, found)
    return [d for d in found if d.cls != "ball"]


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
            dets = _people(det, frame, calib)
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
                teams.add_sample(tp.track_id, feats[tp.det_index], tp.frame)
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
    number_reads: dict[int, list[Reading]] | None = None,
    vectors: dict[int, list[tuple[int, NDArray[np.float64]]]] | None = None,
    role_samples: dict[int, list[tuple[int, NDArray[np.float64]]]] | None = None,
    rosters: dict[str, set[int]] | None = None,
) -> AnalysisResult:
    t0 = time.perf_counter()
    colours = {tid: np.median(np.stack(v), axis=0) for tid, v in teams.samples.items() if v}
    raw_tracks = len({p.track_id for p in points})
    points, mapping = stitch(points, fps, colours=colours)
    framed = all(len(teams.frames.get(t, [])) == len(v) for t, v in teams.samples.items())
    stitched: dict[int, list[NDArray[Any]]] = defaultdict(list)
    stitched_frames: dict[int, list[int]] = defaultdict(list)
    for old, samples in teams.samples.items():
        stitched[mapping.get(old, old)].extend(samples)
        stitched_frames[mapping.get(old, old)].extend(teams.frames.get(old, []))
    teams.samples, teams.frames = stitched, stitched_frames
    reads: dict[int, list[Reading]] = defaultdict(list)
    for old, rs in (number_reads or {}).items():
        reads[mapping.get(old, old)].extend(rs)
    looks: dict[int, list[tuple[int, NDArray[np.float64]]]] = defaultdict(list)
    for old, vs in (vectors or {}).items():
        looks[mapping.get(old, old)].extend(vs)
    role_framed: dict[int, list[tuple[int, NDArray[np.float64]]]] = defaultdict(list)
    for old, role_list in (role_samples or {}).items():
        role_framed[mapping.get(old, old)].extend(role_list)
    timings["stitching"] += time.perf_counter() - t0
    # people outside play (bench, staff, spectators at the court edge) leave the tracks before
    # anything is learned from them (handball_vision.bench, ADR 028 addendum)
    t0 = time.perf_counter()
    points, bench = _drop_bench(points, fps, calib, teams, reads, looks, role_framed, framed)
    extra = {**extra, "bench": bench}
    timings["bench"] += time.perf_counter() - t0
    role_looks = {t: [v for _, v in vs] for t, vs in role_framed.items() if vs}
    team_out: dict[int, dict[str, Any]] = {}
    for tid in {p.track_id for p in points}:
        r = teams.result(tid)
        if r:
            lab = np.median(np.stack(teams.samples[tid]), axis=0)
            bgr = cv2.cvtColor(
                np.clip(lab, 0, 255).astype(np.uint8).reshape(1, 1, 3), cv2.COLOR_LAB2BGR
            )[0, 0]
            team_out[tid] = {
                "label": r.label,
                "confidence": r.confidence,
                "samples": r.samples,
                "colour": f"#{int(bgr[2]):02x}{int(bgr[1]):02x}{int(bgr[0]):02x}",
                "lab": [round(float(v), 1) for v in lab],
            }
    # team labels relative to this match's colours (lighting shifts absolute colours)
    clustered = relabel_by_clusters(
        {
            t: (np.asarray(v["lab"], dtype=np.float64), int(v["samples"]))
            for t, v in team_out.items()
        },
        teams.kits,
    )
    for tid, label in clustered.items():
        if team_out[tid]["label"] != label:
            team_out[tid]["label"] = label
            team_out[tid]["label_source"] = "cluster"
    # goalkeepers by position and by which team defends their goal (kit colours often missing)
    pts = [(round(p.frame * 1000 / fps), p.track_id, p.x, p.y) for p in points]
    observed = [(round(p.frame * 1000 / fps), p.track_id, p.x, p.y) for p in points if p.observed]
    for tid, label in assign_goalkeepers(
        observed, {t: str(v["label"]) for t, v in team_out.items()}
    ).items():
        if tid in team_out and team_out[tid]["label"] != label:
            team_out[tid]["label"] = label
            team_out[tid]["label_source"] = "position"
    # second signal besides the kit colour: throw-off formations (addendum 01, 4.8)
    refined = refine_teams(
        pts,
        {t: str(v["label"]) for t, v in team_out.items()},
        {t: float(v["confidence"]) for t, v in team_out.items()},
    )
    for tid, label in refined.items():
        if label != team_out[tid]["label"]:
            team_out[tid]["label"] = label
            team_out[tid]["label_source"] = "formation"
    if role_looks:
        changed = _apply_role_votes(points, team_out, role_looks, observed)
        extra = {**extra, "roles_changed": changed}
    if reads:
        t0 = time.perf_counter()
        before = len({p.track_id for p in points})
        points, merged = merge_by_number(points, team_out, reads, fps, looks=looks, rosters=rosters)
        extra = {
            **extra,
            "merged_by_number": merged,
            "split_by_number": len({p.track_id for p in points}) + merged - before,
        }
        if looks:
            extra["identified_by_appearance"] = identify_by_appearance(
                points, team_out, looks, fps, reads
            )
        timings["numbers_vote"] += time.perf_counter() - t0
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


def _drop_bench(
    points: list[TrackPoint],
    fps: float,
    calib: Calibration,
    teams: TeamAssigner,
    reads: dict[int, list[Reading]],
    looks: dict[int, list[tuple[int, NDArray[np.float64]]]],
    role_looks: dict[int, list[tuple[int, NDArray[np.float64]]]],
    framed: bool = True,
) -> tuple[list[TrackPoint], dict[str, Any]]:
    """Cut the bench stretches out of the tracks and move every look (colour, number, appearance,
    role) to the track it now belongs to; looks on a bench stretch are dropped. Without frames
    for the colour samples (`framed` False) a track keeps its samples and a new piece copies its
    parent's."""
    from handball_vision.bench import split_bench

    split = split_bench(points, fps, calib)
    if not split.stretches:
        return points, {"stretches": 0, "tracks_removed": 0, "pieces": 0, "items": []}

    def regroup(items: dict[int, list[Any]], frame_of: Callable[[Any], int]) -> None:
        out: dict[int, list[Any]] = defaultdict(list)
        for t, vs in items.items():
            for v in vs:
                owner = split.owner(t, frame_of(v))
                if owner is not None:
                    out[owner].append(v)
        items.clear()
        items.update(out)

    if framed:
        pairs = {t: list(zip(teams.frames[t], vs, strict=True)) for t, vs in teams.samples.items()}
        regroup(pairs, lambda v: int(v[0]))
        teams.samples = defaultdict(list, {t: [c for _, c in vs] for t, vs in pairs.items()})
        teams.frames = defaultdict(list, {t: [f for f, _ in vs] for t, vs in pairs.items()})
    else:
        for t in split.removed:
            teams.samples.pop(t, None)
        for new, (old, _, _) in split.pieces.items():
            teams.samples[new] = list(teams.samples.get(old, []))
    regroup(reads, lambda r: int(r.frame))
    regroup(looks, lambda v: int(v[0]))
    regroup(role_looks, lambda v: int(v[0]))
    return split.points, {
        "stretches": len(split.stretches),
        "tracks_removed": len(split.removed),
        "pieces": len(split.pieces),
        "items": [s.to_dict(fps) for s in split.stretches],
    }


def _apply_role_votes(
    points: list[TrackPoint],
    team_out: dict[int, dict[str, Any]],
    role_looks: dict[int, list[NDArray[np.float64]]],
    observed: list[tuple[int, int, float, float]],
) -> dict[str, int]:
    """Referees and short goalkeeper tracks from the role classifier (handball_vision.roles)."""
    from handball_vision.roles import apply_roles, goal_presence, track_roles

    roles = track_roles(role_looks)
    for tid, probs in roles.items():
        if tid in team_out:
            team_out[tid]["role_p"] = [round(float(v), 3) for v in probs]
    spans: dict[int, tuple[int, int]] = {}
    for p in points:
        a, b = spans.get(p.track_id, (p.frame, p.frame))
        spans[p.track_id] = (min(a, p.frame), max(b, p.frame))
    near, side = goal_presence(observed)
    # the team defending a goal: from the goalkeepers the position rule found (nearest in time)
    keepers = [
        (t, str(v["label"]).removesuffix("_gk"), side.get(t))
        for t, v in team_out.items()
        if str(v.get("label", "")).endswith("_gk") and side.get(t)
    ]
    goal_team: dict[int, str] = {}
    for t in roles:
        if t not in side or t not in spans:
            continue
        same = [
            (abs(spans[k][0] - spans[t][0]), team)
            for k, team, s in keepers
            if s == side[t] and k in spans
        ]
        if same:
            goal_team[t] = min(same)[1]
    changes = apply_roles(team_out, roles, spans, near, goal_team)
    for tid, label in changes.items():
        team_out[tid]["label"] = label
        team_out[tid]["label_source"] = "role"
    return {
        "referee": sum(1 for v in changes.values() if v == "referee"),
        "goalkeeper": sum(1 for v in changes.values() if v.endswith("_gk")),
        "team": sum(1 for v in changes.values() if v in ("home", "away")),
    }


def _split_at_switches(
    points: list[TrackPoint],
    team_out: dict[int, dict[str, Any]],
    reads: dict[int, list[Reading]],
    looks: dict[int, list[tuple[int, NDArray[np.float64]]]],
) -> tuple[list[TrackPoint], dict[int, list[Reading]], dict[int, list[tuple[int, Any]]]]:
    """Cut tracks where the shirt numbers say the tracker swapped players; each part becomes its
    own track (same team entry) with its own readings."""
    next_id = max([p.track_id for p in points], default=0) + 1
    cuts: dict[int, list[tuple[int, int]]] = {}  # track -> [(from_frame, new id)]
    out_reads: dict[int, list[Reading]] = defaultdict(list)
    for t, rs in reads.items():
        frames = split_points(rs) if t in team_out else []
        bounds = [(f, next_id + k) for k, f in enumerate(frames)]
        next_id += len(frames)
        if bounds:
            cuts[t] = bounds
            for _, nid in bounds:
                team_out[nid] = {
                    k: v
                    for k, v in team_out[t].items()
                    if k not in ("number", "number_confidence", "number_readings")
                }
        for r in rs:
            tid = t
            for f, nid in bounds:
                if r.frame >= f:
                    tid = nid
            out_reads[tid].append(r)
    out_looks: dict[int, list[tuple[int, Any]]] = defaultdict(list)
    for t, vs in looks.items():
        for f0, v in vs:
            tid = t
            for f, nid in cuts.get(t, []):
                if f0 >= f:
                    tid = nid
            out_looks[tid].append((f0, v))
    if not cuts:
        return points, out_reads, out_looks

    def owner(p: TrackPoint) -> int:
        tid = p.track_id
        for f, nid in cuts.get(p.track_id, []):
            if p.frame >= f:
                tid = nid
        return tid

    return [replace(p, track_id=owner(p)) for p in points], out_reads, out_looks


MIN_ANCHOR_READINGS = 4


def identify_by_appearance(
    points: list[TrackPoint],
    team_out: dict[int, dict[str, Any]],
    looks: Mapping[int, Sequence[NDArray[np.float64] | tuple[int, NDArray[np.float64]]]],
    fps: float,
    reads: Mapping[int, list[Reading]] | None = None,
) -> int:
    """Numbers for tracks nobody read a number on, by appearance (reid.py): the numbered tracks of
    this match teach what each player looks like. `looks` is keyed by the final track ids, as
    vectors or (frame, vector); with frames and the tracks' `reads` a numbered track teaches only
    with the vectors next to readings of its number (reid.anchor_vectors), and a track whose own
    readings say otherwise is not given the number (reid.contradicts)."""
    span: dict[int, list[TrackPoint]] = defaultdict(list)
    for p in points:
        span[p.track_id].append(p)
    frags = []
    for tid, ps in span.items():
        info = team_out.get(tid)
        if info is None or str(info["label"]) == "referee" or len(looks.get(tid, [])) < 3:
            continue
        ps.sort(key=lambda p: p.frame)
        # only well-read numbers teach; a number read a few times may be a misreading (24 for
        # 14) and is checked against the anchors like a track without number
        anchor = int(info.get("number_readings", 0)) >= MIN_ANCHOR_READINGS
        items = looks[tid]
        framed = all(isinstance(v, tuple) for v in items)
        vectors = np.stack([v[1] if isinstance(v, tuple) else v for v in items])
        frames = np.array([v[0] for v in items if isinstance(v, tuple)], np.int64)
        readings = tuple(
            (r.frame, r.number) for r in (reads or {}).get(tid, []) if r.confidence >= MIN_CONFIDENCE
        )
        frags.append(
            Fragment(
                tid,
                str(info["label"]),
                ps[0].frame,
                ps[-1].frame,
                (ps[0].x, ps[0].y),
                (ps[-1].x, ps[-1].y),
                vectors,
                info.get("number") if anchor else None,
                frames if framed and reads is not None else None,
                readings,
            )
        )
    found = assign(frags, fps)
    for tid, number in found.items():
        read = team_out[tid].get("number")
        team_out[tid].update(
            number=number, number_source="read" if read == number else "appearance"
        )
    return len(found)


def merge_by_number(
    points: list[TrackPoint],
    team_out: dict[int, dict[str, Any]],
    reads: dict[int, list[Reading]],
    fps: float,
    max_overlap_s: float = 1.0,
    looks: dict[int, list[tuple[int, Any]]] | None = None,
    rosters: dict[str, set[int]] | None = None,
) -> tuple[list[TrackPoint], int]:
    """Number per track by vote, then one track per player: fragments of the same team with the
    same number that do not overlap in time are joined (the number is the identity the tracker
    loses on occlusions and camera pans). When two fragments with the same number overlap, the one
    with the weaker vote loses its number. Returns the points and the number of joined fragments.

    `rosters` ("home"/"away" -> shirt numbers) restricts each team's votes to its roster (see
    `vote`); a team without roster is voted freely. `reads` and `looks` are updated in place to
    the new track ids (cut at switches, joined by number)."""
    points, split_reads, moved = _split_at_switches(points, team_out, reads, looks or {})
    reads.clear()
    reads.update(split_reads)
    if looks is not None:
        looks.clear()
        looks.update(moved)
    span: dict[int, tuple[int, int]] = {}
    for p in points:
        a, b = span.get(p.track_id, (p.frame, p.frame))
        span[p.track_id] = (min(a, p.frame), max(b, p.frame))

    def side(t: int) -> str:
        # a number belongs to one person of a team: a "goalkeeper" fragment with a field player's
        # number is the position heuristic being wrong (they still may not overlap in time)
        return str(team_out[t]["label"]).removesuffix("_gk")

    votes = {
        t: v
        for t, rs in reads.items()
        if t in team_out and (v := vote(rs, (rosters or {}).get(side(t)))) is not None
    }
    for t, v in votes.items():
        team_out[t].update(
            number=v.number, number_confidence=v.confidence, number_readings=v.readings
        )

    groups: dict[tuple[str, int], list[int]] = defaultdict(list)
    for t, v in votes.items():
        if side(t) != "referee":
            groups[(side(t), v.number)].append(t)
    max_overlap = max_overlap_s * fps  # frames
    rename: dict[int, int] = {}
    for tids in groups.values():
        tids.sort(key=lambda t: -votes[t].confidence * votes[t].readings)
        chains: list[list[int]] = []
        for t in tids:
            a, b = span[t]
            for chain in chains:
                clash = any(min(b, span[c][1]) - max(a, span[c][0]) > max_overlap for c in chain)
                if not clash:
                    chain.append(t)
                    break
            else:
                if chains:  # overlaps the stronger fragment: its number is the misreading
                    for k in ("number", "number_confidence", "number_readings"):
                        team_out[t].pop(k, None)
                    continue
                chains.append([t])
        for chain in chains:
            head = min(chain, key=lambda c: span[c][0])
            for c in chain:
                if c != head:
                    rename[c] = head
    if not rename:
        return points, 0
    for old, new in rename.items():
        if looks is not None and old in looks:
            looks.setdefault(new, []).extend(looks.pop(old))
        if old in reads:
            reads.setdefault(new, []).extend(reads.pop(old))
        keep, gone = team_out[new], team_out.pop(old)
        if span[old][1] - span[old][0] > span[new][1] - span[new][0]:
            keep["label"] = gone["label"]  # the longer fragment knows the role better
        if int(gone.get("number_readings", 0)) > int(keep.get("number_readings", 0)):
            for k in ("number_confidence", "number_readings"):
                keep[k] = gone[k]
        keep["samples"] = int(keep.get("samples", 0)) + int(gone.get("samples", 0))
        keep["merged_from"] = [*keep.get("merged_from", []), old]
    out = [
        TrackPoint(
            rename.get(p.track_id, p.track_id),
            p.frame,
            p.x,
            p.y,
            p.vx,
            p.vy,
            p.observed,
            p.det_index,
        )
        for p in points
    ]
    # the same frame twice in one track (rounding at the joins): keep the observed point
    seen: dict[tuple[int, int], TrackPoint] = {}
    for p in out:
        key = (p.track_id, p.frame)
        if key not in seen or (p.observed and not seen[key].observed):
            seen[key] = p
    return sorted(seen.values(), key=lambda p: (p.frame, p.track_id)), len(rename)


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
        # a learned detector needs only the court homography, not the rendered background
        frame_calib = (
            moving_det.set_frame(n) if detector is None else moving_det.frame_calibration(n)
        )
        timings["view"] += time.perf_counter() - t0
        dets: list[Detection] = []
        if frame_calib is None:
            n_lost += 1
        elif n % detect_every == 0:
            t0 = time.perf_counter()
            dets = _people(det, frame, frame_calib)
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
                teams.add_sample(tp.track_id, feats[tp.det_index], tp.frame)
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
