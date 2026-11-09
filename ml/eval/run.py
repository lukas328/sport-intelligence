"""Evaluation harness (BRIEF 10.3): runs stages 2 to 5 on a golden set and prints one table.

Golden set today: synthetic matches (source "synthetic", exact ground truth) generated with fixed
seeds and camera positions: three fixed cameras and two operators that pan (and zoom) with play.
For moving cameras, calibration is measured per frame and detection/tracking only count players
inside the current view. Real annotated matches are added via ml/eval/golden_set/manifest.json
once available (Q-DATA-1, Q-DATA-3); the same metrics apply.

    uv run python ml/eval/run.py [--seconds 60] [--out docs/perf/eval.md]
"""

from __future__ import annotations

import argparse
import json
import tempfile
import time
from pathlib import Path
from typing import Any

import numpy as np

from handball_vision.calibration import court_error_m
from handball_vision.detection import BackgroundDetector, MovingBackgroundDetector, foot_positions
from handball_vision.metrics import (
    DetectionScores,
    detection_scores,
    majority_gt,
    team_accuracy,
    tracking_scores,
)
from handball_vision.motion import estimate_motion
from handball_vision.pipeline import analyse_video, iter_frames
from handball_vision.synthetic import SyntheticConfig, SyntheticMatch

SCENARIOS = [
    {
        "name": "balcony-centre",
        "seed": 7,
        "camera": (20.0, -12.0, 10.0),
        "target": (20.0, 8.0, 0.0),
        "focal_px": 470.0,
    },
    {
        "name": "low-off-centre",
        "seed": 3,
        "camera": (16.0, -13.0, 9.0),
        "target": (20.0, 8.0, 0.0),
        "focal_px": 460.0,
    },
    {
        "name": "high-far",
        "seed": 5,
        "camera": (22.0, -15.0, 12.0),
        "target": (20.0, 8.0, 0.0),
        "focal_px": 470.0,
    },
    {
        "name": "pan-follow",
        "seed": 7,
        "camera": (20.0, -12.0, 10.0),
        "target": (20.0, 8.0, 0.0),
        "focal_px": 900.0,
        "pan": 1.0,
    },
    {
        "name": "pan-zoom",
        "seed": 3,
        "camera": (20.0, -12.0, 10.0),
        "target": (20.0, 8.0, 0.0),
        "focal_px": 900.0,
        "pan": 1.0,
        "zoom": 0.4,
    },
]
TARGETS = {
    "calibration_m": ("<", 0.5),
    "detection_recall": (">=", 0.95),
    "mota": (">=", 0.6),
    "team_accuracy": (">=", 0.97),
    "realtime_factor": ("<=", 0.75),
}


def evaluate(scn: dict[str, object], seconds: float, workdir: Path) -> dict[str, float]:
    cfg = SyntheticConfig(
        seconds=seconds,
        seed=int(scn["seed"]),
        camera=scn["camera"],  # type: ignore[arg-type]
        target=scn["target"],
        focal_px=float(scn["focal_px"]),
        pan=float(scn.get("pan", 0.0)),  # type: ignore[arg-type]
        zoom=float(scn.get("zoom", 0.0)),  # type: ignore[arg-type]
    )  # type: ignore[arg-type]
    match = SyntheticMatch(cfg)
    if match.moving:
        return evaluate_moving(match, scn, seconds, workdir)
    video = workdir / f"{scn['name']}.mp4"
    truth = match.write(video)
    k = cfg.kits
    t0 = time.perf_counter()
    res = analyse_video(
        video,
        {
            "home": k.home,
            "home_gk": k.home_gk,
            "away": k.away,
            "away_gk": k.away_gk,
            "referee": k.referee,
        },
    )
    elapsed = time.perf_counter() - t0

    # detection quality, measured separately per frame
    det = BackgroundDetector(res.calibration)
    det.warm_up([f for i, f in enumerate(iter_frames(video)) if i % 30 == 0])
    preds, truths = [], []
    for frame, gt in zip(iter_frames(video), truth, strict=False):
        preds.append(foot_positions(res.calibration, det.detect([frame])[0]))
        truths.append(np.array([[o.x, o.y] for o in gt.objects if o.label != "ball"]))
    ds: DetectionScores = detection_scores(preds, truths)

    by_frame: dict[int, list] = {}
    for p in res.points:
        by_frame.setdefault(p.frame, []).append(p)
    frames = []
    for gt in truth:
        ps = by_frame.get(gt.index, [])
        objs = [o for o in gt.objects if o.label != "ball"]
        frames.append(
            (
                [p.track_id for p in ps],
                np.array([[p.x, p.y] for p in ps]).reshape(-1, 2),
                [o.object_id for o in objs],
                np.array([[o.x, o.y] for o in objs]),
            )
        )
    ts = tracking_scores(frames)
    labels = {o.object_id: o.label for o in truth[0].objects}
    team_acc = team_accuracy(
        {t: v["label"] for t, v in res.teams.items()}, majority_gt(frames), labels
    )
    return {
        "calibration_m": round(court_error_m(res.calibration, match.h), 3),
        "calibration_confidence": round(res.calibration.confidence, 3),
        "detection_precision": round(ds.precision, 3),
        "detection_recall": round(ds.recall, 3),
        "position_error_m": round(ds.mean_error_m, 3),
        "mota": ts.mota,
        "idf1": ts.idf1,
        "id_switches": ts.id_switches,
        "team_accuracy": round(team_acc, 3),
        "tracks": len(res.teams),
        "realtime_factor": round(elapsed / seconds, 3),
    }


def _in_view(o: Any, size: tuple[int, int]) -> bool:
    return bool(0 <= (o.bbox[0] + o.bbox[2]) / 2 < size[0] and 0 <= o.bbox[3] < size[1])


def evaluate_moving(
    match: SyntheticMatch, scn: dict[str, object], seconds: float, workdir: Path
) -> dict[str, float]:
    """Panning / zooming camera: per-frame calibration, players inside the view only."""
    video = workdir / f"{scn['name']}.mp4"
    truth = match.write(video)
    k = match.cfg.kits
    kits = {
        "home": k.home,
        "home_gk": k.home_gk,
        "away": k.away,
        "away_gk": k.away_gk,
        "referee": k.referee,
    }
    t0 = time.perf_counter()
    motion = estimate_motion(iter_frames(video), expected_frames=len(truth))
    res = analyse_video(video, kits, motion=motion)
    elapsed = time.perf_counter() - t0
    size = match.cfg.size

    det = MovingBackgroundDetector(res.calibration, motion.background(), motion)
    preds, truths, calib_err = [], [], []
    for frame, gt in zip(iter_frames(video), truth, strict=False):
        calib = det.set_frame(gt.index)
        if calib is None or gt.homography is None:
            continue
        if gt.index % 25 == 0:
            calib_err.append(court_error_m(calib, gt.homography))
        preds.append(foot_positions(calib, det.detect([frame])[0]))
        truths.append(
            np.array(
                [[o.x, o.y] for o in gt.objects if o.label != "ball" and _in_view(o, size)]
            ).reshape(-1, 2)
        )
    ds: DetectionScores = detection_scores(preds, truths)

    by_frame: dict[int, list[Any]] = {}
    for p in res.points:
        by_frame.setdefault(p.frame, []).append(p)
    frames = []
    for gt in truth:
        ps = by_frame.get(gt.index, [])
        objs = [o for o in gt.objects if o.label != "ball" and _in_view(o, size)]
        frames.append(
            (
                [p.track_id for p in ps],
                np.array([[p.x, p.y] for p in ps]).reshape(-1, 2),
                [o.object_id for o in objs],
                np.array([[o.x, o.y] for o in objs]).reshape(-1, 2),
            )
        )
    ts = tracking_scores(frames)
    labels = {o.object_id: o.label for o in truth[0].objects}
    team_acc = team_accuracy(
        {t: v["label"] for t, v in res.teams.items()}, majority_gt(frames), labels
    )
    return {
        "calibration_m": round(float(np.median(calib_err)), 3),
        "calibration_confidence": round(res.calibration.confidence, 3),
        "detection_precision": round(ds.precision, 3),
        "detection_recall": round(ds.recall, 3),
        "position_error_m": round(ds.mean_error_m, 3),
        "mota": ts.mota,
        "idf1": ts.idf1,
        "id_switches": ts.id_switches,
        "team_accuracy": round(team_acc, 3),
        "tracks": len(res.teams),
        "realtime_factor": round(elapsed / seconds, 3),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=60)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()
    rows = {}
    with tempfile.TemporaryDirectory() as tmp:
        for scn in SCENARIOS:
            rows[str(scn["name"])] = evaluate(scn, args.seconds, Path(tmp))
            print(scn["name"], rows[str(scn["name"])], flush=True)
    keys = list(next(iter(rows.values())))
    mean = {k: round(float(np.mean([r[k] for r in rows.values()])), 3) for k in keys}
    lines = [
        "| metric | " + " | ".join(rows) + " | mean | target |",
        "|---" * (len(rows) + 3) + "|",
    ]
    for k in keys:
        tgt = TARGETS.get(k)
        mark = ""
        if tgt:
            op, v = tgt
            ok = mean[k] < v if op == "<" else mean[k] >= v if op == ">=" else mean[k] <= v
            mark = f"{op} {v} {'✓' if ok else '✗'}"
        lines.append(
            f"| {k} | " + " | ".join(str(r[k]) for r in rows.values()) + f" | {mean[k]} | {mark} |"
        )
    table = "\n".join(lines)
    print(table)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            "# Evaluation (synthetic golden set)\n\nGenerated by `ml/eval/run.py`. Synthetic footage with exact ground truth;"
            " detector = background model (heuristic). Real matches will be added to the golden set.\n\n"
            "`pan-*`: the camera follows play (tripod pan, `pan-zoom` also zooms); calibration is the median"
            " per-frame court error, detection and tracking count only players inside the current view.\n\n"
            f"Clip length per scenario: {args.seconds:.0f} s at 25 fps, 1280x720, CPU only.\n\n{table}\n"
        )
    if args.json:
        args.json.write_text(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
