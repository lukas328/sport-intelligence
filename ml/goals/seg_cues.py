"""Goal-moment signals and cues over whole segments, from the cached heavy pass (`seg_extract.py`).

Everything lives on one 10 Hz grid over segment time. Coordinates are 1280-px image units; "canvas"
adds the accumulated camera pan, so a fixed camera's canvas is its image and a panning camera's
canvas is the hall as the camera swept it.

Signals (`signals`):
- `pan`: horizontal camera speed (px/s), `cam`: accumulated pan (canvas offset), `energy`:
  pan-compensated motion energy, `resp`: phase-correlation response;
- `flow_x`: mean residual horizontal flow of the moving pixels (camera removed, so it is their
  canvas velocity; image px/s): which way the players run; `flow_share`: share of moving pixels
  (activity); `flow_cx`: canvas x of the moving pixels' centroid;
- people (YOLOX at 2 Hz, interpolated): `cx` median canvas x of the people's feet, `spread` their
  10-90 % canvas x range, `n` count, `bal` balance of people left and right of the court centre
  (1 = half and half). Spectators and benches are dropped as "static": a detection whose canvas
  position is occupied in most detection frames of the surrounding 30 s;
- `p`: play position, `cx` scaled to -1..1 between the 3rd and 97th percentile of the segment
  (0 = middle of the court the camera covered, +-1 = the two ends).

Cues (`compute`, one value per grid step t, windows `BEFORE` back and `AFTER` ahead):
- `pan_rev`, `still_swing`, `pan_after`: as `cues.py` (camera follows the attack, turns round);
- `cen_rev`: the same with the people centroid's canvas velocity (fixed-camera replacement);
- `flow_rev`: the same with the moving pixels' mean residual flow;
- `play_rev`: the same with the mean of the three normalised velocities (pan, centroid, flow);
- `energy_drop`: motion energy before / after;
- `restart`: throw-off detector, see `restart_score`. It fires at the restart, 10-25 s after the
  goal; `restart_back` is the same series moved back by `RESTART_LAG` so it points at the goal.

usage (look at it): python ml/goals/seg_cues.py SEG.npz
"""

from __future__ import annotations

import sys
from typing import Any

import numpy as np

DT = 0.1
BEFORE, AFTER = 2.0, 2.0
RESTART_LAG = 14.0  # median throw-off start - goal (s), set from the labelled segments (seg_eval.py)


def _bin_mean(t: np.ndarray, x: np.ndarray, tg: np.ndarray) -> np.ndarray:
    """Mean of x per grid cell [tg, tg + DT); empty cells interpolated."""
    idx = np.floor(t / DT).astype(int)
    ok = (idx >= 0) & (idx < len(tg))
    s = np.bincount(idx[ok], weights=x[ok], minlength=len(tg))
    c = np.bincount(idx[ok], minlength=len(tg))
    have = c > 0
    out = np.zeros(len(tg))
    out[have] = s[have] / c[have]
    if have.sum() >= 2:
        out[~have] = np.interp(tg[~have], tg[have], out[have])
    return out


def smooth(x: np.ndarray, sec: float) -> np.ndarray:
    k = max(1, round(sec / DT))
    if k <= 1:
        return x
    w = np.hanning(k + 2)[1:-1]
    w /= w.sum()
    xp = np.pad(x, (k, k), mode="edge")
    return np.convolve(xp, w, mode="same")[k:-k]


def static_mask(pt: np.ndarray, px: np.ndarray, py: np.ndarray, win: float = 15.0,
                rx: float = 25.0, ry: float = 15.0, share: float = 0.6) -> np.ndarray:
    """True for detections at a canvas spot that is occupied in at least `share` of the detection
    frames within +-`win` s (benches, spectators, the officials' table)."""
    frames = np.unique(pt)
    out = np.zeros(len(pt), bool)
    for i in range(len(pt)):
        m = (np.abs(pt - pt[i]) <= win) & (np.abs(px - px[i]) <= rx) & (np.abs(py - py[i]) <= ry)
        nf = ((frames >= pt[i] - win) & (frames <= pt[i] + win)).sum()
        out[i] = len(np.unique(pt[m])) >= share * nf
    return out


def signals(z: Any) -> dict[str, np.ndarray]:
    t = z["t"].astype(float)
    T = float(t[-1])
    tg = np.arange(0, T, DT)
    dt = np.diff(t, prepend=t[0] - (t[1] - t[0]))
    pan_px = z["pan"][:, 0].astype(float)
    pan = smooth(_bin_mean(t, pan_px / np.maximum(dt, 1e-3), tg), 0.3)
    cam_frames = np.cumsum(pan_px)
    cam = np.interp(tg, t, cam_frames)
    energy = _bin_mean(t, z["energy"].astype(float), tg)
    resp = _bin_mean(t, z["resp"].astype(float), tg)
    ft = z["flow_t"].astype(float)
    cnt, fsum = z["flow_cnt"].astype(float), z["flow_sum"].astype(float)
    tot = cnt.sum(axis=1)
    centres = (np.arange(cnt.shape[1]) + 0.5) * 1280 / cnt.shape[1]
    fx = np.where(tot > 0, fsum.sum(axis=1) / np.maximum(tot, 1), 0.0) * 4 / 0.1  # 1280-px/s
    fcx = np.where(tot > 0, (cnt * centres).sum(axis=1) / np.maximum(tot, 1), 640.0)
    flow_x = smooth(np.interp(tg, ft, fx), 0.5)
    flow_share = smooth(np.interp(tg, ft, z["flow_share"].astype(float)), 0.5)
    flow_cx = smooth(np.interp(tg, ft, fcx) + cam, 0.5)
    pe = z["people"]
    out = {"t": tg, "pan": pan, "cam": cam, "energy": energy, "resp": resp, "flow_x": flow_x,
           "flow_share": flow_share, "flow_cx": flow_cx}
    if len(pe) >= 20:
        pt = pe[:, 0].astype(float)
        cxi = (pe[:, 1] + pe[:, 3]) / 2
        px = cxi + np.interp(pt, t, cam_frames)
        py = pe[:, 4].astype(float)
        keep = ~static_mask(pt, px, py) & ((pe[:, 4] - pe[:, 2]) >= 18)
        frames = np.unique(pt)
        med, lo, hi, n = [], [], [], []
        for f in frames:
            m = keep & (pt == f)
            if m.sum() >= 2:
                q = np.percentile(px[m], [10, 50, 90])
                lo.append(q[0])
                med.append(q[1])
                hi.append(q[2])
            else:
                lo.append(np.nan)
                med.append(np.nan)
                hi.append(np.nan)
            n.append(m.sum())
        med, lo, hi, n = map(np.array, (med, lo, hi, n))
        ok = ~np.isnan(med)
        if ok.sum() >= 10:
            cx = smooth(np.interp(tg, frames[ok], med[ok]), 1.0)
            out["cx"] = cx
            out["spread"] = smooth(np.interp(tg, frames[ok], hi[ok] - lo[ok]), 1.0)
            out["n"] = np.interp(tg, frames, n.astype(float))
            a, b = np.percentile(cx, [3, 97])
            c0, half = (a + b) / 2, max((b - a) / 2, 50.0)
            out["p"] = np.clip((cx - c0) / half, -1.5, 1.5)
            # people left / right of the court centre (canvas), per detection frame
            bal = []
            for f in frames:
                m = keep & (pt == f)
                if m.sum() >= 4:
                    left = (px[m] < c0).mean()
                    bal.append(1 - abs(2 * left - 1))
                else:
                    bal.append(np.nan)
            bal = np.array(bal)
            okb = ~np.isnan(bal)
            out["bal"] = smooth(np.interp(tg, frames[okb], bal[okb]), 1.0) if okb.sum() >= 5 else np.zeros(len(tg))
    if "cx" not in out:  # no usable detections: the moving pixels stand in for the people
        cx = out["flow_cx"]
        a, b = np.percentile(cx, [3, 97])
        c0, half = (a + b) / 2, max((b - a) / 2, 50.0)
        out |= {"cx": cx, "spread": np.zeros(len(tg)), "n": np.zeros(len(tg)), "bal": np.zeros(len(tg)),
                "p": np.clip((cx - c0) / half, -1.5, 1.5)}
    out["cx_v"] = np.gradient(out["cx"], DT)
    return out


def _rev(v: np.ndarray, i: int, kb: int, ka: int) -> tuple[float, float]:
    vb = v[max(0, i - kb):i].mean() if i > 0 else 0.0
    va = v[i:i + ka].mean() if i < len(v) else 0.0
    return float(vb), float(va)


def _robust_scale(x: np.ndarray) -> float:
    return float(max(np.percentile(np.abs(x), 90), 1e-6))


def restart_score(s: dict[str, np.ndarray]) -> np.ndarray:
    """Throw-off restart at t: (1) a lull in [t-3, t] (little motion, slow camera), (2) the play at
    the court centre during it, (3) people on both sides of the centre line, (4) activity picks up
    after t, (5) in [t-20, t-5] the play was near one end (the goal before). Product of soft terms
    in 0..1."""
    tg = s["t"]
    act = s["flow_share"] / max(np.median(s["flow_share"]), 1e-6)
    pan = np.abs(s["pan"]) / _robust_scale(s["pan"])
    spd = np.abs(s["cx_v"]) / _robust_scale(s["cx_v"])
    p = s["p"]
    out = np.zeros(len(tg))
    k3, k2 = round(3 / DT), round(2 / DT)
    for i in range(k3, len(tg) - k2):
        a_b = act[i - k3:i].mean()
        lull = np.clip(1.3 - a_b, 0, 1) * np.clip(1.2 - pan[i - k3:i].mean(), 0, 1) * np.clip(1.2 - spd[i - k3:i].mean(), 0, 1)
        if lull <= 0:
            continue
        centre = float(np.exp(-(p[i - k3:i].mean() / 0.35) ** 2))
        bal = 0.5 + 0.5 * float(s["bal"][i - k3:i].mean())
        a_a = act[i:i + k2].mean()
        start = float(np.clip((a_a - a_b) / max(a_b, 0.2), 0, 1))
        j0, j1 = max(0, i - round(20 / DT)), max(0, i - round(5 / DT))
        end_before = float(np.clip((np.abs(p[j0:j1]).max() - 0.3) / 0.4, 0, 1)) if j1 > j0 else 0.0
        out[i] = lull * centre * bal * start * end_before
    return out


def compute(s: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    tg = s["t"]
    kb, ka = round(BEFORE / DT), round(AFTER / DT)
    k1 = round(1.0 / DT)
    vp = s["pan"] / _robust_scale(s["pan"])
    vc = s["cx_v"] / _robust_scale(s["cx_v"])
    vf = s["flow_x"] / _robust_scale(s["flow_x"])
    play = (vp + vc + vf) / 3
    names = ("pan_rev", "still_swing", "pan_after", "cen_rev", "flow_rev", "play_rev", "energy_drop")
    out: dict[str, list[float]] = {k: [] for k in names}
    for i in range(len(tg)):
        b, a = _rev(s["pan"], i, kb, ka)
        out["pan_after"].append(abs(a))
        out["pan_rev"].append(float(np.sqrt(max(0.0, -b * a))))
        quiet = np.abs(s["pan"][max(0, i - k1):i]).mean() if i > 0 else 0.0
        out["still_swing"].append(abs(a) / (1.0 + quiet / 100))
        for name, v in (("cen_rev", vc), ("flow_rev", vf), ("play_rev", play)):
            b, a = _rev(v, i, kb, ka)
            out[name].append(float(np.sqrt(max(0.0, -b * a)) + 0.5 * abs(a)))
        eb = s["energy"][max(0, i - kb):i].mean() if i > 0 else 0.0
        ea = s["energy"][i:i + ka].mean()
        out["energy_drop"].append(float(np.log((eb + 0.1) / (ea + 0.1))))
    res = {k: np.array(v) for k, v in out.items()}
    res["restart"] = restart_score(s)
    lag = round(RESTART_LAG / DT)
    res["restart_back"] = np.r_[res["restart"][lag:], np.zeros(lag)]
    return res


PROFILE_WIN = (-2.0, 3.0)
CHANNELS = ("pan", "cx_v", "flow_x", "flow_share", "energy")


def channels(s: dict[str, np.ndarray], names: tuple[str, ...] = CHANNELS) -> np.ndarray:
    return np.column_stack([s[n] for n in names])


def profile_at(ch: np.ndarray, i: int, sign_cols: tuple[int, ...]) -> np.ndarray:
    """Window of the channels around grid index i (edge-padded); the signed (velocity) columns are
    flipped together so that the mean of the first of them after i is positive."""
    i0 = i + round(PROFILE_WIN[0] / DT)
    n = round((PROFILE_WIN[1] - PROFILE_WIN[0]) / DT)
    idx = np.clip(np.arange(i0, i0 + n), 0, len(ch) - 1)
    w = ch[idx].copy()
    if sign_cols:
        after = w[-round(PROFILE_WIN[1] / DT):, list(sign_cols)].sum()
        if after < 0:
            w[:, list(sign_cols)] *= -1
    return w


def main() -> None:
    z = np.load(sys.argv[1])
    s = signals(z)
    c = compute(s)
    for k, v in {**s, **c}.items():
        print(f"{k:12s} mean {np.mean(v):9.3f}  p10 {np.percentile(v, 10):9.3f}  p90 {np.percentile(v, 90):9.3f}")


if __name__ == "__main__":
    main()
