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
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field, replace
from itertools import pairwise
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

# identity and video reading live in their own modules; the names stay importable from here
from handball_vision.identity import MIN_ANCHOR_READINGS as MIN_ANCHOR_READINGS
from handball_vision.identity import _split_at_switches as _split_at_switches
from handball_vision.identity import identify_by_appearance as identify_by_appearance
from handball_vision.identity import merge_by_number as merge_by_number
from handball_vision.identity import split_by_reading_colour as split_by_reading_colour
from handball_vision.motion import CameraMotion, estimate_motion
from handball_vision.numbers import Reading
from handball_vision.physical import physical
from handball_vision.teams import TeamAssigner, colour_distance, covered_share, relabel_by_clusters
from handball_vision.tracking import CourtTracker, TrackPoint, stitch
from handball_vision.video_io import U8 as U8
from handball_vision.video_io import _frames as _frames
from handball_vision.video_io import _open as _open
from handball_vision.video_io import iter_frames as iter_frames
from handball_vision.video_io import sample_frames as sample_frames

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
    # ball path of the ball net (ballpossession.path_rows: t_ms, x, y, confidence), or None
    ball_rows: Any = None

    def detect_events(self, side_hint: str | None = None) -> EventResult:
        """Automatic event baseline from the tracks (throw-offs, goals, possession, sides);
        `side_hint`: the side the home team is known to defend at the start (second half)."""
        labels = {tid: str(v["label"]) for tid, v in self.teams.items()}
        pts = [(round(p.frame * 1000 / self.fps), p.track_id, p.x, p.y) for p in self.points]
        return detect_events(pts, labels, side_hint)

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
                        np.array([p.observed for p in pts]),
                    ).to_dict(),
                }
            )
        return out


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
    points, n, n_dets, _ = _track_frames(
        _frames(path, max_frames), det, teams, fps, calib, detect_every, timings, progress, total
    )
    return _finish(points, teams, fps, calib, n, n_dets, timings, det.source, {"camera": "fixed"})


def _track_frames(
    frames: Iterable[U8],
    det: Detector,
    teams: TeamAssigner,
    fps: float,
    view: Calibration | Callable[[int], Calibration | None],
    detect_every: int,
    timings: dict[str, float],
    progress: Progress | None,
    total: int,
) -> tuple[list[TrackPoint], int, int, int]:
    """Detection, appearance and tracking over the frames, shared by the fixed and the moving
    camera. `view` is the court calibration of a fixed camera, or for a moving one the calibration
    of frame n (None where the frame could not be placed: nothing is detected there). Returns the
    track points, the frames, the detections and the frames without a view."""
    tracker = CourtTracker(fps=fps)
    points: list[TrackPoint] = []
    n = n_dets = n_lost = 0
    for frame in frames:
        if isinstance(view, Calibration):
            frame_calib: Calibration | None = view
        else:
            t0 = time.perf_counter()
            frame_calib = view(n)
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
        cover = covered_share(dets)
        timings["tracking"] += time.perf_counter() - t0
        for tp in step:
            if tp.det_index is not None and not np.isnan(feats[tp.det_index]).any():
                teams.add_sample(
                    tp.track_id,
                    feats[tp.det_index],
                    tp.frame,
                    bool(cover[tp.det_index] < CLEAR_COVER),
                )
        points += step
        n += 1
        if progress and total and n % 100 == 0:
            progress("tracking", min(1.0, n / total))
    return points, n, n_dets, n_lost


# Long links (off by default; docs/plans/produkt-analyse-integration.md, «Feldrand-Filter»): with
# the court-edge filter and the team condition, stitching over gaps up to 8 s instead of 4 s named
# 29 % of the field players' time instead of 23 % on the dev clips, wrong names unchanged, but
# about 10 % of the new links were visibly wrong and one more referee sample got a number.
LONG_LINKS = False
LONG_LINK_GAP_S = 8.0
EDGE_MARGIN_M = 0.5  # outside the court lines by more than this
EDGE_SHARE = 0.5  # share of a piece's positions out there
EDGE_MIN_S = 1.0  # and for at least this long
COURT_L, COURT_W = 40.0, 20.0


def edge_pieces(points: list[TrackPoint], fps: float) -> set[int]:
    """Raw track pieces of people standing outside the court (bench, staff, spectators at the
    line, a referee off the court): at least `EDGE_SHARE` of the positions more than
    `EDGE_MARGIN_M` outside the 40 x 20 m court, over at least `EDGE_MIN_S`. They are not linked
    to other pieces and carry no shirt number: on the dev clips Horgen H1/H2 most links over long
    gaps that joined a non-player to a player had such a piece (bench at y -1 m, behind a corner).
    Positions come from the court calibration; without it there are no tracks."""
    by: dict[int, list[TrackPoint]] = defaultdict(list)
    for p in points:
        by[p.track_id].append(p)
    out: set[int] = set()
    m = EDGE_MARGIN_M
    for t, pts in by.items():
        outside = [p.x < -m or p.x > COURT_L + m or p.y < -m or p.y > COURT_W + m for p in pts]
        span_s = (pts[-1].frame - pts[0].frame) / fps
        if span_s >= EDGE_MIN_S and sum(outside) >= EDGE_SHARE * len(pts):
            out.add(t)
    return out


NEUTRAL_DISTANCE = 15.0  # colour distance to the nearer team kit above which a shirt is no team's
END_LOOKS = 5  # colour looks at each end of a piece
# The end colours only from looks where the person stands clear of others: a box covered by
# another person box by at least `CLEAR_COVER` of its area holds two shirts in its torso crop. Only
# clear looks among the last (first) `END_WINDOW` looks count, at least `END_MIN_CLEAR` of them,
# otherwise the end has no team and blocks a long link.
CLEAR_COVER = 0.15
END_WINDOW = 15
END_MIN_CLEAR = 3


def shirt_team(colour: NDArray[Any], kits: dict[str, NDArray[Any]]) -> str:
    """ "home" or "away" by the nearer team kit, "none" when the shirt is neither team's (more than
    `NEUTRAL_DISTANCE` from both: referees, staff, goalkeepers; on the dev clips Horgen H1/H2 field
    players were 1 to 8 away, 2 of 138 above 15, referees and staff 20 of 31 above)."""
    dh, da = colour_distance(colour, kits["home"]), colour_distance(colour, kits["away"])
    if min(dh, da) > NEUTRAL_DISTANCE:
        return "none"
    return "home" if dh <= da else "away"


def piece_ends(
    samples: dict[int, list[NDArray[Any]]],
    frames: dict[int, list[int]],
    kits: dict[str, NDArray[Any]],
    clear: dict[int, list[bool]] | None = None,
) -> dict[int, tuple[str | None, str | None]] | None:
    """The team of each raw piece's shirt at its start and at its end (median of its first and
    last `END_LOOKS` colour looks): a piece can hold a swap of its own, so its whole median says
    little about the person at the moment it ends. With `clear` (parallel to `samples`), only
    looks clear of other people count, see `CLEAR_COVER`. None without both team kits (entered or
    learned); a piece without looks has (None, None)."""
    if "home" not in kits or "away" not in kits:
        return None
    out: dict[int, tuple[str | None, str | None]] = {}
    for t, looks in samples.items():
        if not looks:
            continue
        order = np.argsort(np.asarray(frames.get(t, list(range(len(looks))))), kind="stable")
        if len(order) != len(looks):
            order = np.arange(len(looks))
        ordered = [looks[k] for k in order]
        flags = clear.get(t) if clear is not None else None
        if flags is None or len(flags) != len(looks):
            first = np.median(np.stack(ordered[:END_LOOKS]), axis=0)
            last = np.median(np.stack(ordered[-END_LOOKS:]), axis=0)
            out[t] = (shirt_team(first, kits), shirt_team(last, kits))
            continue
        ok = [bool(flags[k]) for k in order]
        ends: list[str | None] = []
        for window in (
            range(min(END_WINDOW, len(looks))),
            range(max(0, len(looks) - END_WINDOW), len(looks)),
        ):
            clean = [ordered[k] for k in window if ok[k]]
            clean = clean[:END_LOOKS] if window.start == 0 else clean[-END_LOOKS:]
            ends.append(
                shirt_team(np.median(np.stack(clean), axis=0), kits)
                if len(clean) >= END_MIN_CLEAR
                else None
            )
        out[t] = (ends[0], ends[1])
    return out


# Cutting raw pieces where the shirt changes (docs/plans/produkt-analyse-integration.md, «Farbsprung
# im Tracker»): the tracker sometimes hands a track from a player to a referee, a coach or a player
# of the other team standing next to him. Each clear look (no other person box over
# `CLEAR_COVER` of it) gets a class: home, away or none (no team's kit, `shirt_team`); a class
# holds when it is the majority within `CUT_WINDOW_S` around the look, and only stretches of at
# least `CUT_MIN_RUN_S` count (hysteresis: shorter ones go to the longer neighbour). On the dev
# clips Horgen H1/H2 (ml/eval/identity_dev.py) right numbers 10 -> 12 of 27, wrong 1 -> 0, named
# share 24.6 -> 23.2 %; referees and staff with a player label 22 -> 14 of 72.
COLOUR_CUT = True
CUT_WINDOW_S = 1.0
CUT_MIN_RUN_S = 1.5
KEEPER_ZONE_M = 6.5


def shirt_runs(frames: list[int], classes: list[str], fps: float) -> list[tuple[int, int, str]]:
    """Stretches of one shirt class (first frame, last frame, class) in time order, from the
    classes of single clear looks: each look takes the majority within `CUT_WINDOW_S`, stretches
    shorter than `CUT_MIN_RUN_S` go to the longer neighbour."""
    if not frames:
        return []
    order = np.argsort(np.asarray(frames), kind="stable")
    fr = np.asarray(frames, np.int64)[order]
    cl = [classes[k] for k in order]
    names = sorted(set(cl))
    onehot = np.array([[c == n for n in names] for c in cl], np.int64)
    csum = np.vstack([np.zeros(len(names), np.int64), np.cumsum(onehot, axis=0)])
    half = CUT_WINDOW_S * fps / 2
    lo = np.searchsorted(fr, fr - half, side="left")
    hi = np.searchsorted(fr, fr + half, side="right")
    counts = csum[hi] - csum[lo]
    smooth = []
    for k in range(len(fr)):
        best = counts[k].max()
        top = [names[j] for j in range(len(names)) if counts[k][j] == best]
        smooth.append(cl[k] if cl[k] in top else top[0])
    runs: list[list[Any]] = []
    for f, c in zip(fr.tolist(), smooth, strict=True):
        if runs and runs[-1][2] == c:
            runs[-1][1] = f
        else:
            runs.append([f, f, c])
    min_len = CUT_MIN_RUN_S * fps
    while len(runs) > 1:
        k = min(range(len(runs)), key=lambda i: runs[i][1] - runs[i][0])
        if runs[k][1] - runs[k][0] >= min_len:
            break
        nb = [i for i in (k - 1, k + 1) if 0 <= i < len(runs)]
        to = max(nb, key=lambda i: runs[i][1] - runs[i][0])
        runs[to][0], runs[to][1] = min(runs[to][0], runs[k][0]), max(runs[to][1], runs[k][1])
        del runs[k]
        merged: list[list[Any]] = []
        for r in runs:
            if merged and merged[-1][2] == r[2]:
                merged[-1][1] = r[1]
            else:
                merged.append(r)
        runs = merged
    return [(int(a), int(b), str(c)) for a, b, c in runs]


def cut_at_shirt_changes(
    points: list[TrackPoint],
    teams: TeamAssigner,
    fps: float,
    per_track: Sequence[dict[int, list[Any]]],
) -> tuple[list[TrackPoint], int]:
    """Cut raw pieces at stable shirt changes (`shirt_runs`); each stretch becomes a piece of its
    own. Colour samples in `teams` and the per-track lists in `per_track` (number readings with
    `.frame`, (frame, item) tuples) move with them, in place. Needs both team kits. Returns the
    points and the number of cuts."""
    kits = teams.kits
    if "home" not in kits or "away" not in kits:
        return points, 0
    next_id = max([p.track_id for p in points], default=0) + 1
    # goalkeepers wear a kit of their own ("none" here) and stand at their goal: a piece mostly
    # within `KEEPER_ZONE_M` of a goal is not cut (the position rule needs keeper tracks of 10 s,
    # `events.assign_goalkeepers`; cutting them cost the sides on the dev clip Horgen H2)
    near: dict[int, list[bool]] = defaultdict(list)
    for p in points:
        if p.observed:
            d = min(np.hypot(p.x, p.y - COURT_W / 2), np.hypot(COURT_L - p.x, p.y - COURT_W / 2))
            near[p.track_id].append(bool(d < KEEPER_ZONE_M))
    cuts: dict[int, list[tuple[int, int]]] = {}  # track -> [(from frame, new id)]
    for t, looks in list(teams.samples.items()):
        if near.get(t) and sum(near[t]) >= 0.5 * len(near[t]):
            continue
        frames = teams.frames.get(t, [])
        clear = teams.clear.get(t, [])
        if len(frames) != len(looks) or len(clear) != len(looks):
            continue
        sel = [k for k in range(len(looks)) if clear[k]]
        runs = shirt_runs([frames[k] for k in sel], [shirt_team(looks[k], kits) for k in sel], fps)
        if len(runs) < 2:
            continue
        bounds = []
        for (_, a, _), (b, _, _) in pairwise(runs):
            bounds.append(((a + b) // 2 + 1, next_id))
            next_id += 1
        cuts[t] = bounds
    if not cuts:
        return points, 0

    def owner(t: int, frame: int) -> int:
        tid = t
        for f, nid in cuts.get(t, []):
            if frame >= f:
                tid = nid
        return tid

    for t in cuts:
        items = list(zip(teams.frames[t], teams.samples[t], teams.clear[t], strict=True))
        for nid in [t, *(n for _, n in cuts[t])]:
            teams.samples[nid], teams.frames[nid], teams.clear[nid] = [], [], []
        for f, c, ok in items:
            nid = owner(t, f)
            teams.samples[nid].append(c)
            teams.frames[nid].append(f)
            teams.clear[nid].append(ok)
    for group in per_track:
        for t in [t for t in group if t in cuts]:
            for v in group.pop(t):
                f = int(v.frame) if hasattr(v, "frame") else int(v[0])
                group.setdefault(owner(t, f), []).append(v)
    out = [replace(p, track_id=owner(p.track_id, p.frame)) for p in points]
    return out, sum(len(b) for b in cuts.values())


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
    if COLOUR_CUT:
        number_reads = dict(number_reads or {})
        vectors = dict(vectors or {})
        role_samples = dict(role_samples or {})
        points, n_cuts = cut_at_shirt_changes(
            points, teams, fps, [number_reads, vectors, role_samples]
        )
        extra = {**extra, "shirt_cuts": n_cuts}
    colours = {tid: np.median(np.stack(v), axis=0) for tid, v in teams.samples.items() if v}
    raw_tracks = len({p.track_id for p in points})
    if LONG_LINKS:
        # people outside the court are not linked and nobody's shirt number; links over long gaps
        # only between pieces whose shirt at the meeting ends is the same team
        edge = edge_pieces(points, fps)
        piece_teams = piece_ends(teams.samples, teams.frames, teams.kits, teams.clear)
        points, mapping = stitch(
            points,
            fps,
            max_gap_s=LONG_LINK_GAP_S,
            colours=colours,
            excluded=edge,
            piece_teams=piece_teams,
        )
        number_reads = {t: rs for t, rs in (number_reads or {}).items() if t not in edge}
    else:
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
    # a goalkeeper kit that fits a whole team (the keeper colour entered equals a team's field
    # shirts): those players are field players; the position rule below finds the real keepers
    for tid in crowded_keepers(points, {t: str(v["label"]) for t, v in team_out.items()}):
        team_out[tid]["label"] = str(team_out[tid]["label"]).removesuffix("_gk")
        team_out[tid]["label_source"] = "keeper_crowd"
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
    if reads and framed:
        # the team of a number is the colour of the shirt it was read on
        t0 = time.perf_counter()
        points, by_colour = split_by_reading_colour(
            points, team_out, teams, reads, [looks, role_framed], fps
        )
        extra = {**extra, "reading_colour": by_colour}
        timings["numbers_vote"] += time.perf_counter() - t0
    if reads:
        t0 = time.perf_counter()
        before = len({p.track_id for p in points})
        points, merged = merge_by_number(
            points, team_out, reads, fps, looks=looks, rosters=rosters, roles=role_framed
        )
        extra = {
            **extra,
            "merged_by_number": merged,
            "split_by_number": len({p.track_id for p in points}) + merged - before,
        }
        if looks:
            extra["identified_by_appearance"] = identify_by_appearance(
                points, team_out, looks, fps, reads, roles=role_framed
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


MAX_KEEPERS_AT_ONCE = 2  # one keeper per team on court, plus a moment of overlap at a change
CROWD_SHARE = 0.5  # share of the keeper label's frames with more tracks at once than that


def crowded_keepers(points: list[TrackPoint], labels: dict[int, str]) -> list[int]:
    """Tracks with a goalkeeper label ("home_gk", "away_gk") from a label that is worn by more
    than `MAX_KEEPERS_AT_ONCE` tracks at once in at least `CROWD_SHARE` of the frames it is seen
    in: a team has one keeper on court, so such a label is really a field kit (staging
    2026-11-17: the keeper colour entered was the opponents' yellow, all their players became
    "home_gk" and the ball possession statistics showed one team only)."""
    at: dict[str, dict[int, set[int]]] = defaultdict(lambda: defaultdict(set))
    for p in points:
        label = labels.get(p.track_id, "")
        if label.endswith("_gk") and p.observed:
            at[label][p.frame].add(p.track_id)
    out: list[int] = []
    for frames in at.values():
        crowded = sum(len(v) > MAX_KEEPERS_AT_ONCE for v in frames.values())
        if crowded >= CROWD_SHARE * len(frames):
            out.extend(sorted({t for v in frames.values() for t in v}))
    return out


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
    # a learned detector needs only the court homography, not the rendered background
    view = moving_det.set_frame if detector is None else moving_det.frame_calibration
    points, n, n_dets, n_lost = _track_frames(
        _frames(path, max_frames), det, teams, fps, view, detect_every, timings, progress, total
    )
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
