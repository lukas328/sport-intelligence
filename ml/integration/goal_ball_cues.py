"""A1 (2026-11-20): ball cues for goal candidates on the dev segments (features per candidate).
Usage: uv run --project packages/vision python ml/integration/goal_ball_cues.py OUT MARKS.json ROWS.json SEGMENTS.json
OUT: observe outputs (kernels handball-shot-dev-0..4); MARKS: {segment: [[t_s, kind], ...]} from
ml/data/segment_labels; evaluation: goal_ball_cues_eval.py ROWS.json."""
import json, sys
from pathlib import Path
import numpy as np
from handball_vision import goalcandidates as gc, observe as ob
from handball_vision.ballpossession import ball_path_v2
from handball_vision.motion import CameraMotion

out = Path(sys.argv[1]); marks = json.load(open(sys.argv[2])); dst = Path(sys.argv[3])
segs = json.load(open(sys.argv[4]))
game_of = {s["file"][:-4]: s["game"] for s in segs}
rows = []
for d in sorted(out.iterdir()):
    obs = ob.load_observations(d / "observations.npz", CameraMotion.load(d / "motion.npz"))
    res = gc.from_observations(obs)
    goals = [t for t, k in marks.get(d.name, []) if k in ("goal", "penalty_goal", "empty_goal")]
    fps = obs.fps
    # ball in world azimuth (reference px on the camera cylinder), per frame
    first, path, conf = ball_path_v2(obs, obs.ball_cands) if obs.ball_cands else (0, [], [])
    bt, bx = [], []
    for k, q in enumerate(path):
        if q is None: continue
        f = first + k
        h = obs.motion.frame_to_canvas(f)
        if h is None: continue
        p = np.asarray(h, float) @ np.array([q[0], q[1], 1.0])
        w = gc._canvas_to_reference(obs.motion, (p[:2] / p[2])[None, :])
        bt.append(f / fps); bx.append(w[0, 0])
    bt, bx = np.array(bt), np.array(bx)
    if len(bx) > 50:
        lo, hi = np.percentile(bx, [3, 97]); center, half = (lo + hi) / 2, max((hi - lo) / 2, 1.0)
    else:
        center, half = 0.0, 1.0
    # 10 Hz grid of ball position (NaN where none) and speed
    grid = np.arange(0, obs.total / fps, 0.1)
    bg = np.full(len(grid), np.nan)
    if len(bt):
        idx = np.clip(np.searchsorted(bt, grid), 0, len(bt) - 1)
        near = np.abs(bt[idx] - grid) < 0.15
        bg[near] = bx[idx[near]]
    rel = (bg - center) / half                      # -1 .. 1 goal to goal
    spd = np.abs(np.gradient(bg, 0.1)) / half       # half-courts per second
    def win(a, b, p):
        i, j = np.searchsorted(grid, p + a), np.searchsorted(grid, p + b)
        return slice(i, max(i, j))
    def runlen(mask):
        best = cur = 0
        for m in mask:
            cur = cur + 1 if m else 0; best = max(best, cur)
        return best * 0.1
    for c in res["candidates"]:
        p = c["t_ms"] / 1000
        pre, post = win(-6, 0, p), win(2, 25, p)
        sp = spd[pre]; sp = sp[np.isfinite(sp)]
        r_post, s_post = rel[post], spd[post]
        center_still = np.isfinite(r_post) & (np.abs(r_post) < 0.2) & (np.nan_to_num(s_post, nan=9) < 0.15)
        rp = rel[win(-4, 0, p)]; rp = rp[np.isfinite(rp)]
        rows.append({
            "seg": d.name, "game": game_of.get(d.name, d.name), "t": p, "rate": c["rate"],
            "rank": c.get("rank"), "score": c["score"],
            "tp": any(-3 <= p - g <= 8 for g in goals),
            "goal": next((g for g in goals if -3 <= p - g <= 8), None),
            "ball_speed_pre": float(np.percentile(sp, 95)) if len(sp) > 5 else np.nan,
            "end_pre": float(np.max(np.abs(rp))) if len(rp) else np.nan,
            "center_still_post": runlen(center_still),
            "center_any_post": float(np.mean(np.abs(r_post[np.isfinite(r_post)]) < 0.2)) if np.isfinite(r_post).sum() > 10 else np.nan,
        })
    rows.append({"seg": d.name, "game": game_of.get(d.name, d.name), "meta": True,
                 "goals": goals, "play_s": res["play_s"]})
dst.write_text(json.dumps(rows))
print(len(rows))
