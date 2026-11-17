"""Calibration metric on the frozen test set (research, ml/).

    python ml/calib/evaluate.py RESULTS_JSON TRUTH_JSON [--split dev|test|all] [--out OUT_MD]

Per truth frame the clicked keypoints (after the line fit of `truth.py refit`: the model's
projection of each clicked keypoint) are mapped by the calibration (`frame_to_court` of
`run.py calibrate`: camera motion, then the court) and compared with their court position. Per
piece: the median error over its points (metres, capped at 50 m). Classes:

- correct: calibrated and median error <= 1.0 m (`--good`);
- wrong (falsely accepted): calibrated and median error > 1.0 m;
- rejected: no court (`needs_calibration`), with the reason.

Shares with 95 % intervals from a bootstrap over halls (2000 draws; a hall's pieces stay
together). Pieces whose frames were all "not determinable" are left out and counted.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np

HERE = Path(__file__).resolve().parent
CAP_M = 50.0


def truth_points(entry: dict[str, Any]) -> tuple[np.ndarray, np.ndarray] | None:
    """(pixels, court metres) of one truth frame, or None when not determinable."""
    if entry.get("status") == "skip":
        return None
    px = entry.get("refined") or entry.get("points") or {}
    court = entry.get("court") or {}
    names = [n for n in px if n in court]
    if len(names) < 4:
        return None
    return (
        np.array([px[n] for n in names], np.float64),
        np.array([court[n] for n in names], np.float64),
    )


# a pixel near the bottom middle of every proxy frame (1280 x 720, one source gives 1280 x 596):
# the floor right in front of the camera, so its sign marks "in front"
FLOOR_PX = (640.0, 590.0)


def front_sign(frame_to_court: np.ndarray) -> float:
    """Sign of the homogeneous scale for floor points in front of the camera (a homography is
    defined up to its sign, so "w > 0" alone says nothing)."""
    w = frame_to_court[2] @ np.array([FLOOR_PX[0], FLOOR_PX[1], 1.0])
    return 1.0 if w >= 0 else -1.0


def errors_m(m: list[list[float]], px: np.ndarray, court: np.ndarray) -> np.ndarray:
    h = np.array(m, np.float64)
    h = h * front_sign(h)
    q = np.c_[px, np.ones(len(px))] @ h.T
    with np.errstate(divide="ignore", invalid="ignore"):
        xy = q[:, :2] / q[:, 2:3]
        e = np.linalg.norm(xy - court, axis=1)
    e[~np.isfinite(e) | (q[:, 2] <= 0)] = CAP_M  # behind the horizon: as far off as it gets
    return np.minimum(e, CAP_M)


def score(
    results: dict[str, Any], truth: dict[str, Any], pieces: list[dict[str, Any]], good_m: float
) -> list[dict[str, Any]]:
    res = {r["id"]: r for r in results["results"]}
    rows = []
    for p in pieces:
        pid = p["id"]
        frames = {fr: tp for fr, e in truth.get(pid, {}).items() if (tp := truth_points(e))}
        r = res.get(pid)
        row = {"id": pid, "hall": p["hall"], "game": p["game"]}
        if not frames or r is None:
            row["cls"] = "no_truth" if r is not None else "not_run"
            rows.append(row)
            continue
        if not r["ok"]:
            row.update(cls="rejected", reason=r.get("reason", "court"))
            rows.append(row)
            continue
        errs = []
        for fr, (px, court) in frames.items():
            m = r.get("frame_to_court", {}).get(fr)
            errs.append(errors_m(m, px, court) if m is not None else np.full(len(px), CAP_M))
        e = np.concatenate(errs)
        med = float(np.median(e))
        row.update(
            cls="correct" if med <= good_m else "wrong",
            median_m=round(med, 2),
            p90_m=round(float(np.percentile(e, 90)), 2),
            points=len(e),
        )
        rows.append(row)
    return rows


def shares(rows: list[dict[str, Any]], draws: int = 2000, seed: int = 0) -> dict[str, Any]:
    use = [r for r in rows if r["cls"] in ("correct", "wrong", "rejected")]
    by_hall: dict[str, list[str]] = defaultdict(list)
    for r in use:
        by_hall[r["hall"]].append(r["cls"])
    halls = sorted(by_hall)
    out: dict[str, Any] = {"pieces": len(use), "halls": len(halls)}
    if not use:
        return out
    rng = np.random.default_rng(seed)
    classes = ("correct", "wrong", "rejected")
    counts = np.array([[sum(c == k for c in by_hall[h]) for k in classes] for h in halls], float)
    point = counts.sum(0) / counts.sum()
    boot = []
    for _ in range(draws):
        pick = counts[rng.integers(0, len(halls), len(halls))].sum(0)
        boot.append(pick / pick.sum())
    lo, hi = np.percentile(np.array(boot), [2.5, 97.5], axis=0)
    for k, c in enumerate(classes):
        out[c] = {
            "n": int(counts[:, k].sum()),
            "share": round(float(point[k]), 3),
            "ci95": [round(float(lo[k]), 3), round(float(hi[k]), 3)],
        }
    acc = [r for r in use if r["cls"] != "rejected"]
    if acc:
        out["accepted_median_m"] = round(float(np.median([r["median_m"] for r in acc])), 2)
        # of the courts the product accepts, how many are wrong
        out["wrong_of_accepted"] = round(sum(r["cls"] == "wrong" for r in acc) / len(acc), 3)
    out["reasons"] = dict(Counter(r.get("reason") for r in use if r["cls"] == "rejected"))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("results", type=Path)
    ap.add_argument("truth", type=Path)
    ap.add_argument("--split", default="dev", choices=["dev", "test", "all"])
    ap.add_argument("--good", type=float, default=1.0)
    ap.add_argument("--rows", action="store_true")
    a = ap.parse_args()
    pieces = json.loads((HERE / "testset.json").read_text())["pieces"]
    if a.split != "all":
        pieces = [p for p in pieces if p["split"] == a.split]
    rows = score(json.loads(a.results.read_text()), json.loads(a.truth.read_text()), pieces, a.good)
    if a.rows:
        for r in rows:
            print(json.dumps(r, ensure_ascii=False))
    s = shares(rows)
    s["left_out"] = dict(Counter(r["cls"] for r in rows if r["cls"] in ("no_truth", "not_run")))
    print(json.dumps(s, indent=1))


if __name__ == "__main__":
    main()
