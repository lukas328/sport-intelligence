"""Court sides on the frozen dev labels (ml/gold/data/sides_dev_v1.json).

    python ml/eval/sides_dev.py CLIPS_DIR H1_OBS H2_OBS [--no-formation]

Runs the product's tracking and `events_payload` on the observations of the two clips, once as
they are and once with the goalkeeper labels taken off (keepers in the referee cluster or out of
the picture, the staging case), and prints per clip the share of the video with the right side,
the wrong side and no side, and the number of events. `--no-formation` switches the field
players' formation votes off (`events.FORMATION_VOTES`). Dev only, never the end test.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

from handball_gpu_worker.analysis import events_payload, play_intervals
from handball_vision import events
from handball_vision import observe as learned
from handball_vision.motion import CameraMotion, MotionEstimator
from handball_vision.pipeline import _open, iter_frames

LABELS = Path(__file__).resolve().parents[1] / "gold" / "data" / "sides_dev_v1.json"
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


def _shares(sides: list[dict[str, Any]], t0: int, t1: int, truth: str) -> dict[str, float]:
    right = wrong = 0
    for k, s in enumerate(sides):
        end = sides[k + 1]["from_ms"] if k + 1 < len(sides) else t1
        a, b = max(t0, s["from_ms"]), min(t1, end)
        if b > a:
            if s["home_defends"] == truth:
                right += b - a
            else:
                wrong += b - a
    span = max(1, t1 - t0)
    return {
        "right": round(right / span, 3),
        "wrong": round(wrong / span, 3),
        "unknown": round(1 - (right + wrong) / span, 3),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("clips", type=Path)
    ap.add_argument("h1", type=Path)
    ap.add_argument("h2", type=Path)
    ap.add_argument("--no-formation", action="store_true")
    a = ap.parse_args()
    events.FORMATION_VOTES = not a.no_formation
    labels = json.loads(LABELS.read_text(encoding="utf-8"))["clips"]
    for clip, obs_dir in (("h1", a.h1), ("h2", a.h2)):
        mot = _motion(a.clips / FILES[clip])
        obs = learned.load_observations(obs_dir / "observations.npz", mot)
        for fo in obs.frames:
            fo.embeds = {}
        hall = mot.background()
        calib, _ = learned.auto_calibrate(obs, hall)
        play_file = obs_dir / "play.json"
        play = json.loads(play_file.read_text()) if play_file.exists() else None
        res = learned.track(obs, calib, {}, hall, play=play_intervals(play))
        times = [round(p.frame * 1000 / res.fps) for p in res.points]
        t0, t1 = min(times), max(times)
        for keepers in (True, False):
            r = res if keepers else copy.copy(res)
            if not keepers:
                r.teams = {
                    t: {**v, "label": str(v.get("label", "")).removesuffix("_gk")}
                    for t, v in res.teams.items()
                }
            ev = events_payload(r)
            print(
                json.dumps(
                    {
                        "clip": clip,
                        "goalkeepers": keepers,
                        "formation": events.FORMATION_VOTES,
                        **_shares(ev["sides"], t0, t1, labels[clip]["home_defends"]),
                        "events": len(ev["events"]),
                        "missing": ev["missing"],
                    }
                )
            )


if __name__ == "__main__":
    main()
