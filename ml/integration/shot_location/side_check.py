"""Team at shot time from the possession phases, on the frozen shot truth (LLM labels).
usage: SHOT_LOC_DIR=... python side_check.py
"today" is goal_candidates.suggest_side; the other rules are exploration on the same labels."""

# ruff: noqa: S301

import collections
import json
import os
import pickle
from pathlib import Path

from handball_vision.events import detect

SP = Path(os.environ["SHOT_LOC_DIR"])
TEAM = {"yellow": "home", "red": "away"}


def today(phases, g):
    near = [p for p in phases if g - 12_000 <= p.end_ms <= g + 3000]
    return max(near, key=lambda p: p.end_ms).team if near else None


def cover(phases, g, back):
    t = g - back
    c = [p for p in phases if p.start_ms <= t <= p.end_ms + 1000]
    return c[-1].team if c else None


def overlap(phases, g, w):
    best, most = None, 0
    for p in phases:
        o = min(p.end_ms, g) - max(p.start_ms, g - w)
        if o > most:
            most, best = o, p.team
    return best


RULES = {
    "today": today,
    "cover-2s": lambda ph, g: cover(ph, g, 2000),
    "cover-1s": lambda ph, g: cover(ph, g, 1000),
    "overlap6s": lambda ph, g: overlap(ph, g, 6000),
    "overlap10s": lambda ph, g: overlap(ph, g, 10_000),
}


def verdict(v, truth):
    return "none" if v is None else "ok" if v == truth else "wrong"


def main():
    truth = json.loads((SP / "wl/truth.json").read_text())
    by_time = {k: collections.Counter() for k in ("release+0", "release+1.5", "release+3")}
    by_cand = {k: collections.Counter() for k in RULES}
    for h, shots in truth.items():
        with (SP / "wo" / f"out_{h}" / "trk.pkl").open("rb") as fh:
            d = pickle.load(fh)
        fps = d["fps"]
        labels = {t: str(v.get("label")) for t, v in d["teams"].items()}
        pts = [(round(f * 1000 / fps), tid, x, y) for f, tid, x, y, _, _ in d["points"]]
        res = detect(pts, labels)
        print(h, "sides", res.sides, "missing", res.missing, "phases", len(res.possessions))
        cands = d["extra"]["goal_candidates"]["shots"]["candidates"]
        for s in shots:
            want, rel = TEAM[s["team"]], s["release_t"] * 1000
            for off, key in ((0, "release+0"), (1500, "release+1.5"), (3000, "release+3")):
                by_time[key][verdict(today(res.possessions, rel + off), want)] += 1
            near = min(cands, key=lambda c: abs(c["goal_ms"] - rel))
            if abs(near["goal_ms"] - rel) > 5000:
                for k in RULES:
                    by_cand[k]["no candidate"] += 1
                continue
            for k, rule in RULES.items():
                by_cand[k][verdict(rule(res.possessions, near["goal_ms"]), want)] += 1
    print(
        "suggest_side at a goal time after the release:", {k: dict(v) for k, v in by_time.items()}
    )
    print("rules at the shot candidates' goal_ms:", {k: dict(v) for k, v in by_cand.items()})


if __name__ == "__main__":
    main()
