"""Calibration test set: one 90 s piece per game, halls and camera kinds broadly mixed (research, ml/).

    python ml/calib/testset.py pick        # -> ml/calib/testset.json (frozen once, see below)

Games: the 42 games of ball test set 2 (ml/ball/test_games.json, 42 halls) plus one game per
of 24 further home teams of the library (ml/data/catalog.json), drawn with a fixed seed; SG
Wädenswil/Horgen (club streams, the product's first users) gets four games. Games marked as not
handball are skipped. Per game one segment among s0, s1, s3, s4 (s2 at 50 % of the video is often
half-time), the piece from 20 s to 110 s of it, like the 39-game measurement of ADR 025.

Hall: the game itself for the 42 test-set games (42 halls), else the home team (first team of
the catalog entry); the bootstrap resamples halls, and the
split puts whole halls into `dev` or `test` (about half each, by a hash of the hall name, so the
split does not move when games are added). `test` is the frozen end test: no tuning on it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
START_S, DUR_S = 20.0, 90.0
EXTRA_SGWH = 4
MAX_OTHER = 24  # further halls besides test set 2 and SG Wädenswil/Horgen


def hall_of(game: dict, test2: set[str]) -> str:
    # the catalog's teams of some test-set games are league words: those 42 games are 42 halls
    teams = game.get("teams") or []
    return game["name"] if game["name"] in test2 or not teams else teams[0]


def split_of(hall: str) -> str:
    return (
        "test"
        if int(hashlib.sha1(hall.encode(), usedforsecurity=False).hexdigest(), 16) % 2
        else "dev"
    )


def pick(a: argparse.Namespace) -> None:
    games = json.loads((ROOT / "ml/data/catalog.json").read_text())["games"]
    test2 = set(json.loads((ROOT / "ml/ball/test_games.json").read_text())["games"])
    skip = set(json.loads((ROOT / "ml/data/not_handball.json").read_text())["games"])
    have = [
        g for g in games if (g.get("video") or {}).get("kaggle_dataset") and g["name"] not in skip
    ]
    rnd = random.Random(a.seed)
    chosen = [g for g in have if g["name"] in test2]
    taken_halls = {hall_of(g, test2) for g in chosen}
    by_hall: dict[str, list[dict]] = {}
    for g in have:
        if g["name"] not in test2:
            by_hall.setdefault(hall_of(g, test2), []).append(g)
    sgwh = sorted(by_hall.pop("SGWaedenswilHorgen", []), key=lambda g: g["name"])
    chosen += rnd.sample(sgwh, min(EXTRA_SGWH, len(sgwh)))
    others = sorted(h for h in by_hall if h not in taken_halls)
    for hall in rnd.sample(others, min(MAX_OTHER, len(others))):
        chosen.append(rnd.choice(sorted(by_hall[hall], key=lambda g: g["name"])))
    out = []
    for g in sorted(chosen, key=lambda g: g["name"]):
        v = g["video"]
        segs = [s for s in range(v.get("segments", 5)) if s != 2] or [0]
        s = rnd.choice(segs)
        hall = hall_of(g, test2)
        out.append(
            {
                "id": f"c{len(out):03d}",
                "game": g["name"],
                "dataset": v["kaggle_dataset"],
                "file": f"{g['name']}_s{s}.mp4",
                "start_s": START_S,
                "dur_s": DUR_S,
                "hall": hall,
                "split": split_of(hall),
                "source_px": [v.get("width"), v.get("height")],
                "fps": v.get("fps"),
            }
        )
    doc = {
        "note": "calibration test set, frozen 2026-11-16 (ml/calib/testset.py); split by hall, "
        "'test' is the end test: no tuning on it",
        "pieces": out,
    }
    (HERE / "testset.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    n_test = sum(p["split"] == "test" for p in out)
    print(len(out), "pieces,", len({p["hall"] for p in out}), "halls,", n_test, "test")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pick")
    p.add_argument("--seed", type=int, default=20261116)
    p.set_defaults(fn=pick)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
