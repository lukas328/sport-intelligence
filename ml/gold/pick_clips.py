"""Pick the clips of the gold standard (docs/plans/tracking-strategie.md, section 5).

One clip of DUR seconds per game of ball test set 2 (ml/ball/test_games.json: 42 games, their
halls never in any training). With clock data the clip lies where the match clock runs without a
break for the whole clip (moments of play); without clock data a random window. Fixed seed, so the
list is reproducible; the list itself is committed (gold_clips.json) and never changes once
labelling starts.

    python ml/gold/pick_clips.py LIBRARY_JSON [--dur 8] [--seed 2026]
"""

import argparse
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "ball"))
from testset_pick import running_ms  # noqa: E402


def windows(seg: dict, dur_ms: int) -> list[int]:
    """Start times (ms) where the clock runs for the whole window (samples about 2 s apart)."""
    run = sorted(running_ms(seg))
    out = []
    for i, a in enumerate(run):
        j = i
        while j + 1 < len(run) and run[j + 1] - run[j] <= 3000:
            j += 1
        if run[j] + 2000 - a >= dur_ms and a >= 2000:
            out.append(a)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("library", type=Path)
    ap.add_argument("--dur", type=float, default=8.0)
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument(
        "--train",
        action="store_true",
        help="training clips: every game NOT in test set 2 or its halls",
    )
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--per-game", type=int, default=1)
    a = ap.parse_args()
    rnd = random.Random(a.seed)
    games = json.load(open(a.library))["games"]
    test = json.load(open(HERE.parent / "ball" / "test_games.json"))["games"]
    if a.train:
        from testset_pick import TEST_HALLS, home_team

        homes = {home_team(g) for g in test}
        test = [
            n
            for n in games
            if n not in test
            and home_team(n) not in homes
            and not any(h in n.lower() for h in TEST_HALLS)
            and games[n].get("segments")
            and games[n].get("kaggle_dataset", "").startswith("handball-segs")
        ]
    dur = int(a.dur * 1000)
    clips = []
    for n in sorted(test):
        g = games[n]
        opts = [(s, t) for s in g["segments"] for t in windows(s, dur)]
        used: list[tuple[str, int]] = []
        for _ in range(a.per_game):
            free = [
                (s, t)
                for s, t in opts
                if all(s["file"] != f or abs(t - u) > 2 * dur for f, u in used)
            ]
            if free:
                s, t = rnd.choice(free)
                run = True
            else:
                s = rnd.choice(g["segments"])
                t = rnd.randrange(10000, 160000 - dur)
                run = False
            used.append((s["file"], t))
            clips.append(
                {
                    "id": (f"t{len(clips):03d}" if a.train else f"g{len(clips):02d}"),
                    "game": n,
                    "dataset": g["kaggle_dataset"],
                    "file": s["file"],
                    "start_ms": t,
                    "dur_ms": dur,
                    "fps": g["fps"],
                    "width": g["width"],
                    "height": g["height"],
                    "clock_running": run,
                }
            )
    out = a.out or HERE / "gold_clips.json"
    json.dump(
        {
            "note": (
                "training clips (games outside test set 2 and its halls)"
                if a.train
                else "gold standard clips, never in any training; see docs/plans/tracking-strategie.md"
            ),
            "clips": clips,
        },
        open(out, "w"),
        indent=1,
    )
    print(
        out,
        len(clips),
        "clips;",
        sum(c["clock_running"] for c in clips),
        "with running clock;",
        sorted({c["fps"] for c in clips}),
    )


if __name__ == "__main__":
    main()
