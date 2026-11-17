"""Shot end test: combine the owner's whole-segment marks with the round-1 answers.

The page "Würfe markieren" (one end-test segment at a time, the owner presses W at each shot and then an outcome
key) stores one doc per segment in the artifact db collection `marks`:
    {seg, game, marks: [{t_s, approx: true, outcome, from_round1?}], done}
`t_s` is an approximate release time in segment seconds (about +/- 1 s); the exact release is derived later from
the ball path in a +/- 1.5 s window. `from_round1` is the cand_t of a round-1 shot the owner confirmed in time.

Input: the `marks` collection saved as JSON files (ArtifactData list with out_dir), i.e. a directory of
<seg>.json documents, each {"id", "data": {...}} or the bare data. Output: ml/gold/data/shot_endtest_marks.json,
a list of shots {seg, file, t_s, approx, kind, source} with source "marks" (new), "marks+r1" (round-1 shot with
a marked time) or "r1" (round-1 shot without a marked time, cand_t as approximate time). Segments not marked
"done" are listed in "open_segments" and their new marks are still included.

These are end-test segments of never-trained halls: frozen, no development or tuning on them.

usage: python ml/gold/shot_marks.py <marks_dir> [--out ml/gold/data/shot_endtest_marks.json]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
KINDS = {"goal", "save", "miss", "unclear", "foul", "open"}


def load_marks(d: Path) -> dict[str, dict]:
    out = {}
    for f in sorted(d.rglob("*.json")):
        raw = json.loads(f.read_text())
        data = raw.get("data", raw) if isinstance(raw, dict) else {}
        seg = data.get("seg") or raw.get("id") or f.stem
        out[seg] = data
    return out


def combine(marks: dict[str, dict], answers: list[dict]) -> dict:
    r1: dict[str, list[dict]] = {}
    for a in answers:
        if a.get("state") == "shot":
            r1.setdefault(a["seg"], []).append(a)
    shots, open_segs = [], []
    for seg in sorted(set(marks) | set(r1)):
        m = marks.get(seg, {})
        if seg in marks and not m.get("done"):
            open_segs.append(seg)
        confirmed = {}
        for x in m.get("marks", []):
            kind = x.get("outcome", "open")
            if kind not in KINDS:
                kind = "open"
            if x.get("from_round1") is not None:
                confirmed[round(float(x["from_round1"]), 1)] = x
                continue
            if kind == "foul":
                continue  # whistled before or at the shot: not a shot for the end test
            shots.append(
                {
                    "seg": seg,
                    "file": seg + ".mp4",
                    "t_s": float(x["t_s"]),
                    "approx": True,
                    "kind": kind,
                    "source": "marks",
                }
            )
        for a in r1.get(seg, []):
            x = confirmed.get(round(float(a["cand_t"]), 1))
            if x is not None:
                shots.append(
                    {
                        "seg": seg,
                        "file": seg + ".mp4",
                        "t_s": float(x["t_s"]),
                        "approx": True,
                        "kind": a.get("kind", "unclear"),
                        "source": "marks+r1",
                        "cand_t": a["cand_t"],
                    }
                )
            else:
                shots.append(
                    {
                        "seg": seg,
                        "file": seg + ".mp4",
                        "t_s": float(a["cand_t"]),
                        "approx": True,
                        "kind": a.get("kind", "unclear"),
                        "source": "r1",
                        "cand_t": a["cand_t"],
                    }
                )
    shots.sort(key=lambda s: (s["seg"], s["t_s"]))
    note = (
        "Shot end test from the owner's whole-segment marks (page 'Würfe markieren') plus round-1 answers. t_s is "
        "an approximate release time (+/- 1 s); the exact release comes later from the ball path. Frozen: no "
        "development or tuning on it."
    )
    return {"note": note, "open_segments": open_segs, "shots": shots}


def main() -> None:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("marks_dir", type=Path)
    p.add_argument("--answers", type=Path, default=HERE / "data" / "shot_endtest_answers.json")
    p.add_argument("--out", type=Path, default=HERE / "data" / "shot_endtest_marks.json")
    a = p.parse_args()
    res = combine(load_marks(a.marks_dir), json.loads(a.answers.read_text())["answers"])
    a.out.write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n")
    by = {}
    for s in res["shots"]:
        by[s["source"]] = by.get(s["source"], 0) + 1
    print(len(res["shots"]), "shots", by, "open segments:", len(res["open_segments"]))


if __name__ == "__main__":
    main()
