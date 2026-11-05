"""Analysis with a learned person detector in one decoding pass (ADR 025).

1. **Observe** (`observe`): every frame goes through the camera-motion estimator; every
   `detect_every`-th frame through the detector (people and ball boxes in frame pixels, plus a
   small Lab sample of each torso); every `segment_every`-th frame gives its floor-marking
   segments. Nothing here needs the court yet, so the video is decoded once.
2. **Calibrate** (`auto_calibrate`): the hall's floor orientation from the markings, the camera
   height from the people, a metric top view, the court template (lines, players on the court,
   goalkeepers in the goal mouths) and finally the goal frames (striped posts and crossbar).
   Multi-sport halls: if the court from all lines is not trustworthy, the line colour that forms
   the handball court gets a search of its own; flat views (low cameras) stop early.
3. **Track** (`track`): the stored detections are mapped to the court frame by frame (court
   homography of the frame = panorama calibration x camera rotation), filtered to the court,
   tracked and assigned to teams; the result is the same `AnalysisResult` as before.
"""

from __future__ import annotations

import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from numpy.typing import NDArray

from handball_vision import geometry, topview
from handball_vision.calibration import Calibration, CalibrationError, line_masks
from handball_vision.detection import Detection, Detector, filter_on_court, foot_positions
from handball_vision.motion import CameraMotion, MotionEstimator

F64 = NDArray[np.float64]
U8 = NDArray[Any]
Progress = Callable[[str, float], None]


@dataclass
class FrameObservation:
    index: int
    people: list[Detection]
    torsos: list[
        NDArray[np.float64] | None
    ]  # Lab pixels of the torso (n x 3), not yet floor-filtered
    balls: list[Detection]
    numbers: dict[int, tuple[int, float]] = field(default_factory=dict)  # person -> (number, conf)
    embeds: dict[int, NDArray[np.float64]] = field(default_factory=dict)  # person -> appearance
    roles: dict[int, NDArray[np.float64]] = field(default_factory=dict)  # person -> role probs


@dataclass
class Observations:
    motion: CameraMotion
    frames: list[FrameObservation]
    segments: dict[int, F64]  # frame index -> floor marking segments (x1, y1, x2, y2), frame px
    fps: float
    total: int
    timings_s: dict[str, float] = field(default_factory=dict)
    detector_source: str = "model"


def _torso_sample(frame: U8, d: Detection) -> NDArray[np.float64] | None:
    h, w = d.y2 - d.y1, d.x2 - d.x1
    y1, y2 = int(d.y1 + h * 0.18), int(d.y1 + h * 0.5)
    x1, x2 = int(d.x1 + w * 0.2), int(d.x2 - w * 0.2)
    if y2 - y1 < 2 or x2 - x1 < 2:
        return None
    crop = frame[max(0, y1) : y2, max(0, x1) : x2]
    if crop.size == 0:
        return None
    small = cv2.resize(crop, (6, 8), interpolation=cv2.INTER_AREA)
    return np.asarray(cv2.cvtColor(small, cv2.COLOR_BGR2LAB).reshape(-1, 3), dtype=np.uint8)


def observe(
    path: Path,
    detector: Detector,
    detect_every: int = 3,
    segment_every: int = 90,
    max_frames: int | None = None,
    progress: Progress | None = None,
    on_frame: Callable[[int, U8], None] | None = None,
    numbers: Any = None,  # handball_vision.numbers.NumberReader
    number_every: int = 15,
    embedder: Any = None,  # handball_vision.reid.Embedder
    embed_every: int = 30,
    roles: Any = None,  # handball_vision.roles.RoleClassifier
    role_every: int = 30,
) -> Observations:
    """`on_frame(index, frame)` sees every decoded frame (e.g. the score overlay reader), so the
    video is decoded only once."""
    from handball_vision.pipeline import _open, iter_frames

    _, _, fps, total = _open(path)
    if max_frames is not None:
        total = min(total, max_frames) if total else max_frames
    est = MotionEstimator(keep_every=max(1, total // 30) if total else 25)
    frames: list[FrameObservation] = []
    segments: dict[int, F64] = {}
    timings: dict[str, float] = defaultdict(float)
    for n, frame in enumerate(iter_frames(path)):
        if max_frames is not None and n >= max_frames:
            break
        t0 = time.perf_counter()
        est.add(frame)
        timings["camera_motion"] += time.perf_counter() - t0
        if on_frame is not None:
            t0 = time.perf_counter()
            on_frame(n, frame)
            timings["overlay"] += time.perf_counter() - t0
        if n % detect_every == 0:
            t0 = time.perf_counter()
            found = detector.detect([frame])[0]
            people = [d for d in found if d.cls != "ball"]
            balls = [d for d in found if d.cls == "ball"]
            timings["detection"] += time.perf_counter() - t0
            t0 = time.perf_counter()
            fo = FrameObservation(n, people, [_torso_sample(frame, d) for d in people], balls)
            frames.append(fo)
            timings["appearance"] += time.perf_counter() - t0
            if numbers is not None and n % number_every == 0:
                t0 = time.perf_counter()
                fo.numbers = read_numbers(numbers, frame, people)
                timings["numbers"] += time.perf_counter() - t0
            if embedder is not None and n % embed_every == 0:
                t0 = time.perf_counter()
                vecs = embedder.embed(frame, [(d.x1, d.y1, d.x2, d.y2) for d in people])
                fo.embeds = {k: v for k, v in enumerate(vecs) if v is not None}
                timings["appearance_net"] += time.perf_counter() - t0
            if roles is not None and n % role_every == 0:
                t0 = time.perf_counter()
                probs = roles.classify(frame, [(d.x1, d.y1, d.x2, d.y2) for d in people])
                fo.roles = {k: v for k, v in enumerate(probs) if v is not None}
                timings["roles"] += time.perf_counter() - t0
            if n % segment_every == 0:
                t0 = time.perf_counter()
                segments[n] = topview.frame_segments(
                    frame, [(d.x1, d.y1, d.x2, d.y2) for d in people]
                )
                timings["markings"] += time.perf_counter() - t0
        if progress and total and n % 100 == 0:
            progress("observe", min(1.0, n / total))
    t0 = time.perf_counter()
    motion = est.finish()
    timings["camera_motion"] += time.perf_counter() - t0
    if len(motion.samples) > 30:
        step = len(motion.samples) / 30
        motion.samples = [motion.samples[int(k * step)] for k in range(30)]
    return Observations(motion, frames, segments, fps, n, dict(timings), detector.source)


def read_numbers(reader: Any, frame: U8, people: list[Detection]) -> dict[int, tuple[int, float]]:
    """Shirt numbers of the players large, sharp and fully inside the frame."""
    from handball_vision.numbers import MIN_BOX_HEIGHT, sharp_enough

    h, w = frame.shape[:2]
    out: dict[int, tuple[int, float]] = {}
    for k, d in enumerate(people):
        box = (d.x1, d.y1, d.x2, d.y2)
        if d.y2 - d.y1 < MIN_BOX_HEIGHT or d.x1 < 2 or d.y1 < 2 or d.x2 > w - 2 or d.y2 > h - 2:
            continue
        if not sharp_enough(frame, box):
            continue
        r = reader.read_player(frame, box)
        if r is not None:
            out[k] = (r.number, round(r.confidence, 3))
    return out


def save_observations(obs: Observations, path: Path) -> None:
    """Detections, torso samples and marking segments (the camera motion is saved separately):
    a re-run with clicked court points skips decoding and detection."""
    idx, boxes, scores, kinds, torsos, has_torso = [], [], [], [], [], []
    for fo in obs.frames:
        for d, t in zip(fo.people, fo.torsos, strict=True):
            idx.append(fo.index)
            boxes.append((d.x1, d.y1, d.x2, d.y2))
            scores.append(d.score)
            kinds.append(0)
            has_torso.append(t is not None)
            torsos.append(t if t is not None else np.zeros((48, 3), np.uint8))
        for d in fo.balls:
            idx.append(fo.index)
            boxes.append((d.x1, d.y1, d.x2, d.y2))
            scores.append(d.score)
            kinds.append(1)
            has_torso.append(False)
            torsos.append(np.zeros((48, 3), np.uint8))
    nums = [(fo.index, k, n, c) for fo in obs.frames for k, (n, c) in fo.numbers.items()]
    emb_idx = [(fo.index, k) for fo in obs.frames for k in fo.embeds]
    embs = [v for fo in obs.frames for v in fo.embeds.values()]
    role_idx = [(fo.index, k) for fo in obs.frames for k in fo.roles]
    role_p = [v for fo in obs.frames for v in fo.roles.values()]
    seg_idx = [i for i, sg in obs.segments.items() for _ in range(len(sg))]
    segs = (
        np.vstack([sg for sg in obs.segments.values() if len(sg)])
        if obs.segments
        else np.zeros((0, 4))
    )
    np.savez_compressed(
        path,
        frames=np.array([fo.index for fo in obs.frames], np.int32),
        idx=np.array(idx, np.int32),
        boxes=np.array(boxes, np.float32).reshape(-1, 4),
        scores=np.array(scores, np.float32),
        kinds=np.array(kinds, np.uint8),
        torsos=np.array(torsos, np.uint8).reshape(-1, 48, 3),
        has_torso=np.array(has_torso, bool),
        seg_idx=np.array(seg_idx, np.int32),
        segs=np.asarray(segs, np.float32).reshape(-1, 4),
        meta=np.array([obs.fps, obs.total], np.float64),
        numbers=np.array(nums, np.float64).reshape(-1, 4),  # frame, person, number, confidence
        emb_idx=np.array(emb_idx, np.int32).reshape(-1, 2),
        embs=np.array(embs, np.float16).reshape(len(embs), -1) if embs else np.zeros((0, 0)),
        role_idx=np.array(role_idx, np.int32).reshape(-1, 2),
        role_p=np.array(role_p, np.float16).reshape(-1, 3),
    )


def load_observations(path: Path, motion: CameraMotion, source: str = "model") -> Observations:
    z = np.load(path)
    by: dict[int, FrameObservation] = {
        int(i): FrameObservation(int(i), [], [], []) for i in z["frames"]
    }
    for i, b, sc, k, t, ht in zip(
        z["idx"], z["boxes"], z["scores"], z["kinds"], z["torsos"], z["has_torso"], strict=True
    ):
        fo = by[int(i)]
        d = Detection(
            float(b[0]),
            float(b[1]),
            float(b[2]),
            float(b[3]),
            float(sc),
            "person" if k == 0 else "ball",
        )
        if k == 0:
            fo.people.append(d)
            fo.torsos.append(t if ht else None)
        else:
            fo.balls.append(d)
    if "embs" in z.files and len(z["emb_idx"]):
        for (f, k), v in zip(z["emb_idx"], z["embs"], strict=True):
            if int(f) in by:
                by[int(f)].embeds[int(k)] = np.asarray(v, np.float64)
    if "role_p" in z.files:
        for (f, k), v in zip(z["role_idx"], z["role_p"], strict=True):
            if int(f) in by:
                by[int(f)].roles[int(k)] = np.asarray(v, np.float64)
    for f, k, n, c in z["numbers"] if "numbers" in z.files else []:
        if int(f) in by:
            by[int(f)].numbers[int(k)] = (int(n), float(c))
    segments: dict[int, F64] = defaultdict(lambda: np.zeros((0, 4)))
    for i in np.unique(z["seg_idx"]):
        segments[int(i)] = np.asarray(z["segs"][z["seg_idx"] == i], dtype=np.float64)
    fps, total = z["meta"]
    return Observations(
        motion, [by[k] for k in sorted(by)], dict(segments), float(fps), int(total), {}, source
    )


def _canvas_intrinsics(motion: CameraMotion) -> F64:
    return np.asarray(motion.canvas_intrinsics(), dtype=np.float64)


def _frame_k(motion: CameraMotion, index: int) -> F64:
    return np.asarray(motion._k_frame(index), dtype=np.float64)


def _to_canvas_rot(motion: CameraMotion, index: int) -> F64 | None:
    r = motion._r(index)
    if r is None:
        return None
    return np.asarray(motion.ref_r @ r.T, dtype=np.float64)


def people_on_canvas(
    obs: Observations, min_score: float = 0.5, min_height: float = 40
) -> tuple[F64, F64]:
    """Feet and heads of confidently detected people, in canvas pixels."""
    feet, heads = [], []
    for fo in obs.frames:
        h = obs.motion.frame_to_canvas(fo.index)
        if h is None:
            continue
        for d in fo.people:
            if d.score < min_score or d.height < min_height:
                continue
            cx = (d.x1 + d.x2) / 2
            f, hd = geometry.apply(h, np.array([[cx, d.y2], [cx, d.y1]]))
            feet.append(f)
            heads.append(hd)
    return np.array(feet).reshape(-1, 2), np.array(heads).reshape(-1, 2)


def _fixed_focal(obs: Observations) -> float:
    """Focal length of a fixed camera: the one under which the hall's markings fit two
    orthogonal floor directions best."""
    w, h = obs.motion.frame_size
    segs = (
        np.vstack([s for s in obs.segments.values() if len(s)])
        if obs.segments
        else np.zeros((0, 4))
    )
    if len(segs) < 30:
        raise CalibrationError("too few floor lines to estimate the camera")
    best = (-1.0, float(w))
    for f in np.linspace(0.5, 2.5, 21) * w:
        k = np.array([[f, 0, w / 2], [0, f, h / 2], [0, 0, 1.0]])
        m, length = topview.segment_normals(segs, k)
        share = topview.orientation_from_normals(m, length)[3]
        if share > best[0]:
            best = (share, float(f))
    return best[1]


MIN_FLOOR_FIT = 0.35  # share of the marking length along two floor directions
MIN_VIEW_DEG = 10.0  # players' median angle below the horizon (flatter views are not trusted)


def auto_calibrate(
    obs: Observations, hall: U8, min_view_deg: float = MIN_VIEW_DEG
) -> tuple[Calibration, dict[str, Any]]:
    """Automatic court calibration of the hall image (panorama or median frame).

    Fails (CalibrationError with the reason) when the markings show no clear floor, when the
    camera sees the floor too flatly (`min_view_deg`) or when the court found is implausible."""
    motion = obs.motion
    if not motion.moving:
        f = _fixed_focal(obs)
        motion.focals = [f] * len(motion.focals)
        motion.canvas_f = f
    kc = _canvas_intrinsics(motion)
    ras, rbs, ms, ls = [], [], [], []
    for idx, seg in obs.segments.items():
        rot = _to_canvas_rot(motion, idx)
        if rot is None or len(seg) == 0:
            continue
        k = _frame_k(motion, idx)
        ra, rb = topview.segment_rays(seg, k, rot)
        m, length = topview.segment_normals(seg, k, rot)
        ras.append(ra)
        rbs.append(rb)
        ms.append(m)
        ls.append(length)
    if not ms:
        raise CalibrationError("no floor markings found")
    ra, rb, m, length = np.vstack(ras), np.vstack(rbs), np.vstack(ms), np.concatenate(ls)
    alpha, beta, yaw, fit = topview.orientation_from_normals(m, length)
    if fit < MIN_FLOOR_FIT:
        raise CalibrationError(
            "the hall's markings do not show a clear floor (only "
            f"{fit:.0%} of the line length runs along two floor directions, "
            f"{MIN_FLOOR_FIT:.0%} needed; many lines on walls, nets or railings, or a very low "
            "camera): click the court points"
        )
    up = topview._up(alpha, beta)
    feet, heads = people_on_canvas(obs)
    height = topview.camera_height_from_people(up, feet, heads, kc)
    fr = topview._rays(kc, feet)
    view_deg = topview.view_depression_deg(up, height, fr)
    if view_deg < min_view_deg:
        raise CalibrationError(
            "the camera sees the floor too flatly for an automatic court (players at a median "
            f"{view_deg:.0f} degrees below the horizon, at least {min_view_deg:.0f} needed; "
            f"camera about {height:.1f} m above the floor): click the court points"
        )
    a, b = topview.segments_on_floor(ra, rb, up, height, yaw)
    if len(a) < 50:
        raise CalibrationError("too few markings on the floor")
    d1, d2 = topview.floor_basis(up, yaw)
    floor_to_cam = np.column_stack([d1, d2, -height * up])
    dn = fr @ up
    ok = dn < -1e-3
    pts = fr[ok] * (-height / dn[ok])[:, None]
    feet_m = np.column_stack([pts @ d1, pts @ d2])
    base = {"floor_fit": round(fit, 3), "view_deg": round(view_deg, 1)}

    def court(tv: topview.TopView, view: str) -> tuple[Calibration, dict[str, Any]]:
        info = {**base, "court_view": view}
        return _court_in_view(tv, feet_m, kc, floor_to_cam, hall, feet, info)

    try:
        return court(topview.line_top_view(a, b), "all")
    except CalibrationError as exc:
        first = exc
    # multi-sport halls: the lines of all sports together can hide the court; the colour whose
    # own lines form the handball court best gets a search of its own
    colours = topview.segment_colours(
        line_masks(hall), topview.rays_to_pixels(kc, ra), topview.rays_to_pixels(kc, rb)
    )
    by_colour = topview.colour_views(ra, rb, colours, up, height, yaw)
    ranked = topview.handball_colour(by_colour)
    scores = {k: round(v, 3) for k, v in ranked}
    tried = []
    for name, score in ranked[:2]:
        if score < 0.6 * ranked[0][1]:
            break  # only colours that form the court about as well as the best one
        try:
            calib, info = court(by_colour[name], name)
        except CalibrationError as exc:
            tried.append(f"{name} lines: {exc}")
            continue
        info["colour_scores"] = scores
        return calib, info
    if not tried:
        raise first
    raise CalibrationError(f"{first}; " + "; ".join(tried))


def _court_in_view(
    tv: topview.TopView,
    feet_m: F64,
    k: F64,
    floor_to_cam: F64,
    hall: U8,
    feet: F64,
    base: dict[str, Any],
) -> tuple[Calibration, dict[str, Any]]:
    """The court in one top view: template search (lines and people), the candidates refined on
    the goal frames, the best goal fit checked for plausibility. `k` and `floor_to_cam` map floor
    metres (along the top view's axes) to hall pixels; `feet` are the players' feet in the hall
    image, `feet_m` the same on the floor."""
    courts: list[tuple[F64, float]] = []  # court -> floor metres, line score
    feet_px = (feet_m - np.array(tv.origin)) * tv.ppm
    for t, line_score in topview.search_court(tv, feet_px=feet_px):
        to_floor = tv.pixel_to_floor() @ t
        if any(topview.same_court(to_floor, c[0], 1e-3) for c in courts):
            continue  # the same court from another weighting: refined once (the goal search
            # is local, so courts that merely lie close are each refined)
        courts.append((to_floor, line_score))
    best: tuple[float, F64, float] | None = None
    for to_floor, line_score in courts:
        h = k @ floor_to_cam @ to_floor
        h = h / h[2, 2]
        h2, _, goal = topview.refine_on_goals(h, k, hall)
        if best is None or goal > best[0]:
            best = (goal, h2, line_score)
    assert best is not None
    goal, h, line_score = best
    h = topview.normalise_orientation(h, k)
    r, t = topview.pose_from_homography(h, k)
    centre = -r.T @ t
    calib = Calibration(
        h,
        confidence=float(min(1.0, goal / 0.45)),
        reprojection_px=0.0,
        source="heuristic",
        image_size=(hall.shape[1], hall.shape[0]),
    )
    court_feet = calib.to_court(feet) if len(feet) else np.zeros((0, 2))
    inside = (
        float(
            (
                (court_feet[:, 0] >= -1)
                & (court_feet[:, 0] <= 41)
                & (court_feet[:, 1] >= -1)
                & (court_feet[:, 1] <= 21)
            ).mean()
        )
        if len(court_feet)
        else 0.0
    )
    info = {
        "goal_score": round(goal, 3),
        "line_score": round(line_score, 3),
        "floor_fit": base["floor_fit"],
        "people_on_court": round(inside, 3),
        "camera_height_m": round(float(centre[2]), 2),
        "camera_x_m": round(float(centre[0]), 2),
        "camera_y_m": round(float(centre[1]), 2),
        **{k2: v for k2, v in base.items() if k2 != "floor_fit"},
    }
    # a real camera stands above the floor beside or behind the court, and play is on the court
    # (a camera right above the near sideline is common, so the near side starts at y < 1)
    plausible = 1.5 <= centre[2] <= 25 and (centre[1] < 1 or centre[0] < -1 or centre[0] > 41)
    if not plausible or inside < 0.5 or goal < 0.2:
        raise CalibrationError(f"automatic court not trustworthy ({info})")
    return calib, info


def _torso_colour(
    sample: NDArray[np.float64] | None, floor: F64 | None
) -> NDArray[np.float64] | None:
    if sample is None:
        return None
    lab = np.asarray(sample, dtype=np.float64)
    if floor is not None:
        keep = np.linalg.norm(lab - floor, axis=1) > 18
        lab = lab[keep] if keep.sum() >= 3 else lab
    return np.asarray(np.median(lab, axis=0), dtype=np.float64)


def track(
    obs: Observations,
    calib: Calibration,
    kits: dict[str, tuple[int, int, int]],
    hall: U8 | None = None,
    progress: Progress | None = None,
    rosters: dict[str, set[int]] | None = None,
) -> Any:
    """Tracks, teams and the AnalysisResult from stored observations and a hall calibration.
    `rosters` (team label -> shirt numbers) keeps voted numbers on the roster (numbers.vote)."""
    from handball_vision.numbers import Reading
    from handball_vision.pipeline import _confident_label, _finish
    from handball_vision.teams import TeamAssigner
    from handball_vision.tracking import CourtTracker

    motion = obs.motion
    timings: dict[str, float] = defaultdict(float, obs.timings_s)
    floor = None
    if hall is not None:
        from handball_vision.detection import court_mask

        court = court_mask(calib) > 0
        if court.any():
            floor = (
                cv2.cvtColor(hall, cv2.COLOR_BGR2LAB)[court]
                .reshape(-1, 3)
                .astype(np.float64)
                .mean(axis=0)
            )
    teams = TeamAssigner(kits, floor_lab=floor)
    step_frames = obs.frames[1].index - obs.frames[0].index if len(obs.frames) > 1 else 1
    tracker = CourtTracker(fps=obs.fps / step_frames)
    points = []
    number_reads: dict[int, list[Reading]] = defaultdict(list)
    vectors: dict[int, list[tuple[int, NDArray[np.float64]]]] = defaultdict(list)
    role_samples: dict[int, list[tuple[int, NDArray[np.float64]]]] = defaultdict(list)
    n_dets = n_lost = 0
    for k, fo in enumerate(obs.frames):
        t0 = time.perf_counter()
        to_canvas = motion.frame_to_canvas(fo.index)
        if to_canvas is None:
            n_lost += 1
            frame_calib = None
        else:
            frame_calib = Calibration(
                np.linalg.inv(to_canvas) @ calib.homography,
                calib.confidence,
                calib.reprojection_px,
                calib.source,
                motion.frame_size,
            )
        keep: list[int] = []
        if frame_calib is not None:
            kept = set(id(d) for d in filter_on_court(frame_calib, fo.people))
            keep = [i for i, d in enumerate(fo.people) if id(d) in kept]
        dets = [fo.people[i] for i in keep]
        timings["court_filter"] += time.perf_counter() - t0
        n_dets += len(dets)
        feats = np.array(
            [
                c if (c := _torso_colour(fo.torsos[i], floor)) is not None else [np.nan] * 3
                for i in keep
            ]
        ).reshape(-1, 3)
        t0 = time.perf_counter()
        pos = foot_positions(frame_calib, dets) if frame_calib is not None else np.zeros((0, 2))
        labels = [None if np.isnan(f).any() else _confident_label(teams, f) for f in feats]
        visible = None
        if frame_calib is not None:
            hmat = frame_calib.homography
            fw, fh = motion.frame_size

            def visible(
                pts: F64, hmat: F64 = hmat, fw: int = fw, fh: int = fh
            ) -> NDArray[np.bool_]:
                hom = np.column_stack([pts, np.ones(len(pts))]) @ hmat.T
                w = hom[:, 2]
                with np.errstate(all="ignore"):
                    x, y = hom[:, 0] / w, hom[:, 1] / w
                return np.asarray(
                    (w > 0) & (x > 15) & (x < fw - 15) & (y > 15) & (y < fh - 5), dtype=bool
                )

        stepped = tracker.step(pos, np.array([d.score for d in dets]), None, labels, visible)
        timings["tracking"] += time.perf_counter() - t0
        stepped = [replace(tp, frame=fo.index) for tp in stepped]  # original frame numbers
        for tp in stepped:
            if tp.det_index is not None and not np.isnan(feats[tp.det_index]).any():
                teams.add_sample(tp.track_id, feats[tp.det_index], tp.frame)
            if tp.det_index is not None and keep[tp.det_index] in fo.embeds:
                vectors[tp.track_id].append((fo.index, fo.embeds[keep[tp.det_index]]))
            if tp.det_index is not None and keep[tp.det_index] in fo.roles:
                role_samples[tp.track_id].append((fo.index, fo.roles[keep[tp.det_index]]))
            if tp.det_index is not None and keep[tp.det_index] in fo.numbers:
                num, conf = fo.numbers[keep[tp.det_index]]
                number_reads[tp.track_id].append(Reading(num, conf, fo.index))
        # det_index from here on: the person's index in the frame's observation (all people)
        points += [
            replace(tp, det_index=None if tp.det_index is None else keep[tp.det_index])
            for tp in stepped
        ]
        if progress and k % 50 == 0:
            progress("tracking", k / max(1, len(obs.frames)))
    result = _finish(
        points,
        teams,
        obs.fps,
        calib,
        len(obs.frames),
        n_dets,
        timings,
        obs.detector_source,
        {
            "camera": "moving" if motion.moving else "fixed",
            "motion": {k2: round(v, 3) for k2, v in motion.stats.items()},
            "frames_without_view": n_lost,
            "detect_every": step_frames,
        },
        number_reads,
        vectors,
        role_samples,
        rosters,
    )
    from handball_vision.ballpossession import from_observations

    t0 = time.perf_counter()
    ball = from_observations(obs, result)
    if ball is not None:
        result.extra["ball"] = ball
    result.timings_s["ball"] = time.perf_counter() - t0
    return result
