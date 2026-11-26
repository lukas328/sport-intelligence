"""Wurfzeit der Kandidaten auf Dev (2026-11-25): features per segment for choosing a release-time
method on the dev segments only.

Usage:
  uv run --project packages/vision python ml/integration/shot_time_dev.py extract OBS LABELS OUT.pkl
  uv run --project packages/vision python ml/integration/shot_time_dev.py eval OUT.pkl [MARKS.json]

OBS: observe outputs of the dev segments (Kaggle kernels handball-shot-dev-0..4, one folder per
segment with motion.npz and observations.npz). LABELS: ml/data/segment_labels (official log
entries, the time a shot was written down, a few seconds after the release). MARKS (optional):
release marks on the dev segments {"shots": [{"seg", "t_s", "kind"}]} in the format of
ml/gold/data/shot_endtest_marks.json; without them the log time is the reference.

The end test (ml/gold/data/shot_endtest_*) is never read here.
"""

from __future__ import annotations

import json
import pickle
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ml/goals"))
import shot_eval as se  # noqa: E402

from handball_vision import goalcandidates as gc  # noqa: E402
from handball_vision import observe as ob  # noqa: E402
from handball_vision.ballpossession import ball_path_v2  # noqa: E402
from handball_vision.motion import CameraMotion  # noqa: E402

ENDTEST = ROOT / "ml/gold/shot_endtest_segments.json"


def endtest_games() -> set[str]:
    d = json.loads(ENDTEST.read_text())
    items = d["segments"] if isinstance(d, dict) else d
    return {s["game"] if isinstance(s, dict) else str(s) for s in items}


def extract(obs_dir: Path, label_dir: Path, dst: Path) -> None:
    segs = se.load_segments(label_dir)
    banned = endtest_games()
    tmpl = gc.load_template()
    out: dict[str, Any] = {}
    for d in sorted(obs_dir.iterdir()):
        info = segs.get(d.name)
        if info is None or info["game"] in banned:
            continue
        obs = ob.load_observations(d / "observations.npz", CameraMotion.load(d / "motion.npz"))
        cam_t, cam_x, pt, px, py, ph, duration = gc.inputs_from_observations(obs)
        s = gc.signals(cam_t, cam_x, pt, px, py, ph, duration)
        idle = gc.no_play(s, bool(obs.motion.moving))
        model = gc.load_shot_model()
        sscore = gc.shot_score(s, model, tmpl)
        found = gc.pick(s["t"], sscore, rates=gc.SHOT_RATES, play=~idle)
        fps = obs.fps
        first, path, conf = ball_path_v2(obs, obs.ball_cands) if obs.ball_cands else (0, [], [])
        bt, bxy, bw, bc = [], [], [], []
        for k, q in enumerate(path):
            if q is None:
                continue
            f = first + k
            h = obs.motion.frame_to_canvas(f)
            if h is None:
                continue
            p = np.asarray(h, float) @ np.array([q[0], q[1], 1.0])
            w = gc._canvas_to_reference(obs.motion, (p[:2] / p[2])[None, :])
            bt.append(f / fps)
            bxy.append((float(q[0]), float(q[1])))
            bw.append((float(w[0, 0]), float(w[0, 1])))
            bc.append(float(conf[k]) if k < len(conf) and conf[k] is not None else np.nan)
        out[d.name] = {
            "game": info["game"],
            "entries": info["entries"],
            "duration": duration,
            "fps": fps,
            "frame_w": float(obs.motion.frame_size[0]),
            "t": s["t"],
            "signals": {k: v for k, v in s.items() if k != "t"},
            "idle": idle,
            "shot_score": sscore,
            "cands": [{"t": c.t, "rate": c.rate, "score": c.score} for c in found],
            "cam_t": cam_t,
            "cam_x": cam_x,
            "ball_t": np.array(bt),
            "ball_xy": np.array(bxy).reshape(-1, 2),
            "ball_w": np.array(bw).reshape(-1, 2),
            "ball_conf": np.array(bc),
        }
        print(d.name, len(found), len(bt), flush=True)
    dst.write_bytes(pickle.dumps(out))


# --- methods: estimated release time of a candidate ----------------------------------------------

HIT = (-3.0, 8.0)  # candidate peak minus shot, the window in which a candidate counts as the shot
RATE = 4


def _ball_speed(v: dict[str, Any]) -> tuple[np.ndarray, np.ndarray] | None:
    """Ball speed in image px/s (1280 px frame) on a 10 Hz grid, NaN where the path has no point."""
    if "_speed" in v:
        return v["_speed"]
    t, p = v["ball_t"], v["ball_xy"] * (1280.0 / v["frame_w"])
    out = None
    if len(t) >= 10:
        g = np.arange(0, v["duration"], 0.1)
        idx = np.clip(np.searchsorted(t, g), 0, len(t) - 1)
        ok = np.abs(t[idx] - g) < 0.15
        x = np.where(ok, p[idx, 0], np.nan)
        y = np.where(ok, p[idx, 1], np.nan)
        out = (g, np.hypot(np.gradient(x, 0.1), np.gradient(y, 0.1)))
    v["_speed"] = out
    return out


def ball_anchor(v: dict[str, Any], peak: float, pct: float = 90.0) -> float | None:
    """Last 10 Hz step 6 s to 0.5 s before the peak where the ball moves faster than the
    segment's `pct` percentile: the last fast ball before play turns round."""
    r = _ball_speed(v)
    if r is None:
        return None
    g, sp = r
    m = (g >= peak - 6.0) & (g <= peak - 0.5)
    q = np.nanpercentile(sp, pct)
    hi = np.where(np.nan_to_num(sp[m]) > q)[0]
    return float(g[m][hi[-1]]) if len(hi) else None


METHODS = {
    "peak": lambda v, p: p,
    "ball90": lambda v, p: ball_anchor(v, p, 90.0),
    "ball98": lambda v, p: ball_anchor(v, p, 98.0),
}


def shots_of(feats: dict[str, Any], marks: dict[str, list[tuple[float, str]]] | None) -> list[dict]:
    """Reference shots: release marks where given, else the official log times."""
    out = []
    for seg, v in feats.items():
        if marks is not None:
            refs = marks.get(seg, [])
        else:
            refs = [(e["t"], e["kind"]) for e in v["entries"] if e["kind"] in se.SHOT]
        for t, kind in refs:
            out.append({"seg": seg, "game": v["game"], "t": t, "kind": kind})
    return out


def evaluate(feats: dict[str, Any], marks: dict | None, boot: int = 2000) -> dict[str, Any]:
    """For each method: estimated time = method(candidate) minus an offset learned
    leave-one-game-out (median of estimate minus reference over the other games' shots).
    A shot counts within 2 s when a candidate (rate <= 4) in the -3/+8 s window has its
    estimate within 2 s; the same measure as the end test."""
    shots = shots_of(feats, marks)
    games = sorted({s["game"] for s in shots})
    res: dict[str, Any] = {
        "shots": len(shots),
        "games": len(games),
        "reference": "release marks" if marks is not None else "log time",
    }
    for name, fn in METHODS.items():
        raw = []  # per shot: list of (method time - ref) over candidates in the window
        for s in shots:
            v = feats[s["seg"]]
            ds = []
            for c in v["cands"]:
                if c["rate"] > RATE or not HIT[0] <= c["t"] - s["t"] <= HIT[1]:
                    continue
                m = fn(v, c["t"])
                if m is not None:
                    ds.append(m - s["t"])
            raw.append(ds)
        within, offs = [], {}
        for g in games:
            pool = [
                min(ds, key=abs) for s, ds in zip(shots, raw, strict=True) if s["game"] != g and ds
            ]
            offs[g] = float(np.median(pool)) if pool else 0.0
        for s, ds in zip(shots, raw, strict=True):
            o = offs[s["game"]]
            within.append(any(abs(d - o) <= 2.0 for d in ds))
        w = np.array(within, float)
        gi = np.array([games.index(s["game"]) for s in shots])
        rng = np.random.default_rng(0)
        bs = []
        for _ in range(boot):
            pick = rng.integers(0, len(games), len(games))
            idx = np.concatenate([np.where(gi == k)[0] for k in pick])
            bs.append(w[idx].mean())
        found = np.array([bool(ds) for ds in raw], float)
        res[name] = {
            "within_2s": round(float(w.mean()), 3),
            "ci95": [round(float(x), 3) for x in np.percentile(bs, [2.5, 97.5])],
            "found_-3_+8": round(float(found.mean()), 3),
            "offset_median_s": round(float(np.median(list(offs.values()))), 2),
        }
    return res


def load_marks(path: Path) -> dict[str, list[tuple[float, str]]]:
    d = json.loads(path.read_text())
    out: dict[str, list[tuple[float, str]]] = {}
    for s in d["shots"]:
        if s.get("t_s") is None or s.get("status", "ok") != "ok":
            continue  # unsure or not visible: left out of the method choice
        out.setdefault(s["seg"], []).append((float(s["t_s"]), s.get("kind", "")))
    return out


if __name__ == "__main__":
    if sys.argv[1] == "extract":
        extract(Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]))
    elif sys.argv[1] == "eval":
        D = pickle.loads(Path(sys.argv[2]).read_bytes())  # noqa: S301 (own file from extract)
        mk = load_marks(Path(sys.argv[3])) if len(sys.argv) > 3 else None
        print(json.dumps(evaluate(D, mk), indent=1))
