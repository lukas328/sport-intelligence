"""Ball: spots still on the camera's canvas (objects at the bench), dev shot clips (2026-11-25).

Product path (hrp1 960 px on every 3rd frame, the observe outputs of kernels handball-shot-dev-0..4)
around the 41 dev shot clips (`ml/gold/shot_clips.json`, split dev; the test split is never read),
scored against the owner's judgement of 546 tracker points (`ml/gold/data/shot_check_dev_labels.json`,
categories of the wrong ones in `shot_check_dev_fp_cats.json`). A tracker point within 20 px of a
point the owner called a ball counts as right; within 20 px of a point he called wrong as the same
wrong object; elsewhere unknown. Variants: `balltrack2` without and with `world` (canvas positions
from the camera motion), the world-static rule's keep / share / cell.

    uv run --project packages/vision python ml/integration/ball_world_static.py prep OBS_DIR OUT.pkl
    uv run --project packages/vision python ml/integration/ball_world_static.py eval OUT.pkl
"""

from __future__ import annotations

import collections
import dataclasses
import json
import math
import pickle
import sys
from pathlib import Path
from typing import Any

import numpy as np

from handball_vision import ballpossession as bp
from handball_vision import balltrack2 as bt
from handball_vision import observe as ob
from handball_vision.motion import CameraMotion

ROOT = Path(__file__).resolve().parents[2]
GOLD = ROOT / "ml/gold"
MARGIN_S = 4.0


def dev_clips() -> list[dict[str, Any]]:
    return [
        c
        for c in json.loads((GOLD / "shot_clips.json").read_text())["clips"]
        if c["split"] == "dev"
    ]


def prep(obs_dir: Path, dst: Path) -> None:
    out: dict[str, Any] = {}
    loaded: dict[str, Any] = {}
    for c in dev_clips():
        seg = c["file"][:-4]
        if seg not in loaded:
            d = obs_dir / seg
            loaded = {
                seg: ob.load_observations(
                    d / "observations.npz", CameraMotion.load(d / "motion.npz")
                )
            }
        obs = loaded[seg]
        frames = sorted(obs.ball_cands)
        step = bp._net_step(frames)
        a = int((c["start_ms"] / 1000 - MARGIN_S) * obs.fps)
        b = int((c["start_ms"] / 1000 + c["dur_ms"] / 1000 + MARGIN_S) * obs.fps)
        fr = [f for f in range(frames[0], frames[-1] + 1, step) if a <= f <= b]
        peaks = [list(obs.ball_cands.get(f, ())) for f in fr]
        world = bp._canvas_points(obs, fr[0], step, peaks) if fr else None
        out[c["id"]] = {
            "frames": fr,
            "peaks": peaks,
            "world": world,
            "fps": obs.fps / step,
            "seg_fps": obs.fps,
            "width": float(obs.motion.frame_size[0]),
        }
    dst.write_bytes(pickle.dumps(out))


def score(
    prep_: dict[str, Any], p: bt.Params | None, use_world: bool
) -> tuple[collections.Counter, collections.Counter]:
    clips = {c["id"]: c for c in dev_clips()}
    labels = json.loads((GOLD / "data/shot_check_dev_labels.json").read_text())["labels"]
    cats = {
        r["id"]: r["cat"]
        for r in json.loads((GOLD / "data/shot_check_dev_fp_cats.json").read_text())["points"]
    }
    paths = {
        cid: bt.track_windows(
            v["peaks"], v["fps"], v["width"], p=p, world=v["world"] if use_world else None
        )[0]
        for cid, v in prep_.items()
    }
    res: collections.Counter = collections.Counter()
    wrong_cat: collections.Counter = collections.Counter()
    for x in labels:
        if x["from"] != "tracker":
            continue
        v, c = prep_[x["video"]], clips[x["video"]]
        f = (c["start_ms"] / 1000 + x["frame"] / c["fps"]) * v["seg_fps"]
        i = int(np.argmin([abs(g - f) for g in v["frames"]]))
        q = paths[x["video"]][i]
        if q is None:
            res["no_point"] += 1
            continue
        s = 1280 / v["width"]
        d = math.hypot(q[0] * s - x["x"], q[1] * s - x["y"])
        if x["state"] in ("ball", "part"):
            res["right" if d <= 20 else "ball_elsewhere"] += 1
        elif d <= 20:
            res["same_wrong"] += 1
            wrong_cat[cats.get(x["id"], "?")] += 1
        else:
            res["wrong_moved"] += 1
    return res, wrong_cat


def evaluate(path: Path) -> None:
    prep_ = pickle.loads(path.read_bytes())  # noqa: S301 (own file from prep)
    base = bt.Params()
    rows = {"without world": score(prep_, base, False)}
    for keep, frac, cell in (
        (0.0, 0.3, 21.0),
        (0.0, 0.2, 21.0),
        (0.0, 0.5, 21.0),
        (0.0, 0.3, 11.0),
        (0.6, 0.3, 21.0),
    ):
        p = dataclasses.replace(
            base, world_static_keep=keep, world_static_frac=frac, world_static_px=cell
        )
        rows[f"world keep {keep} share {frac} cell {cell}"] = score(prep_, p, True)
    print(
        json.dumps(
            {
                k: {"points": dict(r), "same_wrong_by_category": dict(c)}
                for k, (r, c) in rows.items()
            },
            indent=1,
        )
    )


if __name__ == "__main__":
    if sys.argv[1] == "prep":
        prep(Path(sys.argv[2]), Path(sys.argv[3]))
    else:
        evaluate(Path(sys.argv[2]))
