"""Staging runs recomputed offline for the goalkeeper rule (#147, 2026-11-26).

Per run a folder with the artefacts from the test bucket (read only): observations.npz,
motion.npz, panorama.jpg, tracks.parquet, play.json, optionally proxy.mp4. The calibration lives
only in the database, so it is recovered from tracks.parquet and the foot points of the
observations (pairs sorted by x in frames with as many people as tracks, then nearest neighbour,
RANSAC).

  uv run --project packages/vision --with pyarrow python ml/integration/staging_offline/keepers.py \
      calib DIR | track DIR | crops DIR

calib: writes DIR/recovered_calib.json. track: `observe.track` with it (no kits), prints teams,
label sources, `missing` and, for "referee" tracks, duration and share near a goal. crops: image
crops of keeper tracks and goal-bound "referee" tracks from DIR/proxy.mp4 to DIR/gk_crops.jpg. For
the comparison run `track` once from a worktree of main.
"""

from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pyarrow.parquet as pq

from handball_vision import observe as ob
from handball_vision.calibration import Calibration
from handball_vision.motion import CameraMotion


def load(d: Path) -> Any:
    return ob.load_observations(d / "observations.npz", CameraMotion.load(d / "motion.npz"))


def canvas_feet(obs: Any, fo: Any) -> np.ndarray | None:
    h = obs.motion.frame_to_canvas(fo.index)
    if h is None or not fo.people:
        return None
    p = np.array([det.foot for det in fo.people], float)
    q = np.c_[p, np.ones(len(p))] @ np.asarray(h).T
    return q[:, :2] / q[:, 2:]


def recover(d: Path) -> None:
    obs = load(d)
    t = pq.read_table(d / "tracks.parquet").to_pydict()
    byf: dict[int, list[tuple[float, float]]] = defaultdict(list)
    for f, x, y, o in zip(t["frame"], t["x"], t["y"], t["observed"], strict=True):
        if o:
            byf[f].append((x, y))
    frames = {fo.index: fo for fo in obs.frames}
    src: list[Any] = []
    dst: list[Any] = []
    for f, pts in byf.items():
        c = canvas_feet(obs, frames[f]) if f in frames else None
        if c is None or len(c) != len(pts) or len(pts) < 4:
            continue
        src += sorted(pts)
        dst += c[np.argsort(c[:, 0])].tolist()
    hmat, _ = cv2.findHomography(
        np.array(src, np.float32), np.array(dst, np.float32), cv2.RANSAC, 25.0, maxIters=20000
    )
    for it in range(5):
        a, b = [], []
        for f, pts in byf.items():
            c = canvas_feet(obs, frames[f]) if f in frames else None
            if c is None:
                continue
            p = np.array(pts, float)
            q = np.c_[p, np.ones(len(p))] @ hmat.T
            for i, qq in enumerate(q[:, :2] / q[:, 2:]):
                dist = np.hypot(*(c - qq).T)
                if dist.min() < 30:
                    a.append(p[i])
                    b.append(c[dist.argmin()])
        sa, sb = np.array(a, np.float32), np.array(b, np.float32)
        hmat, mask = cv2.findHomography(sa, sb, cv2.RANSAC, 8.0, maxIters=20000)
        r = np.c_[sa, np.ones(len(sa))] @ hmat.T
        err = np.hypot(*((r[:, :2] / r[:, 2:]) - sb).T)[mask.ravel() > 0]
        print(
            it,
            len(sa),
            "inliers",
            round(float(mask.mean()), 3),
            "median px",
            round(float(np.median(err)), 2),
        )
    (d / "recovered_calib.json").write_text(json.dumps({"homography": hmat.tolist()}))


def run(d: Path) -> tuple[Any, Any, Calibration]:
    obs = load(d)
    hall = cv2.imread(str(d / "panorama.jpg"))
    h = np.array(json.loads((d / "recovered_calib.json").read_text())["homography"])
    calib = Calibration(h, 0.9, 3.0, "user_correction", (hall.shape[1], hall.shape[0]))
    play = [tuple(x) for x in json.loads((d / "play.json").read_text())["intervals_ms"]]
    return obs, ob.track(obs, calib, {}, hall, play=play), calib


def goal_share(ps: list[Any]) -> float:
    return max(sum(math.hypot(p.x - gx, p.y - 10) < 6.5 for p in ps) / len(ps) for gx in (0, 40))


def observed(res: Any) -> dict[int, list[Any]]:
    by: dict[int, list[Any]] = defaultdict(list)
    for p in res.points:
        if p.observed:
            by[p.track_id].append(p)
    return by


def track(d: Path) -> None:
    _, res, _ = run(d)
    ev = res.detect_events()
    print("tracks", Counter(str(v.get("label")) for v in res.teams.values()))
    print(
        "sources", Counter((str(v.get("label")), v.get("label_source")) for v in res.teams.values())
    )
    print("missing", ev.missing, "events", len(ev.events))
    by = observed(res)
    for tid, v in res.teams.items():
        if v.get("label") == "referee" and tid in by:
            ps = by[tid]
            dur = (ps[-1].frame - ps[0].frame) / res.fps
            print("referee", tid, "dur_s", round(dur, 1), "goal share", round(goal_share(ps), 2))


def crops(d: Path) -> None:
    obs, res, calib = run(d)
    by = observed(res)
    want = [t for t, v in res.teams.items() if str(v.get("label")).endswith("_gk")]
    want += [
        t
        for t, v in res.teams.items()
        if v.get("label") == "referee" and t in by and goal_share(by[t]) >= 0.8
    ]
    cap = cv2.VideoCapture(str(d / "proxy.mp4"))
    rows = []
    for t in want:
        ps = by[t]
        print(
            t,
            res.teams[t].get("label"),
            "x",
            round(float(np.median([p.x for p in ps])), 1),
            "y",
            round(float(np.median([p.y for p in ps])), 1),
        )
        row = []
        for q in (0.15, 0.5, 0.85):
            p = ps[int(q * (len(ps) - 1))]
            hm = np.linalg.inv(obs.motion.frame_to_canvas(p.frame)) @ calib.homography
            v = hm @ np.array([p.x, p.y, 1.0])
            cap.set(cv2.CAP_PROP_POS_FRAMES, p.frame)
            _, im = cap.read()
            pad = cv2.copyMakeBorder(im, 300, 300, 300, 300, cv2.BORDER_CONSTANT)
            x0, y0 = int(v[0] / v[2]) + 240, int(v[1] / v[2]) + 130
            tile = pad[y0 : y0 + 200, x0 : x0 + 120].copy()
            cv2.putText(tile, str(t), (2, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)
            row.append(tile)
        rows.append(np.hstack(row))
    cv2.imwrite(str(d / "gk_crops.jpg"), np.vstack(rows))


if __name__ == "__main__":
    {"calib": recover, "track": track, "crops": crops}[sys.argv[1]](Path(sys.argv[2]))
