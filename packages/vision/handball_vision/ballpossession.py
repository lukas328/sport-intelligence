"""Who has the ball, from the ball path and the player boxes (BRIEF 7.2 stage 7, player level).

The ball path (`balltrack`) is in frame pixels; a player holds the ball when it is inside the
player's box (widened a little, and raised for a ball held overhead). The court position of a ball
in the air cannot be taken from the floor homography, but the holder's feet can: possession
places the ball on the court.

From the holder per frame:
- **possessions**: one player holding for at least `min_hold_s` (bouncing and short occlusions
  are bridged by `max_gap_s`);
- **passes**: the ball goes from one player to a team-mate within `max_flight_s`;
- **turnovers**: it goes to an opponent (interception, steal, or a lost ball picked up).

Passes and turnovers are only reported between possessions that are both certain; a ball that
disappears for longer is a "lost" end, not a pass.
"""

from __future__ import annotations

import itertools
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

Box = tuple[int, float, float, float, float]  # track id, x1, y1, x2, y2 (frame pixels)


@dataclass(frozen=True)
class Possession:
    track_id: int
    team: str | None
    first: int  # frame
    last: int


@dataclass(frozen=True)
class Transfer:
    kind: str  # "pass" or "turnover"
    from_track: int
    to_track: int
    from_team: str | None
    to_team: str | None
    released: int  # frame the ball left the passer
    received: int  # frame the receiver had it


def holder(ball: tuple[float, float], boxes: Sequence[Box], margin: float = 0.15) -> int | None:
    """The track holding a ball at `ball`: the box containing it (widened by `margin` of its width
    on each side, raised by 20 % of its height for arms overhead). Several boxes: the one whose
    upper-body centre is nearest (the ball is held in hands, not at the feet)."""
    bx, by = ball
    best, best_d = None, float("inf")
    for tid, x1, y1, x2, y2 in boxes:
        w, h = x2 - x1, y2 - y1
        if not (x1 - margin * w <= bx <= x2 + margin * w and y1 - 0.2 * h <= by <= y2):
            continue
        cx, cy = (x1 + x2) / 2, y1 + 0.35 * h
        d = ((bx - cx) / max(w, 1.0)) ** 2 + ((by - cy) / max(h, 1.0)) ** 2
        if d < best_d:
            best, best_d = tid, d
    return best


def holders(
    ball: Mapping[int, tuple[float, float]], boxes: Mapping[int, Sequence[Box]]
) -> dict[int, int | None]:
    """Holder per frame with a ball position and boxes (None: ball free or in flight)."""
    return {f: holder(xy, boxes[f]) for f, xy in sorted(ball.items()) if f in boxes}


def possessions(
    by_frame: Mapping[int, int | None],
    teams: Mapping[int, str],
    fps: float,
    min_hold_s: float = 0.3,
    max_gap_s: float = 0.5,
) -> list[Possession]:
    """Runs of the same holder, short gaps bridged, too short runs dropped."""
    runs: list[list[int]] = []  # [track, first, last]
    gap = round(max_gap_s * fps)
    for f in sorted(by_frame):
        tid = by_frame[f]
        if tid is None:
            continue
        if runs and runs[-1][0] == tid and f - runs[-1][2] <= gap:
            runs[-1][2] = f
        else:
            runs.append([tid, f, f])
    need = min_hold_s * fps
    out = [Possession(t, teams.get(t), a, b) for t, a, b in runs if b - a + 1 >= need]
    # a short foreign run between two of the same holder (a crossing player) disappears above;
    # merge what is now adjacent
    merged: list[Possession] = []
    for p in out:
        if merged and merged[-1].track_id == p.track_id and p.first - merged[-1].last <= 3 * gap:
            merged[-1] = Possession(p.track_id, p.team, merged[-1].first, p.last)
        else:
            merged.append(p)
    return merged


def transfers(pos: Sequence[Possession], fps: float, max_flight_s: float = 2.5) -> list[Transfer]:
    """Passes and turnovers between consecutive possessions of different players."""
    out = []
    for a, b in itertools.pairwise(pos):
        if a.track_id == b.track_id or (b.first - a.last) / fps > max_flight_s:
            continue
        same = a.team is not None and a.team.removesuffix("_gk") == (b.team or "").removesuffix(
            "_gk"
        )
        out.append(
            Transfer(
                "pass" if same else "turnover",
                a.track_id,
                b.track_id,
                a.team,
                b.team,
                a.last,
                b.first,
            )
        )
    return out


def summary(pos: Sequence[Possession], moves: Sequence[Transfer], fps: float) -> dict[str, object]:
    """Ball time per team and player, passes and turnovers per team."""
    team_s: dict[str, float] = {}
    player_s: dict[int, float] = {}
    for p in pos:
        dur = (p.last - p.first + 1) / fps
        if p.team:
            key = p.team.removesuffix("_gk")
            team_s[key] = team_s.get(key, 0.0) + dur
        player_s[p.track_id] = player_s.get(p.track_id, 0.0) + dur
    passes: dict[str, int] = {}
    turnovers: dict[str, int] = {}
    for m in moves:
        key = (m.from_team or "unknown").removesuffix("_gk")
        bucket = passes if m.kind == "pass" else turnovers
        bucket[key] = bucket.get(key, 0) + 1
    return {
        "ball_time_s": {k: round(v, 1) for k, v in team_s.items()},
        "player_ball_time_s": {k: round(v, 1) for k, v in player_s.items()},
        "passes": passes,
        "turnovers": turnovers,
        "possessions": len(pos),
    }
