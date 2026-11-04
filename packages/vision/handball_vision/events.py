"""Automatic event baseline from player tracks (addendum 01, A3; BRIEF 7.2 stage 7).

Without a ball tracker the honest signals in the positions are:

- sides: where each team's goalkeeper stands (defended goal), a lasting flip = side change
- possession phases: one team's field players in the attacking half, the other team's in its own
- throw-offs: one team completely in its own half with a player at the centre point, everybody
  almost standing, then play starts
- goals: a throw-off (that does not open a half) means the other team scored at the end of its
  preceding attack

Every result carries a confidence. Shots, saves and turnovers need the ball and stay with tagging,
imports and the later trained model.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field

BIN_MS = 200
PAUSE_MS = 45_000  # almost nobody on court
BOUNDARY_MS = 90_000  # a long pause followed by a throw-off: probably the next match
CENTRE = (20.0, 10.0)
MIN_SIDE_MS = 45_000  # shortest stretch a side holds (noise lasts seconds, a half 20 to 30 minutes)


@dataclass(frozen=True)
class Detected:
    t_ms: int
    type: str  # throw_off | goal | side_change | possession_change
    team: str | None  # home | away
    confidence: float
    attributes: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class Phase:
    team: str
    start_ms: int
    end_ms: int
    confidence: float
    outcome: str | None = None  # goal | lost | None


@dataclass
class EventResult:
    events: list[Detected]
    possessions: list[Phase]
    sides: list[tuple[int, str]]  # (from t_ms, side home defends: "left" | "right")
    missing: list[str]


def _bins(
    points: list[tuple[int, int, float, float]], teams: dict[int, str]
) -> dict[int, dict[str, list[tuple[float, float]]]]:
    acc: dict[int, dict[int, list[tuple[float, float]]]] = defaultdict(lambda: defaultdict(list))
    for t, tid, x, y in points:
        if teams.get(tid) in ("home", "away", "home_gk", "away_gk"):
            acc[t // BIN_MS][tid].append((x, y))
    out: dict[int, dict[str, list[tuple[float, float]]]] = {}
    for b, per_track in acc.items():
        groups: dict[str, list[tuple[float, float]]] = defaultdict(list)
        for tid, ps in per_track.items():
            mx = sum(p[0] for p in ps) / len(ps)
            my = sum(p[1] for p in ps) / len(ps)
            groups[teams[tid]].append((mx, my))
        out[b] = groups
    return out


def _sides(
    bins: dict[int, dict[str, list[tuple[float, float]]]], window_bins: int = 100
) -> list[tuple[int, str]]:
    """Side the home team defends over time, from both goalkeepers (majority over ~20 s)."""
    votes: list[tuple[int, int]] = []  # (bin, +1 home defends left / -1 right)
    for b in sorted(bins):
        g = bins[b]
        v = 0
        if g.get("home_gk"):
            v += 1 if g["home_gk"][0][0] < 20 else -1
        if g.get("away_gk"):
            v += 1 if g["away_gk"][0][0] > 20 else -1
        if v:
            votes.append((b, 1 if v > 0 else -1))
    if not votes:
        return []
    raw: list[tuple[int, str]] = []
    cur: str | None = None
    for i, (b, _) in enumerate(votes):
        lo, hi = max(0, i - window_bins // 2), min(len(votes), i + window_bins // 2)
        s = sum(v for _, v in votes[lo:hi])
        side = "left" if s >= 0 else "right"
        if side != cur:
            raw.append((b * BIN_MS, side))
            cur = side
    # teams change ends only at half-time: a side that holds for less than MIN_SIDE_MS is noise
    # (few goalkeeper sightings at the start, a keeper running out); it merges into its neighbours
    ends = [t for t, _ in raw[1:]] + [votes[-1][0] * BIN_MS]
    # the last stretch is cut by the end of the video, so it only needs 15 s
    kept = [
        (t, side)
        for k, ((t, side), end) in enumerate(zip(raw, ends, strict=True))
        if end - t >= (15_000 if k == len(raw) - 1 else MIN_SIDE_MS)
    ]
    if not kept:  # a short clip: the majority side
        total = sum(v for _, v in votes)
        return [(votes[0][0] * BIN_MS, "left" if total >= 0 else "right")]
    out: list[tuple[int, str]] = [(votes[0][0] * BIN_MS, kept[0][1])]
    for t, side in kept[1:]:
        if side != out[-1][1]:
            out.append((t, side))
    return out


def _side_at(sides: list[tuple[int, str]], t_ms: int) -> str | None:
    cur = None
    for start, side in sides:
        if start <= t_ms:
            cur = side
    return cur


def _attack_right(team: str, home_defends: str) -> bool:
    return (team == "home") == (home_defends == "left")


def _in_attack_half(x: float, right: bool) -> bool:
    return x > 20 if right else x < 20


def _pauses(
    ordered: list[int], bins: dict[int, dict[str, list[tuple[float, float]]]]
) -> list[tuple[int, int]]:
    """(start_ms, end_ms) of stretches with fewer than 4 field players tracked (missing bins count
    as empty), at least PAUSE_MS long."""
    out: list[tuple[int, int]] = []
    empty_since: int | None = None
    for b in range(ordered[0], ordered[-1] + 1):
        g = bins.get(b, {})
        empty = len(g.get("home", [])) + len(g.get("away", [])) < 4
        if empty and empty_since is None:
            empty_since = b
        elif not empty and empty_since is not None:
            if (b - empty_since) * BIN_MS >= PAUSE_MS:
                out.append((empty_since * BIN_MS, b * BIN_MS))
            empty_since = None
    return out


def detect(points: list[tuple[int, int, float, float]], teams: dict[int, str]) -> EventResult:
    """points: (t_ms, track_id, x, y) in court metres; teams: track_id -> home, home_gk, away, ..."""
    bins = _bins(points, teams)
    missing: list[str] = []
    sides = _sides(bins)
    if not sides:
        return EventResult([], [], [], ["goalkeepers"])
    ordered = sorted(bins)

    # --- possession per bin ---
    label: dict[int, tuple[str | None, float]] = {}
    for b in ordered:
        hd = _side_at(sides, b * BIN_MS)
        best: tuple[str | None, float] = (None, 0.0)  # (team, score)
        for team, other in (("home", "away"), ("away", "home")):
            mine, theirs = bins[b].get(team, []), bins[b].get(other, [])
            if len(mine) < 4 or len(theirs) < 4 or hd is None:
                continue
            right = _attack_right(team, hd)
            a = sum(_in_attack_half(x, right) for x, _ in mine) / len(mine)
            d = sum(_in_attack_half(x, right) for x, _ in theirs) / len(theirs)
            share = min(a, d)  # attackers in the half and the defence back home
            if share >= 0.67 and share > best[1]:
                best = (team, share)
        label[b] = best

    # --- segments (min 2 s, short gaps bridged) ---
    phases: list[Phase] = []
    run_team: str | None = None
    run_start = 0
    run_scores: list[float] = []
    last_seen = 0
    for b in ordered:
        holder, holder_score = label[b]
        if holder is None:
            continue
        if holder != run_team:
            if run_team is not None and (last_seen - run_start) * BIN_MS >= 2000:
                phases.append(
                    Phase(
                        run_team,
                        run_start * BIN_MS,
                        (last_seen + 1) * BIN_MS,
                        round(sum(run_scores) / len(run_scores), 2),
                    )
                )
            run_team, run_start, run_scores = holder, b, []
        run_scores.append(holder_score)
        last_seen = b
    if run_team is not None and (last_seen - run_start) * BIN_MS >= 2000:
        phases.append(
            Phase(
                run_team,
                run_start * BIN_MS,
                (last_seen + 1) * BIN_MS,
                round(sum(run_scores) / len(run_scores), 2),
            )
        )

    # --- throw-offs ---
    # per-track speed (robust to fragmented tracks), median over all field players of a bin
    per_track: dict[int, dict[int, tuple[float, float]]] = defaultdict(dict)
    for t, tid, x, y in points:
        if teams.get(tid) in ("home", "away"):
            per_track[t // BIN_MS][tid] = (x, y)
    speeds: dict[int, float] = {}
    for b in ordered:
        cur, prev_bin = per_track.get(b, {}), per_track.get(b - 1, {})
        moved = sorted(
            math.dist(cur[k], prev_bin[k]) / (BIN_MS / 1000) for k in cur if k in prev_bin
        )
        speeds[b] = moved[len(moved) // 2] if len(moved) >= 4 else 99.0
    events: list[Detected] = []
    stretch: list[int] = []
    stretch_team: str | None = None

    def close_stretch() -> None:
        if stretch_team and len(stretch) * BIN_MS >= 1000:
            end = (stretch[-1] + 1) * BIN_MS
            conf = min(0.9, 0.5 + len(stretch) * BIN_MS / 10_000)
            events.append(Detected(end, "throw_off", stretch_team, round(conf, 2)))

    for b in ordered:
        hd = _side_at(sides, b * BIN_MS)
        who: str | None = None
        if hd is not None and speeds.get(b, 99) < 1.5:
            for team in ("home", "away"):
                mine = bins[b].get(team, [])
                rivals = bins[b].get("away" if team == "home" else "home", [])
                if len(mine) < 4 or len(rivals) < 4:
                    continue
                right = _attack_right(team, hd)
                # one outlier per team is tolerated (tracking noise, a player still walking back)
                own = sum(_in_attack_half(x, right) and abs(x - 20) >= 1.0 for x, _ in mine) <= 1
                at_centre = any(math.dist(p, CENTRE) < 2.5 for p in mine)
                others_home = (
                    sum(not _in_attack_half(x, right) and abs(x - 20) >= 1.0 for x, _ in rivals)
                    <= 1
                )
                if own and at_centre and others_home:
                    who = team
        if who and who == stretch_team and stretch and b - stretch[-1] <= 2:
            stretch.append(b)
        else:
            close_stretch()
            stretch, stretch_team = ([b], who) if who else ([], None)
    close_stretch()
    merged: list[Detected] = []
    for e in events:
        if merged and merged[-1].team == e.team and e.t_ms - merged[-1].t_ms <= 15_000:
            merged[-1] = Detected(e.t_ms, e.type, e.team, max(e.confidence, merged[-1].confidence))
        else:
            merged.append(e)
    events = merged

    # --- pauses and match boundaries (tournament videos, 4.8) ---
    pauses = _pauses(ordered, bins)
    for a, b2 in pauses:
        events.append(Detected(a, "pause", None, 0.9, {"end_ms": b2}))
        restart = [e for e in events if e.type == "throw_off" and 0 <= e.t_ms - b2 <= 60_000]
        if b2 - a >= BOUNDARY_MS and restart:
            events.append(
                Detected(
                    b2,
                    "match_boundary",
                    None,
                    0.7,
                    {"pause_ms": b2 - a, "throw_off_ms": restart[0].t_ms},
                )
            )

    # --- side changes ---
    for t_ms, _ in sides[1:]:
        events.append(Detected(t_ms, "side_change", None, 0.8))
    starts = [0] + [t for t, _ in sides[1:]]

    # --- goals from throw-offs that do not open a half ---
    final_phases = list(phases)
    for ev in [e for e in events if e.type == "throw_off"]:
        if any(0 <= ev.t_ms - s <= 15_000 for s in starts) and not any(
            p.end_ms < ev.t_ms and p.end_ms > max(s for s in starts if s <= ev.t_ms) for p in phases
        ):
            continue  # opening throw-off of a half
        before = [p for p in phases if p.end_ms <= ev.t_ms + 1000 and p.team != ev.team]
        if not before:
            continue
        scorer = before[-1]
        i = phases.index(scorer)
        if ev.t_ms - scorer.end_ms > 12_000 or final_phases[i].outcome == "goal":
            continue  # too long ago, or this attack already has its goal
        conf = round(min(ev.confidence, scorer.confidence) * 0.85, 2)
        events.append(
            Detected(
                scorer.end_ms,
                "goal",
                scorer.team,
                conf,
                {"inferred_from": "throw_off", "throw_off_ms": ev.t_ms},
            )
        )
        final_phases[i] = Phase(
            scorer.team, scorer.start_ms, scorer.end_ms, scorer.confidence, "goal"
        )
    for i, p in enumerate(final_phases):
        nxt = final_phases[i + 1] if i + 1 < len(final_phases) else None
        if nxt is None or nxt.team == p.team:
            continue
        if p.outcome is None:
            final_phases[i] = Phase(p.team, p.start_ms, p.end_ms, p.confidence, "lost")
        events.append(Detected(p.end_ms, "possession_change", nxt.team, p.confidence))
    return EventResult(sorted(events, key=lambda e: e.t_ms), final_phases, sides, missing)


def score(
    found: list[Detected], truth: list[dict[str, object]], kind: str, tol_ms: int
) -> dict[str, float]:
    """Precision/recall of one event type against ground truth (same team, within tolerance)."""
    f = [e for e in found if e.type == kind]
    t = [e for e in truth if e["type"] == kind]
    used: set[int] = set()
    hits = 0
    for e in f:
        for i, g in enumerate(t):
            if (
                i not in used
                and abs(int(str(g["t_ms"])) - e.t_ms) <= tol_ms
                and (g["team"] is None or g["team"] == e.team)
            ):
                used.add(i)
                hits += 1
                break
    return {
        "found": len(f),
        "truth": len(t),
        "precision": hits / len(f) if f else (1.0 if not t else 0.0),
        "recall": hits / len(t) if t else 1.0,
    }


def refine_teams(
    points: list[tuple[int, int, float, float]],
    labels: dict[int, str],
    confidence: dict[int, float],
    min_conf: float = 0.75,
) -> dict[int, str]:
    """Team labels with a second signal besides the kit colour (addendum 01, 4.8).

    At a throw-off both teams stand completely in their own half and nobody moves. Those moments
    are found without trusting the labels (field players split by the centre line, almost
    standing); every track seen there votes for the team that defends that half. Tracks whose
    colour assignment is uncertain take the vote of at least 5 such moments with 80 % agreement.
    """
    bins: dict[int, dict[int, tuple[float, float]]] = defaultdict(dict)
    for t, tid, x, y in points:
        if labels.get(tid) in ("home", "away"):
            bins[t // BIN_MS][tid] = (x, y)
    gk: dict[str, list[float]] = {"home_gk": [], "away_gk": []}
    for _t, tid, x, _y in points:
        if labels.get(tid) in gk:
            gk[labels[tid]].append(x)
    if not gk["home_gk"] and not gk["away_gk"]:
        return dict(labels)
    home_left = (
        sum(gk["home_gk"]) / len(gk["home_gk"]) < 20
        if gk["home_gk"]
        else sum(gk["away_gk"]) / len(gk["away_gk"]) > 20
    )
    votes: dict[int, list[str]] = defaultdict(list)
    for b, cur in bins.items():
        prev = bins.get(b - 1, {})
        moved = sorted(math.dist(cur[k], prev[k]) / (BIN_MS / 1000) for k in cur if k in prev)
        if len(cur) < 10 or len(moved) < 8 or moved[len(moved) // 2] > 1.0:
            continue
        left = [k for k, (x, _) in cur.items() if x < 19.5]
        right = [k for k, (x, _) in cur.items() if x > 20.5]
        if len(left) < 4 or len(right) < 4 or len(left) + len(right) < len(cur) - 2:
            continue
        for k in left:
            votes[k].append("home" if home_left else "away")
        for k in right:
            votes[k].append("away" if home_left else "home")
    out = dict(labels)
    for tid, vs in votes.items():
        if confidence.get(tid, 1.0) >= min_conf or len(vs) < 5:
            continue
        top = max(set(vs), key=vs.count)
        if vs.count(top) / len(vs) >= 0.8:
            out[tid] = top
    return out


def assign_goalkeepers(
    points: list[tuple[int, int, float, float]],
    teams: dict[int, str],
    min_track_ms: int = 10_000,
    area_share: float = 0.6,
    bin_ms: int = 2_000,
) -> dict[int, str]:
    """Goalkeepers by position, not by shirt colour (kit colours entered for a match are often
    wrong or missing for goalkeepers).

    A track that spends most of its time within 6.5 m of a goal is a goalkeeper. Its team: during
    set attacks the defending team stands closer to its own goal than the attacking team; the vote
    over the goalkeeper's time span says which team defended that goal (side changes included).
    `points` are (t_ms, track_id, x, y) of observed positions; returns new labels
    (`home_gk` / `away_gk`) for the goalkeeper tracks.
    """
    by_track: dict[int, list[tuple[int, float, float]]] = defaultdict(list)
    for t, tid, x, y in points:
        by_track[tid].append((t, x, y))
    keepers: dict[int, str] = {}  # track -> goal side "left" | "right"
    for tid, ps in by_track.items():
        if teams.get(tid) == "referee" or ps[-1][0] - ps[0][0] < min_track_ms:
            continue
        left = sum(math.hypot(x, y - 10) < 6.5 for _, x, y in ps) / len(ps)
        right = sum(math.hypot(40 - x, y - 10) < 6.5 for _, x, y in ps) / len(ps)
        if max(left, right) >= area_share:
            keepers[tid] = "left" if left > right else "right"
    if not keepers:
        return {}
    # defending team per time bin and goal
    groups: dict[int, dict[str, list[tuple[float, float]]]] = defaultdict(lambda: defaultdict(list))
    for t, tid, x, y in points:
        lbl = teams.get(tid)
        if lbl in ("home", "away") and tid not in keepers:
            groups[t // bin_ms][lbl].append((x, y))
    votes: list[tuple[int, str, str]] = []  # (bin, side, defending team)
    for b, g in groups.items():
        for side, gx in (("left", 0.0), ("right", 40.0)):
            near = {
                team: sorted(
                    math.hypot(x - gx, y - 10) for x, y in ps if (x < 20) == (side == "left")
                )
                for team, ps in g.items()
            }
            if len(near.get("home", [])) >= 2 and len(near.get("away", [])) >= 2:
                med = {team: d[len(d) // 2] for team, d in near.items()}
                if abs(med["home"] - med["away"]) > 1.0:
                    votes.append((b, side, min(med, key=med.__getitem__)))
    out: dict[int, str] = {}
    for tid, side in keepers.items():
        t0, t1 = by_track[tid][0][0] // bin_ms, by_track[tid][-1][0] // bin_ms
        tally: dict[str, int] = defaultdict(int)
        for b, s, team in votes:
            if t0 <= b <= t1 and s == side:
                tally[team] += 1
        if tally and max(tally.values()) >= 3:
            out[tid] = f"{max(tally, key=tally.__getitem__)}_gk"
    return out
