"""Truth for the calibration test set: court keypoints clicked in single frames (research, ml/).

The truth is a set of points per frame: image pixel <-> court metres (the product's keypoint names,
`handball_court.COURT.keypoints`, plus a few more line crossings below). No homography is fitted
for the truth itself, so lens distortion (wide-angle club cameras) does not bias the metric: the
error of a calibration is measured at the clicked points (`evaluate.py`).

Workflow (LLM proposal, owner check, see docs/plans/kalibrierung.md):

    python ml/calib/truth.py grid FRAME_JPG OUT_JPG            # frame with a labelled pixel grid
    python ml/calib/truth.py zoom FRAME_JPG OUT_JPG X Y W H     # region enlarged, 10 px grid
    python ml/calib/truth.py snap PROPOSALS_JSON TRUTH_JSON OVERLAY_DIR
        # proposals: {"<id>": {"<frame>": {"<keypoint>": [x, y], ...}}} (rough, from the grid)
        # crossings of two lines snap to the line pixels within 18 px; posts and marks stay;
        # writes the snapped truth and one overlay per frame (points, names, and the court lines
        # of a homography through the points, only as a visual aid)

Court coordinates as in the product: x 0..40 along the court, y 0..20, y = 0 the sideline nearest
the camera, x = 0 the goal line on the camera's left.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "packages/court"))
sys.path.insert(0, str(ROOT / "packages/vision"))

import itertools  # noqa: E402

from handball_court import COURT  # noqa: E402

_FT = math.sqrt(9.0**2 - 8.5**2)  # where the 9 m line meets the sidelines (x from the goal line)

KEYPOINTS: dict[str, tuple[float, float]] = {
    **COURT.keypoints,
    "free_throw_left_side_low": (_FT, 0.0),
    "free_throw_left_side_high": (_FT, 20.0),
    "free_throw_right_side_low": (40.0 - _FT, 0.0),
    "free_throw_right_side_high": (40.0 - _FT, 20.0),
}
# points that are not a crossing of two straight-ish lines: no snapping
NO_SNAP = {
    "center",
    "penalty_mark_left",
    "penalty_mark_right",
    "post_left_low",
    "post_left_high",
    "post_right_low",
    "post_right_high",
}


def court_polylines() -> list[np.ndarray]:
    out = []
    for name, line in COURT.lines.items():
        if name.startswith(("goal_left", "goal_right")):
            continue
        out.append(np.array(line, dtype=np.float64))
    return out


def grid(a: argparse.Namespace) -> None:
    im = cv2.imread(str(a.frame))
    h, w = im.shape[:2]
    for x in range(0, w, 50):
        major = x % 100 == 0
        cv2.line(im, (x, 0), (x, h), (0, 255, 255) if major else (0, 160, 160), 1)
        if major:
            for y in range(12, h, 160):
                cv2.putText(im, str(x), (x + 2, y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 3)
                cv2.putText(im, str(x), (x + 2, y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
    for y in range(0, h, 50):
        major = y % 100 == 0
        cv2.line(im, (0, y), (w, y), (255, 0, 255) if major else (160, 0, 160), 1)
        if major:
            for x in range(4, w, 200):
                cv2.putText(im, str(y), (x, y - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 3)
                cv2.putText(im, str(y), (x, y - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 255), 1)
    cv2.imwrite(str(a.out), im, [cv2.IMWRITE_JPEG_QUALITY, 90])


def zoom(a: argparse.Namespace) -> None:
    """A region of the frame enlarged (default 2x) with a 10 px grid labelled in frame pixels."""
    im = cv2.imread(str(a.frame))
    x0, y0, w, h = a.x, a.y, a.w, a.h
    crop = cv2.resize(
        im[y0 : y0 + h, x0 : x0 + w], None, fx=a.scale, fy=a.scale, interpolation=cv2.INTER_CUBIC
    )
    for x in range((x0 // 10 + 1) * 10, x0 + w, 10):
        major = x % 50 == 0
        xs = int((x - x0) * a.scale)
        cv2.line(crop, (xs, 0), (xs, crop.shape[0]), (0, 255, 255) if major else (0, 110, 110), 1)
        if major:
            cv2.putText(crop, str(x), (xs + 2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
    for y in range((y0 // 10 + 1) * 10, y0 + h, 10):
        major = y % 50 == 0
        ys = int((y - y0) * a.scale)
        cv2.line(crop, (0, ys), (crop.shape[1], ys), (255, 0, 255) if major else (110, 0, 110), 1)
        if major:
            cv2.putText(crop, str(y), (2, ys - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 255), 1)
    cv2.imwrite(str(a.out), crop, [cv2.IMWRITE_JPEG_QUALITY, 90])


def _line_mask(crop: np.ndarray) -> np.ndarray:
    """Thin structures that differ from the local floor, any colour (bright or dark)."""
    lab = cv2.cvtColor(crop, cv2.COLOR_BGR2LAB).astype(np.float32)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    resp = np.zeros(crop.shape[:2], np.float32)
    for c in range(3):
        ch = lab[:, :, c]
        top = cv2.morphologyEx(ch, cv2.MORPH_TOPHAT, k)
        black = cv2.morphologyEx(ch, cv2.MORPH_BLACKHAT, k)
        resp = np.maximum(resp, np.maximum(top, black) * (1.0 if c == 0 else 1.5))
    thr = max(12.0, float(np.percentile(resp, 85)))
    return (resp > thr).astype(np.uint8) * 255


def snap_point(img: np.ndarray, p: tuple[float, float], r: int = 18) -> tuple[float, float] | None:
    """The crossing of the two line directions nearest to `p` within `r` px, else None."""
    h, w = img.shape[:2]
    x0, y0 = round(p[0]) - 2 * r, round(p[1]) - 2 * r
    x1, y1 = x0 + 4 * r, y0 + 4 * r
    if x0 < 0 or y0 < 0 or x1 > w or y1 > h:
        return None
    mask = _line_mask(img[y0:y1, x0:x1])
    segs = cv2.HoughLinesP(mask, 1, np.pi / 180, threshold=18, minLineLength=r, maxLineGap=4)
    if segs is None or len(segs) < 2:
        return None
    segs = segs[:, 0, :].astype(np.float64)
    ang = np.mod(np.arctan2(segs[:, 3] - segs[:, 1], segs[:, 2] - segs[:, 0]), np.pi)
    length = np.hypot(segs[:, 2] - segs[:, 0], segs[:, 3] - segs[:, 1])
    c = np.array([2 * r, 2 * r], dtype=np.float64) + (np.array(p) - np.round(p))

    def dist(s: np.ndarray) -> float:
        a, b = s[:2], s[2:]
        d = b - a
        return float(abs(d[0] * (c[1] - a[1]) - d[1] * (c[0] - a[0])) / (np.hypot(*d) + 1e-9))

    order = np.argsort(-length)
    first = None
    for i in order:
        if dist(segs[i]) <= r:
            first = i
            break
    if first is None:
        return None
    best = None
    for i in order:
        da = abs(ang[i] - ang[first])
        da = min(da, np.pi - da)
        if da < np.radians(15) or dist(segs[i]) > r:
            continue
        best = i
        break
    if best is None:
        return None

    def hom(s: np.ndarray) -> np.ndarray:
        return np.cross([s[0], s[1], 1.0], [s[2], s[3], 1.0])

    q = np.cross(hom(segs[first]), hom(segs[best]))
    if abs(q[2]) < 1e-9:
        return None
    q = q[:2] / q[2]
    if np.hypot(*(q - c)) > r:
        return None
    return float(q[0] + x0), float(q[1] + y0)


def draw_overlay(
    img: np.ndarray, pts: dict[str, list[float]], snapped: dict[str, bool]
) -> np.ndarray:
    out = img.copy()
    names = [n for n in pts if n in KEYPOINTS]
    if len(names) >= 4:
        src = np.array([KEYPOINTS[n] for n in names], dtype=np.float64)
        dst = np.array([pts[n] for n in names], dtype=np.float64)
        h, _ = cv2.findHomography(src, dst, 0)
        if h is not None:
            for line in court_polylines():
                dense = np.vstack([np.linspace(a, b, 20) for a, b in itertools.pairwise(line)])
                q = cv2.perspectiveTransform(dense[None], h)[0]
                cv2.polylines(out, [q.astype(np.int32)], False, (255, 200, 0), 1, cv2.LINE_AA)
    for n in names:
        x, y = pts[n]
        col = (0, 255, 0) if snapped.get(n) else (0, 165, 255)
        cv2.circle(out, (round(x), round(y)), 5, col, 1, cv2.LINE_AA)
        cv2.drawMarker(out, (round(x), round(y)), col, cv2.MARKER_CROSS, 7, 1)
        cv2.putText(out, n, (int(x) + 6, int(y) - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 0, 0), 3)
        cv2.putText(out, n, (int(x) + 6, int(y) - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.38, col, 1)
    return out


# ---- whole-court fit: homography plus radial lens distortion, anchored on rough points ----


def _distort(q: np.ndarray, k: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    """Undistorted -> distorted pixels, radial k1, k2 about the image centre (radius in widths)."""
    c = np.array([size[0] / 2, size[1] / 2])
    d = (q - c) / size[0]
    r2 = (d**2).sum(1, keepdims=True)
    return c + d * (1 + k[0] * r2 + k[1] * r2**2) * size[0]


def _undistort(p: np.ndarray, k: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    q = p.astype(np.float64).copy()
    for _ in range(20):  # fixed point: q = p - (distort(q) - q)
        q = q - (_distort(q, k, size) - p)
    return q


def project(model: dict[str, Any], court_pts: np.ndarray) -> np.ndarray:
    h = np.array(model["h"], dtype=np.float64)
    q = cv2.perspectiveTransform(np.asarray(court_pts, np.float64)[None], h)[0]
    return _distort(q, np.array(model["k"]), tuple(model["size"]))


def to_court(model: dict[str, Any], px: np.ndarray) -> np.ndarray:
    hinv = np.linalg.inv(np.array(model["h"], dtype=np.float64))
    q = _undistort(np.asarray(px, np.float64), np.array(model["k"]), tuple(model["size"]))
    return cv2.perspectiveTransform(q[None], hinv)[0]


def _model_points(step: float = 0.2) -> np.ndarray:
    pts = []
    for line in court_polylines():
        for a, b in itertools.pairwise(line):
            n = max(2, int(np.linalg.norm(b - a) / step))
            pts.append(np.linspace(a, b, n, endpoint=False))
    return np.vstack(pts)


MODEL_PTS = _model_points()


def fit_model(
    img: np.ndarray, rough: dict[str, list[float]], distortion: bool = True, sigma_px: float = 10.0
) -> tuple[dict[str, Any], dict[str, float]]:
    """Court -> image model through the rough points, refined on the frame's line pixels
    (truncated chamfer distance), radial distortion optional. Returns the model and fit stats."""
    from scipy.optimize import least_squares

    hgt, wid = img.shape[:2]
    size = (wid, hgt)
    names = [n for n in rough if n in KEYPOINTS]
    src = np.array([KEYPOINTS[n] for n in names], np.float64)
    dst = np.array([rough[n] for n in names], np.float64)
    h0, _ = cv2.findHomography(src, dst, 0)
    if h0 is None:
        raise ValueError("rough points give no homography")
    h0 = h0 / h0[2, 2]
    mask = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    lines = np.zeros(mask.shape, np.uint8)
    step = 160  # local line masks (thresholds follow the local floor)
    for y in range(0, hgt, step):
        for x in range(0, wid, step):
            y1, x1 = min(hgt, y + step), min(wid, x + step)
            lines[y:y1, x:x1] = _line_mask(img[y:y1, x:x1])
    dt = cv2.distanceTransform(255 - lines, cv2.DIST_L2, 3).astype(np.float32)

    def unpack(v: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        hh = np.append(v[:8], 1.0).reshape(3, 3)
        k = v[8:10] if distortion else np.zeros(2)
        return hh, k

    def residuals(v: np.ndarray, trunc: float) -> np.ndarray:
        hh, k = unpack(v)
        q = _distort(cv2.perspectiveTransform(MODEL_PTS[None], hh)[0], k, size)
        inside = (q[:, 0] >= 1) & (q[:, 0] < wid - 2) & (q[:, 1] >= 1) & (q[:, 1] < hgt - 2)
        d = np.full(len(q), trunc, np.float64)
        qi = q[inside]
        d[inside] = np.minimum(
            trunc,
            cv2.remap(
                dt, qi[:, 0:1].astype(np.float32), qi[:, 1:2].astype(np.float32), cv2.INTER_LINEAR
            )[:, 0],
        )
        anchor = (_distort(cv2.perspectiveTransform(src[None], hh)[0], k, size) - dst) / sigma_px
        reg = [v[8] * 2.0, v[9] * 2.0] if distortion else []
        return np.concatenate([d / np.sqrt(max(1, inside.sum()) / 40.0), anchor.ravel(), reg])

    v = np.concatenate([h0.ravel()[:8], np.zeros(2)])
    for trunc in (12.0, 6.0, 3.0):
        v = least_squares(
            residuals, v, args=(trunc,), method="trf", loss="soft_l1", x_scale="jac", max_nfev=400
        ).x
    hh, k = unpack(v)
    q = _distort(cv2.perspectiveTransform(MODEL_PTS[None], hh)[0], k, size)
    inside = (q[:, 0] >= 1) & (q[:, 0] < wid - 2) & (q[:, 1] >= 1) & (q[:, 1] < hgt - 2)
    qi = q[inside]
    d = cv2.remap(
        dt, qi[:, 0:1].astype(np.float32), qi[:, 1:2].astype(np.float32), cv2.INTER_LINEAR
    )[:, 0]
    anchor = np.linalg.norm(
        _distort(cv2.perspectiveTransform(src[None], hh)[0], k, size) - dst, axis=1
    )
    model = {"h": hh.tolist(), "k": [float(k[0]), float(k[1])], "size": [wid, hgt]}
    stats = {
        "on_line_2px": round(float((d <= 2).mean()), 3) if len(d) else 0.0,
        "model_pts_in_frame": int(inside.sum()),
        "anchor_px_median": round(float(np.median(anchor)), 1),
        "anchor_px_max": round(float(anchor.max()), 1),
    }
    return model, stats


def draw_model(img: np.ndarray, model: dict[str, Any], rough: dict[str, list[float]]) -> np.ndarray:
    out = img.copy()
    for line in court_polylines():
        dense = np.vstack([np.linspace(a, b, 40) for a, b in itertools.pairwise(line)])
        q = project(model, dense)
        cv2.polylines(out, [q.astype(np.int32)], False, (255, 0, 255), 1, cv2.LINE_AA)
    for _n, p in rough.items():
        cv2.drawMarker(out, (int(p[0]), int(p[1])), (0, 165, 255), cv2.MARKER_TILTED_CROSS, 8, 1)
    return out


def fit(a: argparse.Namespace) -> None:
    """rough points -> fitted model per frame, overlay per frame, truth JSON (status proposed)."""
    props = json.loads(a.proposals.read_text())
    truth = json.loads(a.truth.read_text()) if a.truth.exists() else {}
    a.overlays.mkdir(parents=True, exist_ok=True)
    for pid, frames in props.items():
        for fr, rough in frames.items():
            img = cv2.imread(str(a.cache / f"{pid}.frames" / f"{int(fr):05d}.jpg"))
            if img is None or len(rough) < 4:
                print(pid, fr, "frame missing or fewer than 4 points")
                continue
            model, stats = fit_model(img, rough, distortion=not a.no_distortion)
            truth.setdefault(pid, {})[str(int(fr))] = {
                "rough": rough,
                "model": model,
                "fit": stats,
                "status": "proposed",
            }
            cv2.imwrite(
                str(a.overlays / f"{pid}_{int(fr):05d}.jpg"),
                draw_model(img, model, rough),
                [cv2.IMWRITE_JPEG_QUALITY, 90],
            )
            print(pid, fr, stats, "k", [round(x, 3) for x in model["k"]])
    a.truth.write_text(json.dumps(truth, indent=1) + "\n")


# ---- labelling page (ml/calib/labelling/feld.html) ----


def truth_frames(cache: Path, pid: str) -> list[int]:
    """The frames to label: a fixed camera's one frame, a moving camera's two pan extremes."""
    sys.path.insert(0, str(HERE))
    from run import turning_frames

    from handball_vision.motion import CameraMotion

    motion = CameraMotion.load(cache / f"{pid}.motion.npz")
    have = sorted(int(f.stem) for f in (cache / f"{pid}.frames").glob("*.jpg"))
    if not motion.moving or len(have) < 3:
        return have[:2]
    want = turning_frames(motion, len(motion))
    return [f for f in have if f in (want[0], want[-1])] or have[:2]


def proposal(
    r: dict[str, Any] | None, frame: int, size: tuple[int, int]
) -> dict[str, list[float]] | None:
    """The product's court in this frame as keypoints inside the frame (None when no court)."""
    if not r or not r.get("ok") or str(frame) not in r.get("frame_to_court", {}):
        return None
    inv = np.linalg.inv(np.array(r["frame_to_court"][str(frame)], np.float64))
    out = {}
    for n, (x, y) in KEYPOINTS.items():
        q = inv @ np.array([x, y, 1.0])
        if q[2] <= 0:
            continue
        u, v = q[0] / q[2], q[1] / q[2]
        if 4 <= u <= size[0] - 4 and 4 <= v <= size[1] - 4:
            out[n] = [round(float(u), 1), round(float(v), 1)]
    return out if len(out) >= 4 else None


def items(a: argparse.Namespace) -> None:
    """Frames and items.json for the labelling page; proposals from a calibration run."""
    ps = json.loads((HERE / "testset.json").read_text())["pieces"]
    res = {r["id"]: r for r in json.loads(a.results.read_text())["results"]} if a.results else {}
    (a.out / "frames").mkdir(parents=True, exist_ok=True)
    out = []
    for p in ps:
        pid = p["id"]
        if not (a.cache / f"{pid}.obs.npz").exists():
            continue
        for fr in truth_frames(a.cache, pid):
            src = a.cache / f"{pid}.frames" / f"{fr:05d}.jpg"
            img = cv2.imread(str(src))
            name = f"frames/{pid}_{fr:05d}.jpg"
            cv2.imwrite(str(a.out / name), img, [cv2.IMWRITE_JPEG_QUALITY, 85])
            out.append(
                {
                    "id": f"{pid}_{fr:05d}",
                    "pid": pid,
                    "frame": fr,
                    "img": name,
                    "label": p["game"].replace("_", " "),
                    "proposal": proposal(res.get(pid), fr, (img.shape[1], img.shape[0])),
                }
            )
    (a.out / "items.json").write_text(json.dumps(out, ensure_ascii=False) + "\n")
    print(len(out), "frames,", sum(1 for x in out if x["proposal"]), "with a proposal")


def pull(a: argparse.Namespace) -> None:
    """Answers of the page (a JSON list of {id, data} rows from the artifact's db) -> truth JSON,
    each frame refined on its line pixels (homography plus radial distortion); the refined
    points are kept only when the fit stays near the clicks (median shift <= 6 px)."""
    rows = json.loads(a.answers.read_text())
    truth = json.loads(a.truth.read_text()) if a.truth.exists() else {}
    for row in rows:
        doc = row.get("data", row)
        pid, fr = row["id"].rsplit("_", 1)
        fr = str(int(fr))
        entry: dict[str, Any] = {
            "status": doc["status"],
            "points": doc.get("points", {}),
            "at": doc.get("at"),
            "proposal": doc.get("proposal"),
        }
        pts = entry["points"]
        entry["court"] = {n: list(KEYPOINTS[n]) for n in pts if n in KEYPOINTS}
        if doc["status"] != "skip" and len(pts) >= 4:
            img = cv2.imread(str(a.cache / f"{pid}.frames" / f"{int(fr):05d}.jpg"))
            try:
                model, stats = fit_model(img, pts, distortion=True, sigma_px=a.sigma)
            except ValueError:
                model, stats = None, {}
            if model is not None:
                names = [n for n in pts if n in KEYPOINTS]
                proj = project(model, np.array([KEYPOINTS[n] for n in names]))
                shift = np.linalg.norm(proj - np.array([pts[n] for n in names]), axis=1)
                entry["fit"] = {**stats, "shift_px_median": round(float(np.median(shift)), 1)}
                entry["model"] = model
                if np.median(shift) <= 6.0:
                    entry["refined"] = {
                        n: [round(float(q[0]), 1), round(float(q[1]), 1)]
                        for n, q in zip(names, proj, strict=False)
                    }
                if a.overlays:
                    a.overlays.mkdir(parents=True, exist_ok=True)
                    cv2.imwrite(
                        str(a.overlays / f"{pid}_{int(fr):05d}.jpg"), draw_model(img, model, pts)
                    )
        truth.setdefault(pid, {})[fr] = entry
    a.truth.write_text(json.dumps(truth, indent=1) + "\n")
    n = sum(len(v) for v in truth.values())
    print(
        n,
        "frames in the truth,",
        sum(1 for v in truth.values() for e in v.values() if "refined" in e),
        "refined",
    )


def snap(a: argparse.Namespace) -> None:
    props = json.loads(a.proposals.read_text())
    truth = json.loads(a.truth.read_text()) if a.truth.exists() else {}
    a.overlays.mkdir(parents=True, exist_ok=True)
    for pid, frames in props.items():
        for fr, pts in frames.items():
            img = cv2.imread(str(a.cache / f"{pid}.frames" / f"{int(fr):05d}.jpg"))
            if img is None:
                print(pid, fr, "frame missing")
                continue
            out, snapped, moved = {}, {}, {}
            for n, p in pts.items():
                if n not in KEYPOINTS:
                    print(pid, fr, "unknown keypoint", n)
                    continue
                q = None if n in NO_SNAP else snap_point(img, (p[0], p[1]))
                out[n] = [round(q[0], 1), round(q[1], 1)] if q else [float(p[0]), float(p[1])]
                snapped[n] = q is not None
                moved[n] = round(float(np.hypot(q[0] - p[0], q[1] - p[1])), 1) if q else None
            truth.setdefault(pid, {})[str(int(fr))] = {
                "points": out,
                "court": {n: KEYPOINTS[n] for n in out},
                "snapped": snapped,
                "moved_px": moved,
                "status": "proposed",
            }
            cv2.imwrite(
                str(a.overlays / f"{pid}_{int(fr):05d}.jpg"),
                draw_overlay(img, out, snapped),
                [cv2.IMWRITE_JPEG_QUALITY, 90],
            )
            print(
                pid,
                fr,
                len(out),
                "points,",
                sum(snapped.values()),
                "snapped,",
                "moved",
                [m for m in moved.values() if m is not None],
            )
    a.truth.write_text(json.dumps(truth, indent=1) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("grid")
    p.add_argument("frame", type=Path)
    p.add_argument("out", type=Path)
    p.set_defaults(fn=grid)
    p = sub.add_parser("zoom")
    p.add_argument("frame", type=Path)
    p.add_argument("out", type=Path)
    p.add_argument("x", type=int)
    p.add_argument("y", type=int)
    p.add_argument("w", type=int)
    p.add_argument("h", type=int)
    p.add_argument("--scale", type=float, default=2.0)
    p.set_defaults(fn=zoom)
    p = sub.add_parser("fit")
    p.add_argument("proposals", type=Path)
    p.add_argument("truth", type=Path)
    p.add_argument("overlays", type=Path)
    p.add_argument("--cache", type=Path, required=True)
    p.add_argument("--no-distortion", action="store_true")
    p.set_defaults(fn=fit)
    p = sub.add_parser("items")
    p.add_argument("cache", type=Path)
    p.add_argument("out", type=Path)
    p.add_argument("--results", type=Path)
    p.set_defaults(fn=items)
    p = sub.add_parser("pull")
    p.add_argument("answers", type=Path)
    p.add_argument("truth", type=Path)
    p.add_argument("--cache", type=Path, required=True)
    p.add_argument("--overlays", type=Path)
    p.add_argument("--sigma", type=float, default=6.0)
    p.set_defaults(fn=pull)
    p = sub.add_parser("snap")
    p.add_argument("proposals", type=Path)
    p.add_argument("truth", type=Path)
    p.add_argument("overlays", type=Path)
    p.add_argument("--cache", type=Path, required=True)
    p.set_defaults(fn=snap)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
