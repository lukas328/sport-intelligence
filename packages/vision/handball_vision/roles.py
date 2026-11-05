"""Player, goalkeeper or referee, from appearance (BRIEF 7.2 stage 4, complements the kit colours).

The kit colours entered for a match are often missing or wrong (goalkeepers, referees). A classifier
on person crops (`RoleClassifier`, ONNX: N x 3 x 128 x 64 RGB in 0..255, softmax over player,
goalkeeper, referee) looks at each person now and then; per track the probabilities are averaged.
On its own it confuses players in dark kits with referees, so the decision also uses what the
tracks know:

- **referee**: the track looks like a referee (averaged over the track), its kit colour is not the
  same as a team's, and at most two referee tracks are on court at the same time (the most certain
  win). This also overrules the goal-line position rule: referees stand at the goal line too;
- **not a referee**: a track the kit colours called referee but the classifier clearly rejects goes
  back to the nearest team (or to goalkeeper when it looks like one and stays at a goal);
- **goalkeeper**: the track looks like a goalkeeper and stays near one goal most of the time; the
  team comes from the existing position logic (`events.assign_goalkeepers`) when it is a long
  track, else from the defending team near that goal.
"""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from numpy.typing import NDArray

F64 = NDArray[np.float64]
ROLES = ("player", "goalkeeper", "referee")
MIN_BOX_HEIGHT = 40


class RoleClassifier:
    def __init__(self, model: Path, threads: int | None = None) -> None:
        import onnxruntime as ort

        opts = ort.SessionOptions()
        if threads:
            opts.intra_op_num_threads = threads
        providers = [
            p
            for p in ("CUDAExecutionProvider", "CPUExecutionProvider")
            if p in ort.get_available_providers()
        ]
        self.session = ort.InferenceSession(str(model), opts, providers=providers)
        self.input = self.session.get_inputs()[0].name

    def classify(
        self, frame: NDArray[Any], boxes: Sequence[tuple[float, float, float, float]]
    ) -> list[F64 | None]:
        """Role probabilities per box (None for boxes too small to judge)."""
        crops, keep = [], []
        h, w = frame.shape[:2]
        for k, (x1, y1, x2, y2) in enumerate(boxes):
            if y2 - y1 < MIN_BOX_HEIGHT:
                continue
            mx, my = 0.1 * (x2 - x1), 0.1 * (y2 - y1)
            c = frame[
                max(0, int(y1 - my)) : min(h, int(y2 + my)),
                max(0, int(x1 - mx)) : min(w, int(x2 + mx)),
            ]
            if c.size == 0:
                continue
            crops.append(cv2.resize(cv2.cvtColor(c, cv2.COLOR_BGR2RGB), (64, 128)))
            keep.append(k)
        out: list[F64 | None] = [None] * len(boxes)
        if not crops:
            return out
        x = np.stack(crops).transpose(0, 3, 1, 2).astype(np.float32)
        probs = self.session.run(None, {self.input: x})[0]
        for k, p in zip(keep, probs, strict=True):
            out[k] = np.asarray(p, np.float64)
        return out


def track_roles(samples: Mapping[int, Sequence[F64]], min_samples: int = 4) -> dict[int, F64]:
    """Mean role probabilities per track with enough looks."""
    return {
        t: np.mean(np.stack(list(v)), axis=0) for t, v in samples.items() if len(v) >= min_samples
    }


def _lab_distance(a: Sequence[float] | F64, b: Sequence[float] | F64) -> float:
    return float(np.linalg.norm(np.asarray(a, np.float64) - np.asarray(b, np.float64)))


def apply_roles(
    team_out: dict[int, dict[str, Any]],
    roles: Mapping[int, F64],
    spans: Mapping[int, tuple[int, int]],
    near_goal: Mapping[int, float],
    goal_team: Mapping[int, str],
    referee_p: float = 0.7,
    goalkeeper_p: float = 0.6,
    colour_gap: float = 8.0,
    near_goal_share: float = 0.5,
    not_referee_p: float = 0.15,
) -> dict[int, str]:
    """New labels from the role votes. `spans` are first/last frames per track, `near_goal` the share
    of its time within 9 m of a goal, `goal_team` the team defending that goal for the track (when
    known). Returns track -> label for the tracks that change."""
    centres: dict[str, list[list[float]]] = defaultdict(list)
    for v in team_out.values():
        if v.get("label") in ("home", "away") and "lab" in v:
            centres[str(v["label"])].append(list(v["lab"]))
    team_lab = {k: np.median(np.asarray(v), axis=0) for k, v in centres.items() if len(v) >= 2}
    changes: dict[int, str] = {}
    # referees: most certain first, at most two at a time, colour unlike both teams
    cands = sorted(
        (float(p[2]), t)
        for t, p in roles.items()
        if t in team_out and p[2] >= referee_p and p[2] == max(p)
    )
    chosen: list[int] = []
    for _, t in reversed(cands):
        lab = team_out[t].get("lab")
        if lab is not None and any(_lab_distance(lab, c) < colour_gap for c in team_lab.values()):
            continue
        a0, a1 = spans.get(t, (0, 0))
        overlapping = sum(
            1 for o in chosen if min(a1, spans[o][1]) - max(a0, spans[o][0]) > 0 and o in spans
        )
        if overlapping >= 2:
            continue
        chosen.append(t)
        if team_out[t].get("label") != "referee":
            changes[t] = "referee"
    # goalkeepers the position rule missed (short tracks): looks like one and stays at a goal
    for t, p in roles.items():
        if t in changes or t not in team_out or str(team_out[t].get("label", "")).endswith("_gk"):
            continue
        if p[1] >= goalkeeper_p and p[1] == max(p) and near_goal.get(t, 0.0) >= near_goal_share:
            team = goal_team.get(t)
            if team in ("home", "away"):
                changes[t] = f"{team}_gk"
    # 'referee' from the kit colour alone, but clearly not one to the classifier: back to a team
    for t, p in roles.items():
        if t in changes or team_out.get(t, {}).get("label") != "referee" or t in chosen:
            continue
        if p[2] > not_referee_p:
            continue
        if p[1] >= goalkeeper_p and near_goal.get(t, 0.0) >= near_goal_share:
            team = goal_team.get(t)
            if team in ("home", "away"):
                changes[t] = f"{team}_gk"
                continue
        lab = team_out[t].get("lab")
        if lab is not None and team_lab:
            changes[t] = min(team_lab, key=lambda k: _lab_distance(lab, team_lab[k]))
    return changes


def goal_presence(
    points: Sequence[tuple[int, int, float, float]],
) -> tuple[dict[int, float], dict[int, str]]:
    """Per track: share of observed positions within 9 m of a goal, and which goal ("left"/"right")
    it stays at. Court coordinates in metres (40 x 20, goals at x = 0 and 40, y = 10)."""
    near: dict[int, list[str | None]] = defaultdict(list)
    for _, t, x, y in points:
        if math.hypot(x, y - 10) < 9:
            near[t].append("left")
        elif math.hypot(40 - x, y - 10) < 9:
            near[t].append("right")
        else:
            near[t].append(None)
    share = {t: sum(v is not None for v in vs) / len(vs) for t, vs in near.items() if vs}
    side = {}
    for t, vs in near.items():
        sides = [v for v in vs if v]
        if sides:
            side[t] = max(set(sides), key=sides.count)
    return share, side
