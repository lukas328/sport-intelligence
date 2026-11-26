"""Who is who on the frozen dev labels (ml/gold/data/identity_dev_v1.json).

    python ml/eval/identity_dev.py CLIPS_DIR H1_OBS H2_OBS [--roster] [--min-readings N]
        [--share S] [--no-merge]

CLIPS_DIR holds sghorgen-h1-5min.mp4 and sghorgen-h2-5min.mp4; H1_OBS / H2_OBS hold the
observations.npz of the clips (people, torsos and shirt-number readings; the camera motion is
estimated again from the clip). Runs the product's tracking and identity steps without
re-identification (off in the product since #146) and prints, over the labelled field players:
the share of all field samples whose track carries a number, and of the samples with a visible
number the right / wrong / unnamed share. A number is right when it matches the label and, for
numbers both teams wear, the track's team. `--roster` passes the dev squads (`dev_squads`; the
yellow team is "home", the lighter of the learned team colours). Dev only: never the end test.
"""

from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path
from typing import Any

from handball_vision import identity, numbers, pipeline
from handball_vision import observe as learned
from handball_vision.motion import CameraMotion, MotionEstimator
from handball_vision.pipeline import _open, iter_frames

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
    ap.add_argument("--roster", action="store_true")
    ap.add_argument("--min-readings", type=int, default=3)
    ap.add_argument("--share", type=float, default=0.7)
    ap.add_argument("--no-merge", action="store_true")
    a = ap.parse_args()
    data = json.loads(LABELS.read_text(encoding="utf-8"))
    squads = {k: set(v) for k, v in data["dev_squads"].items()}

    base_vote = numbers.vote

    def vote(readings: Any, allowed: Any = None, *_: Any, **__: Any) -> Any:
        v = base_vote(readings, allowed, numbers.MIN_CONFIDENCE, a.min_readings)
        undamped = v.confidence / (1 - 0.5 ** (v.readings + 1)) if v is not None else 0.0
        return v if v is not None and undamped >= a.share - 1e-9 else None

    identity.vote = vote  # type: ignore[assignment]
    if a.no_merge:

        def no_merge(points: Any, team_out: Any, reads: Any, fps: float, **_: Any) -> Any:
            for t, rs in reads.items():
                if t in team_out and (v := vote(rs)) is not None:
                    team_out[t].update(number=v.number, number_confidence=v.confidence)
            return points, 0

        pipeline.merge_by_number = no_merge  # type: ignore[assignment]

    def truth_team(item: dict[str, Any]) -> str | None:
        if "team" in item:
            return str(item["team"])
        n = item["label"]
        inside = [k for k, v in squads.items() if n in v]
        return inside[0] if len(inside) == 1 else None

    tot: collections.Counter[str] = collections.Counter()
    for clip, obs_dir in (("h1", a.h1), ("h2", a.h2)):
        mot = _motion(a.clips / FILES[clip])
        obs = learned.load_observations(obs_dir / "observations.npz", mot)
        for fo in obs.frames:
            fo.embeds = {}
        calib, _ = learned.auto_calibrate(obs, mot.background())
        rosters = {"home": squads["y"], "away": squads["r"]} if a.roster else None
        res = learned.track(obs, calib, {}, mot.background(), rosters=rosters)
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
            tt = truth_team(item)
            if num is None:
                tot["unnamed"] += 1
            elif num == item["label"] and (tt is None or tt == side):
                tot["right"] += 1
            else:
                tot["wrong"] += 1
    v = max(1, tot["visible"])
    print(
        json.dumps(
            {
                "args": {k: getattr(a, k) for k in ("roster", "min_readings", "share", "no_merge")},
                "field_samples": tot["field"],
                "named_share": round(tot["named"] / max(1, tot["field"]), 3),
                "visible": tot["visible"],
                "right": tot["right"],
                "wrong": tot["wrong"],
                "unnamed": tot["unnamed"],
                "right_share": round(tot["right"] / v, 3),
                "wrong_share": round(tot["wrong"] / v, 3),
            }
        )
    )


if __name__ == "__main__":
    main()
