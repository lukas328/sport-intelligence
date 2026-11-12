"""Suggestions for the gold labelling page from the prelabel kernel's pre.json.

The ball net's peaks and OWLv2's boxes per frame go into the product's ball path
(handball_vision.balltrack: physically possible tracklets, static spots dropped, best chain); a
frame on the path gets its point as the suggestion, other frames none. Suggestions only save
clicks: every gold label is the owner's decision.

    python ml/gold/suggest.py PRE_JSON PUB_DIR    # writes PUB_DIR/clips.json
"""

import json
import sys
from pathlib import Path

from handball_vision import balltrack


def suggest(c: dict) -> list:
    peaks = []
    for k, r in enumerate(c["pre"]):
        for x, y, s in r["net"]:
            peaks.append(balltrack.Peak(k, x, y, s))
        for x, y, _w, _h, s in r.get("owl", []):
            # OWLv2 scores are low but precise: 0.1 counts like a confident net peak
            peaks.append(balltrack.Peak(k, x, y, min(0.95, 0.3 + 3 * s)))
    fps = c["fps_read"]
    path, _ = balltrack.track(
        peaks,
        fps,
        max_speed=0.9 * c["w"],
        radius=c["w"] / 160,
        min_score=0.3,
        max_gap=3,
        static_cell=None,
    )
    sug: list = [None] * c["frames"]
    for p in path:
        if 0 <= p.frame < len(sug):
            sug[p.frame] = [round(p.x, 1), round(p.y, 1), round(p.score, 2)]
    return sug


def main() -> None:
    pre = json.load(open(sys.argv[1]))["clips"]
    pub = Path(sys.argv[2])
    pub.mkdir(parents=True, exist_ok=True)
    out = []
    for cid in sorted(pre):
        c = pre[cid]
        fps = round(c["fps_read"], 3)
        out.append(
            {
                "id": cid,
                "fps": fps,
                "n": c["frames"],
                "K": max(1, round(fps / 10)),
                "w": c["w"],
                "h": c["h"],
                "sug": suggest(c),
            }
        )
    json.dump(out, open(pub / "clips.json", "w"), separators=(",", ":"))
    cov = sum(sum(s is not None for s in c["sug"]) for c in out) / max(1, sum(c["n"] for c in out))
    print(len(out), "clips;", f"{100 * cov:.0f} % of frames with a suggestion")


if __name__ == "__main__":
    main()
