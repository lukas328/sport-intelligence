"""Track length against who is who on the frozen dev labels (ml/gold/data/identity_dev_v1.json).

    python ml/eval/track_length_dev.py CLIPS_DIR H1_OBS H2_OBS [--max-age S] [--max-gap S]
        [--speed M_PER_S] [--roster]

Runs the product's tracking with changed tracker / stitching parameters (no re-identification,
off since #146) and prints: right / wrong / unnamed among the labelled field players with a
visible number, the named share of all field samples, the number of tracks and their median
length, tracks mixing the two team colours (>= 25 % of >= 20 looks against two reference colours
learned from all looks), and the identity switches the number steps find afterwards
(`split_by_number`, reading-colour pieces). The labels sample field players only: links that join
a spectator or referee to a player do not show in right / wrong; check them on crop pairs too
(docs/plans/produkt-analyse-integration.md, «Track-Länge auf Dev»). Dev only, never the end test.
"""

from __future__ import annotations

import argparse
import collections
import functools
import json
import statistics
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from handball_vision import observe as learned
from handball_vision import pipeline, tracking
from handball_vision.detection import court_mask
from handball_vision.motion import CameraMotion, MotionEstimator
from handball_vision.pipeline import _open, iter_frames
from handball_vision.teams import _feature, learn_kits

LABELS = Path(__file__).resolve().parents[1] / "gold" / "data" / "identity_dev_v1.json"
FILES = {"h1": "sghorgen-h1-5min.mp4", "h2": "sghorgen-h2-5min.mp4"}


def _motion(video: Path) -> CameraMotion:
    _, _, _, total = _open(video)
    est = MotionEstimator(keep_every=max(1, total // 30) if total else 25)
    for frame in iter_frames(video):
        est.add(frame)
    m = est.finish()
    if len(m.samples) > 30:
        step = len(m.samples) / 30
        m.samples = [m.samples[int(k * step)] for k in range(30)]
    return m


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("clips", type=Path)
    ap.add_argument("h1", type=Path)
    ap.add_argument("h2", type=Path)
    ap.add_argument("--max-age", type=float, default=None, help="tracker occlusion buffer, s")
    ap.add_argument("--max-gap", type=float, default=None, help="stitching gap, s")
    ap.add_argument("--speed", type=float, default=None, help="stitching speed limit, m/s")
    ap.add_argument("--roster", action="store_true")
    a = ap.parse_args()
    data = json.loads(LABELS.read_text(encoding="utf-8"))
    squads = {k: set(v) for k, v in data["dev_squads"].items()}

    base_tracker = tracking.CourtTracker

    class Tracker(base_tracker):  # type: ignore[valid-type,misc]
        def __init__(self, *args: Any, **kw: Any) -> None:
            if a.max_age is not None:
                kw["max_age_s"] = a.max_age
            super().__init__(*args, **kw)

    tracking.CourtTracker = Tracker  # type: ignore[misc]
    stitch_kw = {}
    if a.max_gap is not None:
        stitch_kw["max_gap_s"] = a.max_gap
    if a.speed is not None:
        stitch_kw["speed_mps"] = a.speed
    pipeline.stitch = functools.partial(pipeline.stitch, **stitch_kw)  # type: ignore[assignment]

    tot: collections.Counter[str] = collections.Counter()
    lengths: list[float] = []
    mixed = field = 0
    for clip, obs_dir in (("h1", a.h1), ("h2", a.h2)):
        mot = _motion(a.clips / FILES[clip])
        obs = learned.load_observations(obs_dir / "observations.npz", mot)
        for fo in obs.frames:
            fo.embeds = {}
        hall = mot.background()
        calib, _ = learned.auto_calibrate(obs, hall)
        court = court_mask(calib) > 0
        floor = cv2.cvtColor(hall, cv2.COLOR_BGR2LAB)[court].reshape(-1, 3).astype(float).mean(0)
        looks = [
            c
            for fo in obs.frames[::4]
            for t in fo.torsos
            if (c := learned._torso_colour(t, floor)) is not None
        ]
        ref = learn_kits(looks, {})
        home, away = _feature(ref["home"]), _feature(ref["away"])
        rosters = {"home": squads["y"], "away": squads["r"]} if a.roster else None
        res = learned.track(obs, calib, {}, hall, rosters=rosters)
        tot["split_by_number"] += int(res.extra.get("split_by_number", 0) or 0)
        tot["colour_pieces"] += int((res.extra.get("reading_colour") or {}).get("pieces", 0))
        frames = {fo.index: fo for fo in obs.frames}
        span: dict[int, list[int]] = collections.defaultdict(list)
        sides: dict[int, list[str]] = collections.defaultdict(list)
        for p in res.points:
            span[p.track_id].append(p.frame)
            if p.observed and p.det_index is not None:
                col = learned._torso_colour(frames[p.frame].torsos[p.det_index], floor)
                if col is not None:
                    f = _feature(col)
                    dh, da = np.linalg.norm(f - home), np.linalg.norm(f - away)
                    if dh < 0.6 * da or da < 0.6 * dh:
                        sides[p.track_id].append("h" if dh < da else "a")
        lengths += [(max(v) - min(v)) / res.fps for v in span.values()]
        for t, s in sides.items():
            if res.teams.get(t, {}).get("label") in ("home", "away") and len(s) >= 20:
                field += 1
                count = collections.Counter(s)
                mixed += min(count["h"], count["a"]) >= 0.25 * len(s)
        owner = {(p.frame, p.det_index): p.track_id for p in res.points if p.det_index is not None}
        for item in data["items"]:
            if item["clip"] != clip or item["label"] in ("R", "G"):
                continue
            t = owner.get((item["frame"], item["k"]))
            team = res.teams.get(t, {}) if t is not None else {}
            num = team.get("number")
            side = {"home": "y", "away": "r"}.get(str(team.get("label", "")).removesuffix("_gk"))
            tot["field"] += 1
            tot["named"] += num is not None
            if item["label"] == "-":
                continue
            tot["visible"] += 1
            inside = [k for k, v in squads.items() if item["label"] in v]
            truth = item.get("team") or (inside[0] if len(inside) == 1 else None)
            if num is None:
                tot["unnamed"] += 1
            elif num == item["label"] and (truth is None or truth == side):
                tot["right"] += 1
            else:
                tot["wrong"] += 1
    print(
        json.dumps(
            {
                "args": vars(a) | {"clips": str(a.clips), "h1": str(a.h1), "h2": str(a.h2)},
                "right": tot["right"],
                "wrong": tot["wrong"],
                "unnamed": tot["unnamed"],
                "visible": tot["visible"],
                "named_share": round(tot["named"] / max(1, tot["field"]), 3),
                "tracks": len(lengths),
                "median_s": round(statistics.median(lengths), 1) if lengths else None,
                "mixed": f"{mixed}/{field}",
                "split_by_number": tot["split_by_number"],
                "colour_pieces": tot["colour_pieces"],
            }
        )
    )


if __name__ == "__main__":
    main()
