"""Per-candidate features on the 49 dev segments without calibration: people foot points on the
camera canvas (2 Hz, reference px), team of each person from its torso colour (learned kits),
court ends from the spread of the foot points. Writes one pickle with candidates and features."""

import pickle
import sys
from pathlib import Path

import numpy as np

from handball_vision import goalcandidates as gcm
from handball_vision import observe as ob
from handball_vision.motion import CameraMotion
from handball_vision.teams import learn_kits, side_of

OBS = Path(sys.argv[1])
OUT = Path(sys.argv[2])
WIN = {
    "pre2": (-10, -6),
    "pre1": (-6, -2),
    "peak": (-2, 2),
    "post1": (2, 10),
    "post2": (10, 20),
    "post3": (20, 35),
}


def people(obs):
    fps = float(obs.fps) or 25.0
    motion = obs.motion
    rows = []
    next_t = 0.0
    for fo in obs.frames:
        t = fo.index / fps
        if t < next_t - 0.5 / fps or not fo.people:
            continue
        next_t = max(next_t + 0.5, t + 0.25)
        h = motion.frame_to_canvas(fo.index)
        if h is None:
            continue
        b = np.array([(d.x1, d.y1, d.x2, d.y2) for d in fo.people], float)
        cx = (b[:, 0] + b[:, 2]) / 2
        p = np.column_stack([cx, b[:, 3], np.ones(len(b))]) @ np.asarray(h, float).T
        p = gcm._canvas_to_reference(motion, p[:, :2] / p[:, 2:3])
        for k in range(len(b)):
            col = ob._torso_colour(fo.torsos[k], None) if fo.torsos and k < len(fo.torsos) else None
            rows.append((t, p[k, 0], p[k, 1], col))
    return rows


def seg_feats(seg):
    mot = CameraMotion.load(OBS / seg / "motion.npz")
    obs = ob.load_observations(OBS / seg / "observations.npz", mot)
    gc = gcm.from_observations(obs, play=None)
    if not gc:
        return None
    rows = people(obs)
    t = np.array([r[0] for r in rows])
    x = np.array([r[1] for r in rows])
    np.array([r[2] for r in rows])
    looks = [r[3] for r in rows[::3] if r[3] is not None]
    kits = learn_kits(looks, {})
    cent = {k: v for k, v in kits.items() if k in ("home", "away")}
    team = np.array(
        [
            0 if r[3] is None else {"home": 1, "away": -1}.get(side_of(r[3], cent) or "", 0)
            for r in rows
        ]
    )
    lo, hi = np.percentile(x, 3), np.percentile(x, 97)
    u = (x - lo) / max(1e-6, hi - lo)
    out = []
    for kind, cands in (("goal", gc["candidates"]), ("shot", gc["shots"]["candidates"])):
        for c in cands:
            pk = c["t_ms"] / 1000
            f = {"seg": seg, "kind": kind, "peak": pk, "score": c["score"], "rate": c["rate"]}
            # attacked end before the peak: the end with more people within 25 % of it
            m = (t >= pk - 6) & (t < pk - 1)
            left = int(((u < 0.25) & m).sum())
            right = int(((u > 0.75) & m).sum())
            end = 0.0 if left >= right else 1.0
            d_end = np.abs(u - end)  # distance to the attacked end (court lengths)
            for w, (a, b) in WIN.items():
                mm = (t >= pk + a) & (t < pk + b)
                n = max(1, int(mm.sum()) // max(1, int((b - a) * 2)))  # people per sample
                f[f"{w}_n"] = n
                f[f"{w}_near_end"] = float(((d_end < 0.2) & mm).sum()) / max(1, mm.sum())
                f[f"{w}_centre"] = float(((np.abs(u - 0.5) < 0.15) & mm).sum()) / max(1, mm.sum())
                f[f"{w}_mean_u_to_end"] = float(d_end[mm].mean()) if mm.any() else 0.5
                f[f"{w}_spread"] = float(u[mm].std()) if mm.sum() > 2 else 0.0
                h_ = mm & (team == 1)
                a_ = mm & (team == -1)
                if h_.sum() > 2 and a_.sum() > 2:
                    f[f"{w}_team_gap"] = float(abs(u[h_].mean() - u[a_].mean()))
                    # teams on opposite halves (throw-off formation)
                    hs = np.mean(u[h_] < 0.5)
                    as_ = np.mean(u[a_] < 0.5)
                    f[f"{w}_halves"] = float(abs(hs - as_))
                else:
                    f[f"{w}_team_gap"] = 0.0
                    f[f"{w}_halves"] = 0.0
            # play turns to the other end after the peak (save, miss: counter; goal: centre first)
            mm = (t >= pk + 4) & (t < pk + 14)
            f["turn"] = float(((np.abs(u - (1 - end)) < 0.25) & mm).sum()) / max(1, mm.sum())
            out.append(f)
    return {"seg": seg, "dur": gc["duration_s"], "cands": out}


segs = sorted(p.name for p in OBS.iterdir() if (p / "observations.npz").exists())
part = [s for k, s in enumerate(segs) if k % int(sys.argv[4]) == int(sys.argv[3])]
res = []
for s in part:
    r = seg_feats(s)
    if r:
        res.append(r)
    print(s, len(r["cands"]) if r else None, flush=True)
with OUT.open("wb") as fh:
    pickle.dump(res, fh)
