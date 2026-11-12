"""Pick frames for a hard-negative labelling round: segments round 7 never saw (not its OWLv2
segments, not the first test's or test set 2's games or halls), at moments where the match clock
runs (games without clock data: any moment). Kaggle then runs the net on them and keeps its peaks (kaggle/hardneg_gpu.py).

    python ml/ball/hardneg_pick.py LIBRARY_JSON R7_OWL_SEL_JSON OUT_PICKS_JSON [--per-game 8]
        [--exclude EARLIER_PICKS_JSON ...] [--clock-only]

--exclude keeps 10 s away from the frames of earlier labelling rounds (they went into training);
--datasets widens the pool (e.g. l01 to l04: halls seen in training, other segments);
--clock-only keeps games with clock data only, so every frame is a moment of play (more balls in
flight, fewer balls held during breaks).
"""
import argparse, json, random, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from testset_pick import DATASETS, TEST_HALLS, home_team, running_ms  # noqa: E402

ROOT = Path(__file__).resolve().parent


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("library", type=Path)
    ap.add_argument("r7_segments", type=Path, help="[[dataset, file], ...] used for round 7's OWL labels")
    ap.add_argument("out", type=Path)
    ap.add_argument("--per-game", type=int, default=8)
    ap.add_argument("--seed", type=int, default=31)
    ap.add_argument("--exclude", type=Path, nargs="*", default=[])
    ap.add_argument("--clock-only", action="store_true")
    ap.add_argument("--datasets", nargs="*", default=DATASETS,
                    help="segment datasets to pick from (default: those of test set 2's pool)")
    a = ap.parse_args()
    rnd = random.Random(a.seed)
    games = json.load(open(a.library))["games"]
    used = {f for _, f in json.load(open(a.r7_segments))}
    earlier: dict[str, list[int]] = {}
    for e in a.exclude:
        for p in json.load(open(e)):
            earlier.setdefault(p["file"], []).append(p["t_ms"])
    test = json.load(open(ROOT / "test_games.json"))["games"]
    test_homes = {home_team(g) for g in test}
    picks = []
    for n in sorted(games):
        g = games[n]
        if g.get("kaggle_dataset") not in a.datasets or n in test or home_team(n) in test_homes:
            continue
        if any(h in n.lower() for h in TEST_HALLS):
            continue
        segs = [s for s in g.get("segments", []) if s["file"] not in used]
        if a.clock_only:
            segs = [s for s in segs if any(5000 <= t <= 170000 for t in running_ms(s))]
        if not segs:
            continue
        for _ in range(a.per_game):
            s = rnd.choice(segs)
            near = earlier.get(s["file"], [])
            run = [t for t in running_ms(s) if 5000 <= t <= 170000 and all(abs(t - e) > 10000 for e in near)]
            if a.clock_only and not run:
                continue
            # with clock data only moments of play; without, any moment (some breaks get in)
            t_ms = rnd.choice(run) + rnd.randrange(0, 2000) if run else rnd.randrange(8000, 170000)
            if any(abs(t_ms - e) <= 10000 for e in near):
                continue
            picks.append({"id": f"{s['file'][:-4]}_{t_ms}", "game": n, "dataset": g["kaggle_dataset"],
                          "file": s["file"], "t_ms": t_ms, "clock_running": bool(run)})
    json.dump(picks, open(a.out, "w"))
    print(len({p["game"] for p in picks}), "games,", len(picks), "frames,",
          len({p["dataset"] for p in picks}), "datasets")


if __name__ == "__main__":
    main()
