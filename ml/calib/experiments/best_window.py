"""Experiment (2026-11-17): calibrate on the window of K marking frames with the best floor fit.

    uv run --project packages/vision python ml/calib/experiments/best_window.py CACHE K ID [ID ...]

Result: docs/plans/kalibrierung.md section 5 (rejected: more wrong courts).
"""

# ruff: noqa
import sys, json
import numpy as np

sys.path.insert(0, "ml/calib")
sys.path.insert(0, "packages/vision")
import run
from handball_vision import observe as ob, topview
from handball_vision.calibration import CalibrationError

cache = __import__("pathlib").Path(sys.argv[1])
K = int(sys.argv[2])
out = []
for pid in sys.argv[3:]:
    obs, _ = run.load(cache, pid)
    m = obs.motion
    keys = sorted(obs.segments)
    static = obs.static if m.moving and m.stats.get("pan_deg", 0.0) >= 15 else None
    best = None
    for s in range(0, max(1, len(keys) - K + 1)):
        win = keys[s : s + K]
        ms, ls = [], []
        for idx in win:
            rot = ob._to_canvas_rot(m, idx)
            raw = obs.segments[idx]
            seg = ob.drop_static(raw, static) if static is not None else raw
            if rot is None or len(seg) == 0:
                continue
            a, b = topview.segment_normals(seg, ob._frame_k(m, idx), rot)
            ms.append(a)
            ls.append(b)
        try:
            fit = topview.orientation_from_normals(np.vstack(ms), np.concatenate(ls))[3]
        except (CalibrationError, ValueError):
            continue
        if best is None or fit > best[0]:
            best = (fit, win)
    obs.segments = {k: obs.segments[k] for k in best[1]}
    hall = m.background()
    r = {"id": pid, "moving": bool(m.moving), "window_fit": round(best[0], 3)}
    try:
        c, info = ob.auto_calibrate(obs, hall)
        maps = {}
        for f in sorted((cache / f"{pid}.frames").glob("*.jpg")):
            h = m.frame_to_canvas(int(f.stem))
            if h is not None:
                mm = c.inverse @ np.asarray(h)
                maps[str(int(f.stem))] = (mm / mm[2, 2]).tolist()
        r.update(ok=True, homography=c.homography.tolist(), info=info, frame_to_court=maps)
    except CalibrationError as e:
        r.update(ok=False, reason=e.reason)
    print(pid, r.get("window_fit"), "OK" if r["ok"] else r["reason"], flush=True)
    json.dump(r, open(f"{sys.argv[1]}/{pid}.win{K}.json", "w"))
