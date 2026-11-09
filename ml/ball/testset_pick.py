"""Pick frames for the second ball test set (about 200 balls) from halls not yet in the test.

Games come from the local batches l05 to l13 (not in any ball training so far: round 6 used
b01 to b03, l01 and l02), minus the halls of the first test set (Uznach, Eisenach, Leimental,
Horgen, Cottbus). At most one game per home team (two for national-team games, whose halls
vary), frames only where the match clock runs (the ball is in play) when the game has clock data.
The games are written to `ml/ball/test_games.json`: ball training must leave them out.

    python ml/ball/testset_pick.py LIBRARY_JSON OUT_PICKS_JSON [--games 42] [--per-game 6]
"""
import argparse, collections, json, random
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATASETS = [f"handball-segs-l{n:02d}" for n in range(5, 14)]
TEST_HALLS = ("horgen", "leimental", "uznach", "eisenach", "wetzlar", "cottbus")
LEAGUE_WORDS = {"frauen", "herren", "nati"}


def home_team(name: str) -> str:
    if "_Nati_" in name:
        return "nati"  # national team: halls vary, capped at two games
    t = name.split("_")[1:]  # drop the country
    while t and t[0].lower() in LEAGUE_WORDS:
        t = t[1:]
    t = t[1:]  # league or competition
    while t and (t[0].lower().startswith(("playoff", "final", "halbf", "hz")) or t[0] in ("Final", "HalbF")):
        t = t[1:]
    return (name.split("_")[0] + ":" + (t[0] if t else name)).lower()


def running_ms(seg: dict) -> list[int]:
    """Segment times (ms) where the clock advanced between two samples."""
    s = (seg.get("clock") or {}).get("samples") or []
    return [a for (a, ca), (b, cb) in zip(s, s[1:]) if cb > ca and b - a <= 3000]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("library", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--games", type=int, default=42)
    ap.add_argument("--per-game", type=int, default=6)
    ap.add_argument("--seed", type=int, default=23)
    a = ap.parse_args()
    rnd = random.Random(a.seed)
    games = json.load(open(a.library))["games"]
    cand = sorted(n for n, g in games.items() if g.get("kaggle_dataset") in DATASETS
                  and not any(h in n.lower() for h in TEST_HALLS) and g.get("segments"))
    rnd.shuffle(cand)
    per_home: dict[str, int] = collections.Counter()
    chosen = []
    for n in cand:
        h = home_team(n)
        if per_home[h] >= (2 if "nati" in n.lower() else 1):
            continue
        per_home[h] += 1
        chosen.append(n)
        if len(chosen) == a.games:
            break
    picks = []
    for n in sorted(chosen):
        g = games[n]
        segs = g["segments"]
        for k in range(a.per_game):
            seg = segs[k % len(segs)] if len(segs) >= a.per_game else rnd.choice(segs)
            run = [t for t in running_ms(seg) if 5000 <= t <= 170000]
            t_ms = rnd.choice(run) + rnd.randrange(0, 2000) if run else rnd.randrange(8000, 170000)
            picks.append({"id": f"{seg['file'][:-4]}_{t_ms}", "game": n, "dataset": g["kaggle_dataset"],
                          "file": seg["file"], "t_ms": t_ms, "fps": g.get("fps"), "clock_running": bool(run)})
    json.dump(picks, open(a.out, "w"), indent=0)
    json.dump({"note": "second ball test set (2026-11): leave these games out of ball training",
               "games": sorted(chosen)}, open(ROOT / "test_games.json", "w"), indent=1)
    print(len(chosen), "games,", len(picks), "frames,", sum(p["clock_running"] for p in picks), "with running clock")
    for n in sorted(chosen):
        print(" ", home_team(n), n)


if __name__ == "__main__":
    main()
