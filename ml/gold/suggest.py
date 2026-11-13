"""Suggestions for the gold labelling page from the prelabel kernel's pre.json.

The ball net's peaks and OWLv2's boxes per frame go into the product's ball path
(handball_vision.balltrack: physically possible tracklets, static spots dropped, best chain); a
frame on the path gets its point as the suggestion, other frames none. Suggestions only save
clicks: every gold label is the owner's decision.

    python ml/gold/suggest.py PRE_JSON PUB_DIR [--v2]   # writes PUB_DIR/clips.json; --v2: tracker v2
"""

import json
import sys
from pathlib import Path

from handball_vision import balltrack

sys.path.insert(0, str(Path(__file__).resolve().parent))
V2 = False


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


def suggest_v2(c: dict) -> list:
    """Tracker v2 (tracker.py): 69 % on gold v1 against 32 % for the product's ball path."""
    from tracker import track_clip

    return [[round(q[0], 1), round(q[1], 1), 1.0] if q else None for q in track_clip(c)]


def main() -> None:
    global V2
    V2 = "--v2" in sys.argv
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
                "sug": suggest_v2(c) if V2 else suggest(c),
                # every frame's ball candidates (net peaks >= 0.15, OWLv2 boxes >= 0.08), so the page
                # can snap a rough point (followed with the cursor) to the nearest real candidate
                "cand": [
                    [[p[0], p[1]] for p in r["net"] if p[2] >= 0.15]
                    + [[round(o[0]), round(o[1])] for o in r.get("owl", []) if o[4] >= 0.08]
                    for r in c["pre"]
                ],
            }
        )
    json.dump(out, open(pub / "clips.json", "w"), separators=(",", ":"))
    cov = sum(sum(s is not None for s in c["sug"]) for c in out) / max(1, sum(c["n"] for c in out))
    print(len(out), "clips;", f"{100 * cov:.0f} % of frames with a suggestion")


if __name__ == "__main__":
    main()
