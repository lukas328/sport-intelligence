"""Pick the clips of the shot gold standard: shots from the official game logs (research, ml/).

The tracker is to be judged where it matters most: shots on goal. The shots come from the official
logs per segment (ml/data/segment_labels/*.json: goals, saves, misses with their time in the
segment, read from the match clock), so the choice does not depend on any detector. Per game at
most PER_GAME shots, outcomes mixed (saves and misses first, they are rarer), none within 10 s of
a training clip of round 9/10 (TRAIN_PRE). A clip covers PRE s before to POST s after the logged
time (the log is a few seconds off, and the shot lies before the log entry).

    python ml/gold/pick_shots.py LIBRARY_JSON TRAIN_PRE_JSON [--per-game 5] [--seed 2026]
writes ml/gold/shot_clips.json in the format of gold_clips.json.
"""

import argparse
import glob
import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
PRE, POST = 7000, 3000
KINDS = ("shot_saved", "shot_missed", "goal")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("library", type=Path)
    ap.add_argument("train_pre", type=Path)
    ap.add_argument("--per-game", type=int, default=5)
    ap.add_argument("--seed", type=int, default=2026)
    a = ap.parse_args()
    lib = json.loads(a.library.read_text())["games"]
    train: dict[str, list[tuple[int, int]]] = {}
    for c in json.loads(a.train_pre.read_text())["clips"].values():
        train.setdefault(c["file"], []).append((c["start_ms"], c["start_ms"] + c["dur_ms"]))
    rnd = random.Random(a.seed)
    clips = []
    for f in sorted(glob.glob(str(HERE.parent / "data" / "segment_labels" / "*.json"))):
        d = json.loads(Path(f).read_text())
        name = d["name"].split(".")[0]
        g = lib[name]
        segs = {s["file"]: s for s in g["segments"]}
        cand = []
        for e in d["entries"]:
            if e["kind"] not in KINDS or e["segment"] not in segs:
                continue
            t = e["segment_ms"]
            seg = segs[e["segment"]]
            samples = (seg.get("clock") or {}).get("samples") or [[180000, 0]]
            dur = samples[-1][0]  # last clock reading: the segment lasts at least this long
            if t - PRE < 0 or t + POST > dur:
                continue
            if any(s - 10000 < t < b + 10000 for s, b in train.get(e["segment"], [])):
                continue
            cand.append(e)
        rnd.shuffle(cand)
        cand.sort(key=lambda e: KINDS.index(e["kind"]))
        pick, used = [], []
        for e in cand:
            # one shot per 12 s of a segment, so clips do not overlap
            if any(u[0] == e["segment"] and abs(u[1] - e["segment_ms"]) < 12000 for u in used):
                continue
            if sum(p["kind"] == e["kind"] for p in pick) >= max(2, a.per_game - 3 if e["kind"] == "goal" else 2):
                continue
            pick.append(e)
            used.append((e["segment"], e["segment_ms"]))
            if len(pick) >= a.per_game:
                break
        for e in sorted(pick, key=lambda e: (e["segment"], e["segment_ms"])):
            seg = segs[e["segment"]]
            clips.append({
                "id": f"w{len(clips):02d}", "game": name, "dataset": g["kaggle_dataset"], "file": e["segment"],
                "start_ms": e["segment_ms"] - PRE, "dur_ms": PRE + POST,
                "fps": g["fps"], "width": 1280, "height": 720,
                "shot": {"kind": e["kind"], "log_ms": PRE, "team": e.get("team")},
            })
    out = {"note": "Shot gold: shots from the official logs, clips 7 s before to 3 s after the logged time "
                   "(ml/gold/pick_shots.py). Fixed once labelling starts.", "clips": clips}
    (HERE / "shot_clips.json").write_text(json.dumps(out, indent=1) + "\n")
    kinds = [c["shot"]["kind"] for c in clips]
    print(len(clips), "clips", {k: kinds.count(k) for k in KINDS}, len({c["game"] for c in clips}), "games")


if __name__ == "__main__":
    main()
