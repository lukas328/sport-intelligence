"""Adaptive ball net: a thin base rate everywhere, every frame only where it matters (docs/plans/
produkt-analyse-integration.md, adaptive ball net). Simulated from stored net candidates, no GPU.

Policy per clip:
- base: the net on every `step`-th frame (e.g. 960 px, every 3rd proxy frame), tracked at that
  rate (`balltrack2.track` at fps / step, frames between filled linearly), as `ball_path_v2` does;
- dense windows: every frame (at the dense source's size) where the thin path says the ball is
  fast (speed above `fast_px_s` in 1280 px units), unsure (confidence below `min_conf`) or lost
  (no point), each widened by `margin_s`; plus, when given, around shot candidates
  (`handball_vision.goalcandidates` "shots", from the estimated shot time 3 s before to 1 s
  after);
- path: the thin path, replaced inside each dense window by `balltrack2.track` on the dense
  candidates of the window plus `margin_s` on each side.

Scores: gold v1 (`ml/gold/data/gold_ball_v1.json`, a hit is within 12 px of a gold ball; all,
fast) and the dev shot clips (`ml/gold/shot_clips.json`, split dev only; there is no ball gold, so
the share of frames from 3 s before to 1 s after the logged shot where the path lies within 12 px
of the dense path of the same net at 1280 px on every proxy frame, i.e. every 2nd frame of these
50/60 fps clips). The dense share is the share of frames
the net runs on at dense size inside the windows.

    uv run python ml/integration/adaptive_ball.py gold PRE_1280.json PRE_960_K3.json
    uv run python ml/integration/adaptive_ball.py shots PRE_1280_DEV.json PRE_960_DEV.json ROWS.json
PRE_1280: prelabel output (net candidates on every frame); PRE_960: candidates of the base frames;
ROWS: per dev shot segment the shot candidates (`goalcandidates.from_observations` output "shots").
"""

from __future__ import annotations

import json
import math
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from parity_tracker import GOLD, fps_of, peaks_of, rate, score  # noqa: E402

from handball_vision import balltrack2  # noqa: E402

Pt = tuple[float, float] | None


@dataclass(frozen=True)
class Policy:
    step: int  # base: net on every step-th native frame
    fast_px_s: float | None = None  # dense where the thin path is faster (1280 px units)
    min_conf: float | None = None  # dense where the thin path is less sure
    lost: bool = False  # dense where the thin path has no point
    margin_s: float = 0.5
    shots: bool = False  # dense around shot candidates
    shot_rate: int = 4  # shot candidates up to this rate
    shot_before_s: float = 3.0  # dense window around the estimated shot time
    shot_after_s: float = 1.0


def thin_path(base: dict[int, list], n: int, fps: float, step: int, w: float):
    ts = list(range(0, n, step))
    o, conf = balltrack2.track([base.get(t, []) for t in ts], fps / step, w)
    out: list[Pt] = [None] * n
    cf = [0.0] * n
    for i, t in enumerate(ts):
        out[t], cf[t] = o[i], conf[i]
    for i in range(len(ts) - 1):
        a, b = o[i], o[i + 1]
        if a is None or b is None:
            continue
        for j in range(1, step):
            t = ts[i] + j
            if t < n:
                out[t] = (a[0] + (b[0] - a[0]) * j / step, a[1] + (b[1] - a[1]) * j / step)
    return out, cf, ts


def dense_mask(
    pol: Policy,
    thin: list[Pt],
    cf: list[float],
    ts: list[int],
    fps: float,
    w: float,
    seeds_s: list[float],
) -> list[bool]:
    n = len(thin)
    m = [False] * n
    marg = round(pol.margin_s * fps)

    def mark(a: int, b: int) -> None:
        for t in range(max(0, a), min(n, b + 1)):
            m[t] = True

    for i in range(len(ts) - 1):
        t1, t2 = ts[i], ts[i + 1]
        a, b = thin[t1], thin[t2]
        hit = False
        if pol.lost and (a is None or b is None):
            hit = True
        if pol.min_conf is not None and (cf[t1] < pol.min_conf or cf[t2] < pol.min_conf):
            hit = True
        if pol.fast_px_s is not None and a is not None and b is not None:
            v = math.hypot(b[0] - a[0], b[1] - a[1]) * (1280 / w) * fps / (t2 - t1)
            hit |= v > pol.fast_px_s
        if hit:
            mark(t1 - marg, t2 + marg)
    for s in seeds_s:
        mark(round((s - pol.shot_before_s) * fps), round((s + pol.shot_after_s) * fps))
    return m


def runs(mask: list[bool]) -> list[tuple[int, int]]:
    out, start = [], None
    for t, v in enumerate([*mask, False]):
        if v and start is None:
            start = t
        elif not v and start is not None:
            out.append((start, t))
            start = None
    return out


def adaptive(
    pol: Policy,
    dense: list[list],
    base: dict[int, list],
    fps: float,
    w: float,
    seeds_s: list[float] = (),  # type: ignore[assignment]
    dense_step: int = 1,
) -> tuple[list[Pt], float]:
    """Path and the share of frames inside dense windows (the net runs on every `dense_step`-th
    of them: 2 for 50/60 fps clips, whose proxy has every 2nd frame)."""
    n = len(dense)
    thin, cf, ts = thin_path(base, n, fps, pol.step, w)
    mask = dense_mask(pol, thin, cf, ts, fps, w, list(seeds_s) if pol.shots else [])
    out = list(thin)
    marg = round(pol.margin_s * fps)
    for a, b in runs(mask):
        lo, hi = max(0, a - marg), min(n, b + marg)
        o, _ = balltrack2.track(dense[lo:hi:dense_step], fps / dense_step, w)
        pts: list[Pt] = [None] * (hi - lo)
        for i, q in enumerate(o):
            pts[i * dense_step] = q
        for i in range(len(o) - 1):
            p0, p1 = o[i], o[i + 1]
            if p0 is None or p1 is None:
                continue
            for j in range(1, dense_step):
                f = i * dense_step + j
                if f < len(pts):
                    pts[f] = (
                        p0[0] + (p1[0] - p0[0]) * j / dense_step,
                        p0[1] + (p1[1] - p0[1]) * j / dense_step,
                    )
        for t in range(a, b):
            out[t] = pts[t - lo]
    return out, sum(mask) / n


def policies() -> dict[str, Policy]:
    out = {}
    for k in (3, 4):
        out[f"base k{k}"] = Policy(k)
        out[f"k{k} all dense"] = Policy(k, min_conf=2.0)  # every frame dense: the reference rate
        for v in (600, 900, 1200):
            out[f"k{k} fast>{v}"] = Policy(k, fast_px_s=v)
            out[f"k{k} fast>{v} | lost"] = Policy(k, fast_px_s=v, lost=True)
            out[f"k{k} fast>{v} | lost | conf<0.3"] = Policy(
                k, fast_px_s=v, lost=True, min_conf=0.3
            )
        for v in (1500, 2000, 3000):
            out[f"k{k} fast>{v} m0.25"] = Policy(k, fast_px_s=v, margin_s=0.25)
        out[f"k{k} conf<0.1 m0.25"] = Policy(k, min_conf=0.1, margin_s=0.25)
        out[f"k{k} lost m0.25"] = Policy(k, lost=True, margin_s=0.25)
        out[f"k{k} lost"] = Policy(k, lost=True)
        out[f"k{k} conf<0.3 | lost"] = Policy(k, lost=True, min_conf=0.3)
        for r in (2, 4, 6):
            out[f"k{k} shots r{r}"] = Policy(k, shots=True, shot_rate=r)
            out[f"k{k} shots r{r} wide"] = Policy(
                k, shots=True, shot_rate=r, shot_before_s=5.0, shot_after_s=3.0
            )
            out[f"k{k} shots r{r} | fast>900 | lost"] = Policy(
                k, fast_px_s=900, lost=True, shots=True, shot_rate=r
            )
    return out


def gold_main(pre_dense: Path, pre_base: Path) -> None:
    dense = json.loads(pre_dense.read_text())["clips"]
    base_all = json.loads(pre_base.read_text())["clips"]
    ref = {
        cid: balltrack2.track(peaks_of(dense[cid]), fps_of(dense[cid]), dense[cid]["w"])[0]
        for cid in GOLD
    }
    per = score(ref)
    ids = sorted(per)
    print(f"{'policy':40} {'all':>6} {'fast':>6} {'dense':>6}")
    print(
        f"{'dense 1280 every frame':40} {100 * rate(per, ids, lambda v: True):5.1f}  "
        f"{100 * rate(per, ids, lambda v: v[1]):5.1f}  100.0"
    )
    for name, pol in policies().items():
        if pol.shots or pol.step != 3:
            continue  # gold clips have no shot candidates; the base is stored for every 3rd frame
        paths, share = {}, []
        for cid in GOLD:
            c = dense[cid]
            pk = peaks_of(c)
            b = {
                t: [tuple(v) for v in r["net"]]
                for t, r in enumerate(base_all[cid]["pre"])
                if r["net"]
            }
            # base candidates at 960 px are in 1280-px frame coordinates already (BallNet scale)
            paths[cid], s = adaptive(pol, pk, b, fps_of(c), c["w"])
            share.append((s, len(pk)))
        per = score(paths)
        ds = sum(s * n for s, n in share) / sum(n for _, n in share)
        print(
            f"{name:40} {100 * rate(per, ids, lambda v: True):5.1f}  "
            f"{100 * rate(per, ids, lambda v: v[1]):5.1f}  {100 * ds:5.1f}",
            flush=True,
        )


def shots_main(pre_dense: Path, pre_base: Path, rows_path: Path) -> None:
    dense = json.loads(pre_dense.read_text())["clips"]
    base_all = json.loads(pre_base.read_text())
    rows = {r["seg"]: r for r in json.loads(rows_path.read_text())}
    clips = {cid: c for cid, c in dense.items() if c.get("split") == "dev" and cid in base_all}
    print(
        f"{len(clips)} dev shot clips; segments with shot candidates: "
        f"{sum(c['file'] in rows for c in clips.values())}"
    )
    ref, seeds = {}, {}
    for cid, c in clips.items():
        # reference: the net at 1280 px on every proxy frame (every 2nd native frame at 50/60 fps),
        # what the product computes without any thinning
        ref[cid] = adaptive(
            Policy(6, min_conf=2.0), peaks_of(c), {}, fps_of(c), c["w"], dense_step=2
        )[0]
        sc = rows.get(c["file"], {}).get("sc", [])
        seeds[cid] = {
            r: [(x["goal_ms"] - c["start_ms"]) / 1000 for x in sc if x["rate"] <= r]
            for r in (2, 4, 6)
        }

    def agree(paths: dict[str, list[Pt]]) -> float:
        n = h = 0
        for cid, c in clips.items():
            fps = fps_of(c)
            lo = round((c["shot"]["log_ms"] / 1000 - 3) * fps)
            hi = round((c["shot"]["log_ms"] / 1000 + 1) * fps)
            for t in range(max(0, lo), min(len(ref[cid]), hi)):
                r = ref[cid][t]
                if r is None:
                    continue
                q = paths[cid][t]
                n += 1
                h += q is not None and math.hypot(q[0] - r[0], q[1] - r[1]) <= 12
        return h / max(1, n)

    print(f"{'policy':40} {'agree':>6} {'dense':>6}  (native 50/60 fps; step = 2 x k)")
    for name, pol in policies().items():
        if ONLY and name not in ONLY:
            continue
        pol2 = Policy(**{**pol.__dict__, "step": 2 * pol.step})  # proxy frames at 50/60 fps
        paths, share = {}, []
        for cid, c in clips.items():
            pk = peaks_of(c)
            b = {int(t): [tuple(v) for v in cands] for t, cands in base_all[cid].items()}
            paths[cid], s = adaptive(
                pol2, pk, b, fps_of(c), c["w"], seeds[cid][pol.shot_rate], dense_step=2
            )
            share.append((s, len(pk)))
        ds = sum(s * n for s, n in share) / sum(n for _, n in share)
        print(f"{name:40} {100 * agree(paths):5.1f}  {100 * ds:5.1f}", flush=True)


ONLY = None  # policy names to run (argument --only a,b)


def main() -> None:
    global ONLY
    args = sys.argv[1:]
    if "--only" in args:
        i = args.index("--only")
        ONLY = set(args[i + 1].split(","))
        args = args[:i] + args[i + 2 :]
    mode: Callable[..., None] = {"gold": gold_main, "shots": shots_main}[args[0]]
    mode(*[Path(p) for p in args[1:]])


if __name__ == "__main__":
    main()
