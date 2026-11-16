"""Export the training ball labels that Claude made without the owner's rough track.

Per clip the latest document (dense pass s2, else keyframe pass s1) holds the overview pass's rough
track (labels without "p") and the precise contact-sheet points (with "p"). As in export.py a
precise point is "sure" when it lies within AGREE px of the rough track at f-1..f+1 (two looks
agree: the whole picture and the 200 px crop) and "track" when it belongs to a smooth run anchored
to a sure point; only these two tiers are exported. On 8 gold clips (pilot, ml/gold/data/
pilot_nolead) 98 % of the sure points lay within 12 px of the gold point.

    python ml/gold/export_train.py STATE_DIR CLIPS_JSON OUT_JSON [--agree 30]
STATE_DIR holds s1/ and s2/ with <clip>_doc.json (ml/gold/data/train1_llm).
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from export import promote_tracks, tier  # noqa: E402

KEEP = ("sure", "track", "confirmed")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("state", type=Path)
    ap.add_argument("clips_json", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--agree", type=float, default=30.0)
    ap.add_argument(
        "--with-check",
        action="store_true",
        help="also export unconfirmed points (tier check): on the owner's review of the gold "
        "clips 98 %% of Claude's check points were the ball, but the pilot put only 92 %% of them "
        "within 12 px",
    )
    ap.add_argument(
        "--reviews",
        type=Path,
        nargs="*",
        default=[],
        help="Ball-oder-nicht exports of the check items (ball -> confirmed, none -> dropped)",
    )
    a = ap.parse_args()
    review = {}
    for rd in a.reviews:
        for q in rd.glob("*.json"):
            v = json.loads(q.read_text())
            review[q.stem] = v.get("data", v)["state"]
    keep = KEEP + (("check",) if a.with_check else ())
    clips = {c["id"]: c for c in json.loads(a.clips_json.read_text())}
    out, counts = {}, {k: 0 for k in ("sure", "track", "confirmed", "check", "rejected", "owner")}
    for cid in sorted(clips):
        p = a.state / "s2" / f"{cid}_doc.json"
        if not p.exists():
            p = a.state / "s1" / f"{cid}_doc.json"
        if not p.exists():
            continue
        L = {int(k): v for k, v in json.loads(p.read_text())["labels"].items()}
        rough = {k: v for k, v in L.items() if not v.get("p")}
        rows = [
            {
                "frame": f,
                "x": v.get("x"),
                "y": v.get("y"),
                "state": v["s"],
                "tier": tier(v, rough, f, a.agree),
            }
            for f, v in sorted(L.items())
            if v.get("p")
        ]
        promote_tracks(rows)
        for r in rows:  # the owner's verdict on unconfirmed points
            if r["tier"] == "check":
                st = review.get(f"{cid}_{r['frame']}")
                r["tier"] = {"ball": "confirmed", "none": "rejected"}.get(st, "check")
        for r in rows:
            counts[r["tier"]] += 1
        c = clips[cid]
        out[cid] = {
            "fps": c["fps"],
            "frames": c["n"],
            "w": c["w"],
            "h": c["h"],
            "labels": [r for r in rows if r["tier"] in keep and r["x"] is not None],
        }
    a.out.write_text(json.dumps({"agree_px": a.agree, "clips": out}, separators=(",", ":")))
    print(len(out), "clips;", counts, "->", sum(len(c["labels"]) for c in out.values()), "labels")


if __name__ == "__main__":
    main()
