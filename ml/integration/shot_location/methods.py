# ruff: noqa: S301, SIM115, PTH123
"""Shot location: today's nearest attacker vs the ball path release (pre-registered, written
before the labels were seen). Run: python methods.py -> writes out_<h>/pred.json for truth shots
given in truth.json (release_t, team). Parameters fixed here."""

import itertools
import math
import pickle
from pathlib import Path

import numpy as np

from handball_vision import observe as learned
from handball_vision.ballpossession import holder
from handball_vision.motion import CameraMotion

G_OFFSET_S = 1.5  # a coach marks the goal about this long after the release
WINDOW_S = 10.0  # today's rule: the 10 s before the goal
SEARCH_S = 5.0  # ball path: look for the release in the 5 s before the goal
FAST_MS = 8.0  # floor-projected ball speed of a shot (m/s)
MIN_RUN = 2  # consecutive fast steps towards the goal
COS_MIN = 0.6
HOLD_BACK_S = 0.6  # look back this far for the holder
LENGTH, WIDTH = 40.0, 20.0


def goal_distance(x, y, gx):
    return math.hypot(x - gx, y - min(max(y, 8.5), 11.5))


class Clip:
    def __init__(self, out: Path):
        d = pickle.load(open(out / "trk.pkl", "rb"))
        self.fps = d["fps"]
        self.H = np.array(d["H"])
        self.motion = CameraMotion.load(out / "motion.npz")
        self.obs = learned.load_observations(out / "observations.npz", self.motion)
        self.label = {tid: v.get("label") for tid, v in d["teams"].items()}
        self.points = d["points"]
        first, path, _conf = d["ball"]
        self.ball = {first + k: q for k, q in enumerate(path) if q is not None}
        self.det_frames = {fo.index: fo for fo in self.obs.frames}
        self.det_idx = np.array(sorted(self.det_frames))

    def court_to_frame(self, f):
        m = self.motion.frame_to_canvas(f)
        return None if m is None else np.linalg.inv(m) @ self.H

    def to_court(self, f, px):
        h = self.court_to_frame(f)
        if h is None:
            return None
        v = np.linalg.inv(h) @ np.array([px[0], px[1], 1.0])
        return (float(v[0] / v[2]), float(v[1] / v[2])) if abs(v[2]) > 1e-9 else None

    def today(self, g_ms, team):
        f0, f1 = (g_ms - WINDOW_S * 1000) * self.fps / 1000, g_ms * self.fps / 1000
        att = [p for p in self.points if f0 <= p[0] <= f1 and p[5] and self.label.get(p[1]) == team]
        if not att:
            return None, None
        gx = LENGTH if np.mean([p[2] for p in att]) > LENGTH / 2 else 0.0
        best = min(att, key=lambda p: goal_distance(p[2], p[3], gx))
        return (best[2], best[3]), gx

    def ball_release(self, g_ms, gx):
        f1 = int(g_ms * self.fps / 1000)
        f0 = int(f1 - SEARCH_S * self.fps)
        # the net points (not the in-between fill): frames the net ran on
        fr = [f for f in range(f0, f1 + 1) if f in self.ball and f in self.obs.ball_cands]
        pts = [(f, self.to_court(f, self.ball[f])) for f in fr]
        pts = [(f, c) for f, c in pts if c is not None]
        best = None
        run = 0
        for (fa, a), (fb, b) in itertools.pairwise(pts):
            dt = (fb - fa) / self.fps
            vx, vy = (b[0] - a[0]) / dt, (b[1] - a[1]) / dt
            sp = math.hypot(vx, vy)
            tx, ty = gx - a[0], 10.0 - a[1]
            cos = (vx * tx + vy * ty) / (sp * math.hypot(tx, ty) + 1e-9)
            if sp >= FAST_MS and cos >= COS_MIN and dt <= 0.25:
                run += 1
                if run == 1:
                    start = fa
                if run >= MIN_RUN:
                    best = start
            else:
                run = 0
        return best

    def thrower(self, f):
        """The person holding the ball at the release, else at the last frame with a holder in
        the HOLD_BACK_S before it (the first fast step can start just after the ball left)."""
        if f is None:
            return None
        for k in self.det_idx[(self.det_idx <= f) & (self.det_idx >= f - HOLD_BACK_S * self.fps)][
            ::-1
        ]:
            fo = self.det_frames[int(k)]
            bx = self.ball.get(int(k))
            if bx is None:
                continue
            i = holder(bx, [(j, d.x1, d.y1, d.x2, d.y2) for j, d in enumerate(fo.people)])
            if i is not None:
                d = fo.people[i]
                return self.to_court(int(k), ((d.x1 + d.x2) / 2, d.y2))
        return None


def norm(p, gx):
    if p is None:
        return None
    return (p[0], p[1]) if gx == LENGTH else (LENGTH - p[0], WIDTH - p[1])


def predict(clip, release_t, team, offset=G_OFFSET_S):
    g_ms = (release_t + offset) * 1000
    t, gx = clip.today(g_ms, team)
    if gx is None:
        return {"today": None, "ball": None, "ball_or_today": None, "gx": None}
    rel = clip.ball_release(g_ms, gx)
    b = clip.thrower(rel)
    return {
        "today": norm(t, gx),
        "ball": norm(b, gx),
        "ball_or_today": norm(b if b else t, gx),
        "gx": gx,
        "ball_release_t": None if rel is None else rel / clip.fps,
    }
