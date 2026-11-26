# ruff: noqa: S301
"""Possession per second: position rule (events.detect phases, today's product) vs ball holder
(ballpossession possessions) vs combined. Pre-registered before the labels were seen.
team per second t (centre t + 0.5 s): "home" / "away" / None."""

import pickle
from pathlib import Path

from handball_vision.events import detect

CARRY_S = 3.0  # the last holder's team holds on this long after the last hold (passes, bounces)


def team_of(label):
    if label is None:
        return None
    s = str(label)
    return "home" if s.startswith("home") else "away" if s.startswith("away") else None


def per_second(out: Path, n_s: int):
    with (out / "trk.pkl").open("rb") as fh:
        d = pickle.load(fh)
    fps = d["fps"]
    labels = {t: str(v.get("label")) for t, v in d["teams"].items()}
    pts = [(round(f * 1000 / fps), tid, x, y) for f, tid, x, y, _, _ in d["points"]]
    phases = detect(pts, labels).possessions
    holds = [
        (p["start_ms"], p["end_ms"], team_of(p["team"]))
        for p in (d["extra"].get("ball") or {}).get("possessions", [])
    ]
    holds = [h for h in holds if h[2]]
    pos, ball = [], []
    for t in range(n_s):
        ms = (t + 0.5) * 1000
        c = [p.team for p in phases if p.start_ms <= ms <= p.end_ms]
        pos.append(c[-1] if c else None)
        prev = [h for h in holds if h[0] <= ms]
        last = max(prev, key=lambda h: h[1]) if prev else None
        ball.append(last[2] if last and ms <= last[1] + CARRY_S * 1000 else None)
    comb = [b if b else p for b, p in zip(ball, pos, strict=True)]
    return {"position": pos, "ball": ball, "combined": comb}
