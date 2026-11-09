"""Shirt numbers against the official roster: how many voted numbers exist in the match's rosters,
with and without the roster as a constraint on the vote (`handball_vision.numbers.vote`).

    uv run --project packages/vision python ml/eval/numbers_vs_roster.py \\
        ch-spl2-2024-leimental-arbon --calib path/to/ch-spl2-2024-leimental-arbon-cal.pkl

Works on stored observations with number readings (`data/views/<id>-obs.npz` and
`<id>-motion2.npz`, or `--obs`/`--motion`), the hall calibration (a pickled `Calibration.to_dict()`;
without `--calib` it is estimated from the observations), the kits of `ml/eval/golden_set/manifest.json`
and the official game data `ml/eval/official/<id>.json` (handball.ch "players" with dressNr and
isHome; DHB "log" entries with number and team, which only name players that appear in the log).

The tracks are built as the pipeline builds them (`observe.track`); the readings per track are
taken where the pipeline votes (after stitching, split at identity switches), voted once freely and
once restricted to the team's roster. The manifest does not always say which kit is the home team
(`--home-kit auto` picks the assignment under which more free votes are on the rosters).
"""

from __future__ import annotations

import argparse
import copy
import json
import pickle
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from handball_vision import observe, pipeline
from handball_vision.calibration import Calibration
from handball_vision.motion import CameraMotion
from handball_vision.numbers import MIN_CONFIDENCE, Reading, Vote, vote
from handball_vision.tracking import TrackPoint

ROOT = Path(__file__).resolve().parents[2]
VIEWS = ROOT / "data" / "views"
OFFICIAL = ROOT / "ml" / "eval" / "official"
MANIFEST = ROOT / "ml" / "eval" / "golden_set" / "manifest.json"


def official_rosters(path: Path) -> dict[str, set[int]]:
    """Shirt numbers of the players (not the officials) per side, "home"/"away"."""
    data = json.loads(path.read_text())
    out: dict[str, set[int]] = {"home": set(), "away": set()}
    for p in data.get("players", []):
        if p.get("function") != "teamofficial" and p.get("dressNr") not in (None, ""):
            out["home" if int(p["isHome"]) else "away"].add(int(p["dressNr"]))
    if not any(out.values()):
        for e in data.get("log", []):
            if e.get("number") is not None and e.get("team") in out:
                out[str(e["team"])].add(int(e["number"]))
    return out


def kits_of(clip: str) -> dict[str, tuple[int, int, int]]:
    entry = next(m for m in json.loads(MANIFEST.read_text())["matches"] if m["id"] == clip)

    def bgr(h: str) -> tuple[int, int, int]:
        h = h.lstrip("#")
        return int(h[4:6], 16), int(h[2:4], 16), int(h[0:2], 16)

    kits = {k: bgr(v) for k, v in entry["kits"].items()}
    kits.setdefault("referee", (30, 30, 30))
    return kits


@dataclass
class Captured:
    points: list[TrackPoint]
    team_out: dict[int, dict[str, Any]]
    reads: dict[int, list[Reading]]
    fps: float


def track_and_capture(
    obs: observe.Observations, calib: Calibration, kits: dict[str, tuple[int, int, int]]
) -> Captured:
    """Runs `observe.track` and keeps what goes into the number vote (the pipeline's
    `merge_by_number` is wrapped for that one call)."""
    seen: list[Captured] = []
    original = pipeline.merge_by_number

    def spy(
        points: list[TrackPoint],
        team_out: dict[int, dict[str, Any]],
        reads: dict[int, list[Reading]],
        fps: float,
        *args: Any,
        **kwargs: Any,
    ) -> tuple[list[TrackPoint], int]:
        seen.append(Captured(list(points), copy.deepcopy(team_out), copy.deepcopy(reads), fps))
        return original(points, team_out, reads, fps, *args, **kwargs)

    pipeline.merge_by_number = spy
    try:
        observe.track(obs, calib, kits, obs.motion.background())
    finally:
        pipeline.merge_by_number = original
    if not seen:
        raise SystemExit("no number readings on any track")
    return seen[0]


@dataclass
class Row:
    track: int
    side: str
    readings: Counter[int]
    free: Vote | None
    constrained: Vote | None


def compare(cap: Captured, rosters: dict[str, set[int]]) -> list[Row]:
    """Per track (split at identity switches as in the pipeline): the free and the roster vote."""
    team_out = copy.deepcopy(cap.team_out)
    _, reads, _ = pipeline._split_at_switches(list(cap.points), team_out, cap.reads, {})
    rows = []
    for t, rs in sorted(reads.items()):
        if t not in team_out:
            continue
        side = str(team_out[t]["label"]).removesuffix("_gk")
        if side not in rosters:
            continue
        good = Counter(r.number for r in rs if r.confidence >= MIN_CONFIDENCE)
        rows.append(Row(t, side, good, vote(rs), vote(rs, rosters[side])))
    return rows


def merged_numbers(cap: Captured, rosters: dict[str, set[int]] | None) -> dict[str, list[int]]:
    """Numbers per side after the pipeline's merge (one entry per player track)."""
    team_out = copy.deepcopy(cap.team_out)
    pipeline.merge_by_number(
        list(cap.points), team_out, copy.deepcopy(cap.reads), cap.fps, rosters=rosters
    )
    out: dict[str, list[int]] = {"home": [], "away": []}
    for info in team_out.values():
        side = str(info["label"]).removesuffix("_gk")
        if side in out and info.get("number") is not None:
            out[side].append(int(info["number"]))
    return {k: sorted(v) for k, v in out.items()}


def on_roster(rows: list[Row], rosters: dict[str, set[int]], constrained: bool) -> tuple[int, int]:
    votes = [(r.side, r.constrained if constrained else r.free) for r in rows]
    voted = [(s, v.number) for s, v in votes if v is not None]
    return len(voted), sum(1 for s, n in voted if n in rosters[s])


def fmt(v: Vote | None) -> str:
    if v is None:
        return "-"
    extra = f", {v.corrected} corrected" if v.corrected else ""
    return f"{v.number} ({v.readings}x {v.confidence:.2f}{extra})"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("clip", help="clip id, e.g. ch-spl2-2024-leimental-arbon")
    ap.add_argument("--obs", type=Path)
    ap.add_argument("--motion", type=Path)
    ap.add_argument("--calib", type=Path, help="Calibration.to_dict() as .json or pickle")
    ap.add_argument("--official", type=Path)
    ap.add_argument("--home-kit", choices=("auto", "home", "away"), default="auto")
    args = ap.parse_args()
    clip = args.clip
    obs = observe.load_observations(
        args.obs or VIEWS / f"{clip}-obs.npz",
        CameraMotion.load(args.motion or VIEWS / f"{clip}-motion2.npz"),
    )
    if args.calib:
        if args.calib.suffix == ".json":
            calib = Calibration.from_dict(json.loads(args.calib.read_text()))
        else:  # a pickle written by our own experiments (never load one from elsewhere)
            with args.calib.open("rb") as fh:
                calib = Calibration.from_dict(pickle.load(fh))  # noqa: S301
    else:
        calib, _ = observe.auto_calibrate(obs, obs.motion.background())
    official = official_rosters(args.official or OFFICIAL / f"{clip}.json")
    t0 = time.perf_counter()
    cap = track_and_capture(obs, calib, kits_of(clip))
    n_reads = sum(len(rs) for rs in cap.reads.values())
    print(f"{clip}: tracking {time.perf_counter() - t0:.0f} s, {n_reads} readings on tracks")
    print("official rosters:", {k: sorted(v) for k, v in official.items()})

    swapped = {"home": official["away"], "away": official["home"]}
    options = {"home": official, "away": swapped}
    if args.home_kit == "auto":
        score = {k: on_roster(compare(cap, r), r, False)[1] for k, r in options.items()}
        home_kit = max(score, key=lambda k: score[k])
        print(f"home kit = official {home_kit} team (free votes on roster: {score})")
    else:
        home_kit = args.home_kit
    rosters = options[home_kit]
    rows = compare(cap, rosters)

    print()
    print("| track | team | confident readings | voted | voted with roster |")
    print("|---|---|---|---|---|")
    for r in rows:
        if not r.readings:
            continue
        reads = " ".join(f"{n}x{c}" if c > 1 else str(n) for n, c in r.readings.most_common())
        print(f"| {r.track} | {r.side} | {reads} | {fmt(r.free)} | {fmt(r.constrained)} |")

    with_reads = sum(1 for r in rows if r.readings)
    free_n, free_ok = on_roster(rows, rosters, False)
    con_n, con_ok = on_roster(rows, rosters, True)
    print()
    print(f"tracks with confident readings: {with_reads}")
    print(f"voted without roster: {free_n} tracks, {free_ok} numbers on the official roster")
    print(f"voted with roster:    {con_n} tracks, {con_ok} numbers on the official roster")
    changes = [
        r for r in rows if (r.free and r.free.number) != (r.constrained and r.constrained.number)
    ]
    for r in changes:
        print(f"  track {r.track} ({r.side}): {fmt(r.free)} -> {fmt(r.constrained)}")
    print()
    for label, ros in (("without roster", None), ("with roster", rosters)):
        nums = merged_numbers(cap, ros)
        off = {s: sorted(set(v) - rosters[s]) for s, v in nums.items()}
        print(f"after merging, {label}: {nums} (not on roster: {off})")


if __name__ == "__main__":
    main()
