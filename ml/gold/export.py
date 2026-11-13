"""Export the gold standard labels with trust tiers (docs/plans/tracking-strategie.md, section 5).

The owner's rough track (followed with the cursor) is never a label: it lags 1 to 2 frames and
misses throws and bounces. It only tells where to look. A label is a precise point:
- "owner": the owner clicked it precisely (precision mode);
- "sure": Claude's point (contact sheets, src "llm") lies within AGREE px of the owner's rough
  track in the same frame or one frame either side: two independent looks agree;
- "track": a smooth run of Claude's points anchored to an owner/sure point (see promote_tracks);
- "check": Claude's point without either; not used until the owner has confirmed it.
States without a position ("out", "hidden" without a point) are kept with their tier.

    python ml/gold/export.py LABELS_DIR CLIPS_JSON OUT_JSON [--agree 60]
LABELS_DIR holds one <clip>.json per clip as ArtifactData exports it.
"""

import argparse
import json
import math
from pathlib import Path


def tier(lab: dict, rough: dict[int, dict], f: int, agree: float) -> str:
    if lab.get("src") != "llm":
        return "owner"
    if lab.get("x") is None:
        return "check"
    for g in (f - 1, f, f + 1):
        r = rough.get(g)
        if (
            r
            and r.get("x") is not None
            and math.hypot(r["x"] - lab["x"], r["y"] - lab["y"]) <= agree
        ):
            return "sure"
    return "check"


def promote_tracks(rows: list[dict], smooth: float = 8.0) -> None:
    """A run of "check" points (frames at most 2 apart) that moves smoothly (second difference
    under `smooth` px) and starts or ends next to an owner or sure point is a followed ball
    flight: tier "track". Fast throws are exactly where the rough track lags, so agreement with
    it cannot confirm them; physical smoothness and the anchor can."""
    pos = [r for r in rows if r["x"] is not None]
    pos.sort(key=lambda r: r["frame"])
    i = 0
    while i < len(pos):
        if pos[i]["tier"] != "check":
            i += 1
            continue
        j = i
        while (
            j + 1 < len(pos)
            and pos[j + 1]["tier"] == "check"
            and pos[j + 1]["frame"] - pos[j]["frame"] <= 2
        ):
            j += 1
        run = pos[i : j + 1]
        before = pos[i - 1] if i > 0 else None
        after = pos[j + 1] if j + 1 < len(pos) else None

        def near(r: dict | None, end: dict) -> bool:
            return (
                bool(r)
                and r["tier"] in ("owner", "sure")
                and abs(r["frame"] - end["frame"]) <= 2
                and math.hypot(r["x"] - end["x"], r["y"] - end["y"])
                <= 40 * abs(r["frame"] - end["frame"])
            )

        chain = (
            ([before] if near(before, run[0]) else [])
            + run
            + ([after] if near(after, run[-1]) else [])
        )
        ok = len(run) >= 2 and len(chain) > len(run)
        for a, b, c in zip(chain, chain[1:], chain[2:], strict=False):
            if b["frame"] - a["frame"] != c["frame"] - b["frame"]:
                continue
            if math.hypot(a["x"] - 2 * b["x"] + c["x"], a["y"] - 2 * b["y"] + c["y"]) > smooth * (
                b["frame"] - a["frame"]
            ):
                ok = False
                break
        if ok:
            for r in run:
                r["tier"] = "track"
        i = j + 1


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("labels_dir", type=Path)
    ap.add_argument("clips_json", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--agree", type=float, default=60.0)
    a = ap.parse_args()
    clips = {c["id"]: c for c in json.loads(a.clips_json.read_text())}
    out, counts = {}, {"owner": 0, "sure": 0, "track": 0, "check": 0}
    for p in sorted(a.labels_dir.glob("g*.json")):
        d = json.loads(p.read_text())
        d = d.get("data", d)
        L = {int(k): v for k, v in d.get("labels", {}).items()}
        rough = {k: v for k, v in L.items() if not v.get("p")}
        rows = []
        for f, v in sorted(L.items()):
            if not v.get("p"):
                continue
            t = tier(v, rough, f, a.agree)
            rows.append({"frame": f, "x": v.get("x"), "y": v.get("y"), "state": v["s"], "tier": t})
        promote_tracks(rows)
        for r in rows:
            counts[r["tier"]] += 1
        c = clips[p.stem]
        out[p.stem] = {
            "fps": c["fps"],
            "frames": c["n"],
            "w": c["w"],
            "h": c["h"],
            "shots": d.get("shots", []),
            "labels": rows,
        }
    a.out.write_text(
        json.dumps({"agree_px": a.agree, "clips": out}, indent=None, separators=(",", ":"))
    )
    print(len(out), "clips;", counts)


if __name__ == "__main__":
    main()
