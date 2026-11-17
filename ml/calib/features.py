"""Features for a check against wrongly accepted courts, and how well each separates (research).

    uv run --project packages/vision python ml/calib/features.py RESULTS_JSON CACHE OUT_JSON
    uv run --project packages/vision python ml/calib/features.py separate OUT_JSON RESULTS_JSON TRUTH_JSON

Per accepted court (`run.py calibrate` results):
- the product's own checks (`info`): goal fit, line score, floor fit, people on the court, camera
  height and position, view angle;
- line agreement in the frames themselves: the court lines projected into each stored frame
  (camera motion, then the court) and the share of the line samples within 3 px of a line pixel of
  that frame (`truth._line_mask`), per frame, with the median and the minimum over the frames
  (the minimum is low when the court fits the middle of the pan but not its ends);
- the peak of that agreement: minus the best agreement of the court shifted by 1.5 m along x or
  y (multi-sport floors have lines everywhere, so a wrong court also meets many lines; a right
  one sits on a sharp peak), median and minimum over the frames;
- the share of the projected court inside the frame (how much of the court a frame shows).

`separate` joins the features with the classes of `evaluate.py` (correct / wrong on the truth)
and prints for each feature the AUC (correct above wrong) and the best threshold that keeps all
correct courts.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import evaluate  # noqa: E402
import truth  # noqa: E402

INFO_KEYS = (
    "goal_score",
    "line_score",
    "floor_fit",
    "people_on_court",
    "camera_height_m",
    "view_deg",
)


def line_mask(img: np.ndarray, tile: int = 160) -> np.ndarray:
    h, w = img.shape[:2]
    out = np.zeros((h, w), np.uint8)
    for y in range(0, h, tile):
        for x in range(0, w, tile):
            out[y : y + tile, x : x + tile] = truth._line_mask(img[y : y + tile, x : x + tile])
    return out


SHIFTS_M = ((1.5, 0.0), (-1.5, 0.0), (0.0, 1.5), (0.0, -1.5))


def _agree(dt: np.ndarray, inv: np.ndarray, pts: np.ndarray) -> tuple[float, float]:
    """Share of court line samples within 3 px of a line pixel, and the share inside the frame."""
    h, w = dt.shape
    q = np.c_[pts, np.ones(len(pts))] @ inv.T
    front = q[:, 2] > 0
    q = q[front, :2] / q[front, 2:3]
    inside = (q[:, 0] >= 0) & (q[:, 0] < w - 1) & (q[:, 1] >= 0) & (q[:, 1] < h - 1)
    shown = float(inside.sum() / len(pts))
    if inside.sum() < 30:
        return float("nan"), shown
    return float((truth._sample(dt, q[inside]) <= 3).mean()), shown


def frame_agreement(img: np.ndarray, frame_to_court: list[list[float]]) -> dict[str, float]:
    """Agreement of the court lines with the frame's line pixels, and its peak: the agreement
    minus the best agreement of the same court shifted by 1.5 m (multi-sport floors have lines
    everywhere, so a wrong court also meets many; a right one sits on a sharp peak)."""
    m = np.array(frame_to_court, np.float64)
    inv = np.linalg.inv(m * evaluate.front_sign(m))  # court -> frame, w > 0 in front
    dt = cv2.distanceTransform(255 - line_mask(img), cv2.DIST_L2, 3)
    agree, shown = _agree(dt, inv, truth.MODEL_PTS)
    shifted = [_agree(dt, inv, truth.MODEL_PTS + np.array(s))[0] for s in SHIFTS_M]
    shifted = [x for x in shifted if np.isfinite(x)]
    peak = agree - max(shifted) if shifted and np.isfinite(agree) else float("nan")
    return {"agree": agree, "shown": shown, "peak": peak}


def features(a: Any) -> None:
    res = json.loads(Path(a.results).read_text())["results"]
    out = {}
    for r in res:
        if not r.get("ok"):
            continue
        f: dict[str, Any] = {k: r["info"].get(k) for k in INFO_KEYS}
        per = []
        for fr, m in r.get("frame_to_court", {}).items():
            img = cv2.imread(str(Path(a.cache) / f"{r['id']}.frames" / f"{int(fr):05d}.jpg"))
            if img is not None:
                per.append(frame_agreement(img, m))
        ag = [p["agree"] for p in per if np.isfinite(p["agree"])]
        f["agree_median"] = round(float(np.median(ag)), 3) if ag else 0.0
        f["agree_min"] = round(float(np.min(ag)), 3) if ag else 0.0
        f["shown_min"] = round(min((p["shown"] for p in per), default=0.0), 3)
        pk = [p["peak"] for p in per if np.isfinite(p["peak"])]
        f["peak_median"] = round(float(np.median(pk)), 3) if pk else -1.0
        f["peak_min"] = round(float(np.min(pk)), 3) if pk else -1.0
        out[r["id"]] = f
        print(r["id"], f, flush=True)
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n")


def auc(pos: list[float], neg: list[float]) -> float:
    if not pos or not neg:
        return float("nan")
    wins = sum((p > n) + 0.5 * (p == n) for p in pos for n in neg)
    return wins / (len(pos) * len(neg))


def separate(a: Any) -> None:
    feats = json.loads(Path(a.features).read_text())
    pieces = json.loads((HERE / "testset.json").read_text())["pieces"]
    pieces = [p for p in pieces if p["split"] == a.split]
    rows = evaluate.score(
        json.loads(Path(a.results).read_text()),
        json.loads(Path(a.truth).read_text()),
        pieces,
        a.good,
    )
    cls = {r["id"]: r["cls"] for r in rows if r["cls"] in ("correct", "wrong")}
    keys = sorted({k for f in feats.values() for k in f})
    print(
        f"{sum(c == 'correct' for c in cls.values())} correct, "
        f"{sum(c == 'wrong' for c in cls.values())} wrong"
    )
    for k in keys:
        pos = [
            feats[i][k]
            for i, c in cls.items()
            if c == "correct" and i in feats and feats[i][k] is not None
        ]
        neg = [
            feats[i][k]
            for i, c in cls.items()
            if c == "wrong" and i in feats and feats[i][k] is not None
        ]
        thr = min(pos) if pos else float("nan")
        kept_wrong = sum(n >= thr for n in neg)
        print(
            f"{k:18s} AUC {auc(pos, neg):.2f}  keep all correct at >= {thr:.3f}: "
            f"{kept_wrong} of {len(neg)} wrong still accepted"
        )


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser()
    if len(sys.argv) > 1 and sys.argv[1] == "separate":
        ap.add_argument("cmd")
        ap.add_argument("features")
        ap.add_argument("results")
        ap.add_argument("truth")
        ap.add_argument("--split", default="dev")
        ap.add_argument("--good", type=float, default=1.0)
        separate(ap.parse_args())
        return
    ap.add_argument("results")
    ap.add_argument("cache")
    ap.add_argument("out")
    features(ap.parse_args())


if __name__ == "__main__":
    main()
