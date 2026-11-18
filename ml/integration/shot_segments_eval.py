"""Shots on whole segments with the product chain: are the shots found, and does the ball path
cover them (docs/plans/produkt-analyse-integration.md, shot test).

Two steps, both resumable (one directory per segment under OUT):

- `observe`: the product proxy (1280 px, 25 fps) and `observe()` as the analysis job runs it:
  camera motion, YOLOX on every 3rd frame, the ball net (hrp1, uint8 or float file) at WIDTH px on
  every EVERY-th frame; no shirt numbers, no re-identification (they do not feed the shot
  candidates or the ball path).
- `score`: against marks {segment: [[t_s, outcome], ...]} (outcome goal, save or miss; t_s the
  release, about 1 s precise):
  * goal candidates of the default list (rate <= 2, `goalcandidates`) against the goals, shot
    candidates (rate <= 4) against all shots; a mark is found when a candidate's estimated time
    lies within TOL_S (2 s), each candidate counts once (nearest first); recall per outcome,
    precision = candidates that found a mark / candidates;
  * ball path coverage: share of frames from 1.5 s before to 1.5 s after each shot with a ball
    point (`ballpossession.ball_path_v2`, no clock gate, no court needed); also the share of shots
    with a point on at least half of those frames;
  * 95 % intervals by a bootstrap over games (segments of one game together).

    uv run python ml/integration/shot_segments_eval.py observe SEGMENTS.json OUT MODELS \
        --ball MODEL.onnx --width 960 --every 3
    uv run python ml/integration/shot_segments_eval.py score MARKS.json OUT
    uv run python ml/integration/shot_segments_eval.py dense SEGMENTS.json MARKS.json OUT MODELS \
        --ball MODEL.onnx --width 960

`dense` approximates the GPU setting (ball net on every frame) for the ball path only, without
running a whole segment on every frame on the CPU: the net on every frame from DENSE_S (8 s) before
to DENSE_S after each mark (`ball_dense.json`), and `score` then also reports the coverage of a
ball path tracked on each such window alone (the tracker settles in the 6.5 s before the measured
window). The marks choose where it runs, so this gives no candidate recall or precision; those
come from the CPU setting only.
SEGMENTS.json: [{"dataset": "handball-segs-l01", "file": "<segment>.mp4"}, ...] (Kaggle).
"""

from __future__ import annotations

import argparse
import json
import random
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

TOL_S = 2.0
# the rule the shot candidates were built for (ml/goals/shot_eval.py): the candidate's peak from 3 s
# before to 8 s after the marked moment; reported next to the strict +-2 s of the estimated time
DESIGN_WINDOW_S = (3.0, 8.0)
BALL_WINDOW_S = 1.5
OWNER = "lukasde1000"
DENSE_S = 8.0


def _game(seg: str) -> str:
    return re.sub(r"_s\d+$", "", seg)


def _fetch_proxy(item: dict, d: Path) -> Path:
    """The segment from Kaggle as the product proxy (1280 px, 25 fps) in d."""
    from profile_analysis import _proxy_cmd

    raw, proxy = d / "raw.mp4", d / "proxy.mp4"
    if not proxy.exists():
        url = f"https://www.kaggle.com/api/v1/datasets/download/{OWNER}/{item['dataset']}/{item['file']}"
        curl = shutil.which("curl") or "curl"
        subprocess.run(
            [curl, "-sSfL", "-o", str(raw), url, "-H", "Authorization: Bearer dummy"], check=True
        )
        subprocess.run(_proxy_cmd(raw, proxy), check=True)
        raw.unlink()
    return proxy


def dense(segments: Path, marks_path: Path, out: Path, ball: Path, width: int) -> None:
    """Ball net on every frame within DENSE_S of each mark (resumable per segment)."""
    from handball_vision.ballnet import BallNet, frame_gap
    from handball_vision.pipeline import iter_frames

    marks = load_marks(marks_path)
    net = BallNet([ball], width=width)
    for item in json.loads(segments.read_text()):
        seg = Path(item["file"]).stem
        d = out / seg
        dst = d / "ball_dense.json"
        if dst.exists() or not marks.get(seg) or not (d / "observe.json").exists():
            continue
        fps = float(json.loads((d / "observe.json").read_text())["fps"])
        want = {
            f
            for t, _ in marks[seg]
            for f in range(round((t - DENSE_S) * fps), round((t + DENSE_S) * fps) + 1)
            if f >= 0
        }
        proxy = _fetch_proxy(item, d)
        t0 = time.perf_counter()
        gap = frame_gap(fps)
        buf: list = []
        todo: list[tuple[int, list]] = []
        res: dict[int, list] = {}

        for n, frame in enumerate(iter_frames(proxy)):
            buf.append(frame)
            if len(buf) > 2 * gap + 1:
                buf.pop(0)
            t = n - gap
            if len(buf) == 2 * gap + 1 and t in want:
                todo.append((t, [buf[0], buf[gap], buf[-1]]))
                if len(todo) >= 8:
                    _run_dense(net, todo, res)
        _run_dense(net, todo, res)
        dst.write_text(json.dumps({str(k): v for k, v in sorted(res.items())}))
        proxy.unlink()
        print(seg, len(res), round(time.perf_counter() - t0, 1), flush=True)
    print("finished", flush=True)


def _run_dense(net: object, todo: list[tuple[int, list]], res: dict[int, list]) -> None:
    for (t, _), c in zip(todo, net.run([tr for _, tr in todo]), strict=True):  # type: ignore[attr-defined]
        res[t] = c
    todo.clear()


def _dense_cover(d: Path, shots: list[tuple[float, str]]) -> list[float] | None:
    """Per mark: coverage +-BALL_WINDOW_S of a ball path tracked on its dense window alone."""
    src = d / "ball_dense.json"
    if not src.exists():
        return None
    from handball_vision.ballpossession import ball_path_v2
    from handball_vision.motion import CameraMotion

    cands = {int(k): [tuple(c) for c in v] for k, v in json.loads(src.read_text()).items()}
    fps = float(json.loads((d / "observe.json").read_text())["fps"])

    class _Obs:  # what ball_path_v2 reads
        pass

    obs = _Obs()
    obs.fps = fps  # type: ignore[attr-defined]
    obs.motion = CameraMotion.load(d / "motion.npz")  # type: ignore[attr-defined]
    out = []
    for t, _ in shots:
        lo_w, hi_w = round((t - DENSE_S) * fps), round((t + DENSE_S) * fps)
        win = {f: c for f, c in cands.items() if lo_w <= f <= hi_w}
        pts: set[int] = set()
        if win:
            first, path, _ = ball_path_v2(obs, win)
            pts = {first + k for k, q in enumerate(path) if q is not None}
        lo, hi = round((t - BALL_WINDOW_S) * fps), round((t + BALL_WINDOW_S) * fps)
        out.append(sum(f in pts for f in range(lo, hi + 1)) / max(1, hi - lo + 1))
    return out


def observe(segments: Path, out: Path, models: Path, ball: Path, width: int, every: int) -> None:
    from handball_vision import observe as learned
    from handball_vision.ballnet import BallNet
    from handball_vision.detection import YoloxDetector

    det = YoloxDetector(models / "yolox_s.onnx")
    net = BallNet([ball], width=width)
    for item in json.loads(segments.read_text()):
        seg = Path(item["file"]).stem
        d = out / seg
        if (d / "observations.npz").exists():
            continue
        d.mkdir(parents=True, exist_ok=True)
        proxy = _fetch_proxy(item, d)
        t0 = time.perf_counter()
        obs = learned.observe(proxy, det, detect_every=3, ball_net=net, ball_every=every)
        obs.motion.save(d / "motion.npz")
        learned.save_observations(obs, d / "observations.npz")
        (d / "observe.json").write_text(
            json.dumps(
                {
                    "wall_s": round(time.perf_counter() - t0, 1),
                    "frames": obs.total,
                    "fps": obs.fps,
                    "timings_s": obs.timings_s,
                    "width": width,
                    "every": every,
                }
            )
        )
        proxy.unlink()
        print(seg, obs.total, round(time.perf_counter() - t0, 1), flush=True)
    print("finished", flush=True)


def _segment_results(d: Path) -> dict:
    """Candidates and ball path of one segment from its stored observations (cached)."""
    cached = d / "results.json"
    if cached.exists():
        return json.loads(cached.read_text())
    from handball_vision import goalcandidates as gc
    from handball_vision import observe as learned
    from handball_vision.ballpossession import ball_path_v2
    from handball_vision.motion import CameraMotion

    obs = learned.load_observations(d / "observations.npz", CameraMotion.load(d / "motion.npz"))
    found = gc.from_observations(obs) or {"candidates": [], "shots": {"candidates": []}}
    g_c = [c for c in found["candidates"] if c["rate"] <= gc.DEFAULT_RATE]
    s_c = [c for c in found["shots"]["candidates"] if c["rate"] <= gc.SHOT_DEFAULT_RATE]
    goals = [c["goal_ms"] / 1000 for c in g_c]
    shots = [c["goal_ms"] / 1000 for c in s_c]
    points: list[int] = []
    if obs.ball_cands:
        first, path, _ = ball_path_v2(obs, obs.ball_cands)
        points = [first + k for k, q in enumerate(path) if q is not None]
    res = {
        "fps": obs.fps,
        "frames": obs.total,
        "goal_cands": goals,
        "shot_cands": shots,
        "goal_peaks": [c["t_ms"] / 1000 for c in g_c],
        "shot_peaks": [c["t_ms"] / 1000 for c in s_c],
        "ball_frames": points,
    }
    cached.write_text(json.dumps(res))
    return res


def _match(
    marks: list[float], cands: list[float], tol: float | tuple[float, float]
) -> tuple[list[bool], int]:
    """Per mark whether a candidate lies within tol (a pair (before, after): from `before` s
    before to `after` s after the mark); each candidate used once, nearest pairs first; and the
    number of candidates that found a mark."""
    before, after = (tol, tol) if isinstance(tol, float) else tol
    pairs = sorted(
        (abs(c - m), i, j)
        for i, m in enumerate(marks)
        for j, c in enumerate(cands)
        if -before <= c - m <= after
    )
    hit, used = [False] * len(marks), set()
    for _, i, j in pairs:
        if not hit[i] and j not in used:
            hit[i] = True
            used.add(j)
    return hit, len(used)


def _per_segment(marks: dict[str, list], out: Path) -> dict[str, dict]:
    per = {}
    for seg, shots in marks.items():
        d = out / seg
        if not (d / "observations.npz").exists():
            print("missing observations:", seg, flush=True)
            continue
        r = _segment_results(d)
        goals = [t for t, o in shots if o == "goal"]
        all_t = [t for t, _ in shots]
        g_hit, g_used = _match(goals, r["goal_cands"], TOL_S)
        s_hit, s_used = _match(all_t, r["shot_cands"], TOL_S)
        gd_hit, gd_used = _match(goals, r["goal_peaks"], DESIGN_WINDOW_S)
        sd_hit, sd_used = _match(all_t, r["shot_peaks"], DESIGN_WINDOW_S)
        frames = set(r["ball_frames"])
        cover = []
        for t, _ in shots:
            lo, hi = round((t - BALL_WINDOW_S) * r["fps"]), round((t + BALL_WINDOW_S) * r["fps"])
            n = max(1, hi - lo + 1)
            cover.append(sum(f in frames for f in range(lo, hi + 1)) / n)
        dense_cover = _dense_cover(d, shots)
        per[seg] = {
            "dense": dense_cover,
            "game": _game(seg),
            "shots": [(o, s_hit[k], cover[k]) for k, (_, o) in enumerate(shots)],
            "design_shots": [(o, sd_hit[k]) for k, (_, o) in enumerate(shots)],
            "goals_found_design": sum(gd_hit),
            "goal_cands_hit_design": gd_used,
            "shot_cands_hit_design": sd_used,
            "goals_found": sum(g_hit),
            "goals": len(goals),
            "goal_cands": len(r["goal_cands"]),
            "goal_cands_hit": g_used,
            "shot_cands": len(r["shot_cands"]),
            "shot_cands_hit": s_used,
            "minutes": r["frames"] / r["fps"] / 60,
        }
    return per


def _stats(per: dict[str, dict]) -> dict[str, float]:
    shots = [s for p in per.values() for s in p["shots"]]
    out: dict[str, float] = {}

    def share(xs: list[bool | float]) -> float:
        return sum(xs) / len(xs) if xs else float("nan")

    out["goal recall (goal cand.)"] = share(
        [True] * sum(p["goals_found"] for p in per.values())
        + [False] * sum(p["goals"] - p["goals_found"] for p in per.values())
    )
    gc_n = sum(p["goal_cands"] for p in per.values())
    out["goal cand. precision"] = (
        sum(p["goal_cands_hit"] for p in per.values()) / gc_n if gc_n else float("nan")
    )
    out["shot recall (shot cand.)"] = share([h for _, h, _ in shots])
    for o in ("goal", "save", "miss"):
        out[f"  {o}"] = share([h for oo, h, _ in shots if oo == o])
    sc_n = sum(p["shot_cands"] for p in per.values())
    out["shot cand. precision"] = (
        sum(p["shot_cands_hit"] for p in per.values()) / sc_n if sc_n else float("nan")
    )
    goals_n = sum(p["goals"] for p in per.values())
    out["-3/+8 s: goal recall"] = (
        sum(p["goals_found_design"] for p in per.values()) / goals_n if goals_n else float("nan")
    )
    out["-3/+8 s: goal cand. precision"] = (
        sum(p["goal_cands_hit_design"] for p in per.values()) / gc_n if gc_n else float("nan")
    )
    ds = [s for p in per.values() for s in p["design_shots"]]
    out["-3/+8 s: shot recall"] = share([h for _, h in ds])
    for o in ("goal", "save", "miss"):
        out[f"  -3/+8 s: {o}"] = share([h for oo, h in ds if oo == o])
    out["-3/+8 s: shot cand. precision"] = (
        sum(p["shot_cands_hit_design"] for p in per.values()) / sc_n if sc_n else float("nan")
    )
    out["ball coverage +-1.5 s"] = share([c for _, _, c in shots])
    out["shots with ball >= 50 %"] = share([c >= 0.5 for _, _, c in shots])
    dense = [c for p in per.values() if p["dense"] is not None for c in p["dense"]]
    if dense:
        out["dense: ball coverage +-1.5 s"] = share(dense)
        out["dense: shots with ball >= 50 %"] = share([c >= 0.5 for c in dense])
        # the CPU setting on exactly the shots that have a dense window (same shots compared)
        out["dense: CPU setting, same shots"] = share(
            [c for p in per.values() if p["dense"] is not None for _, _, c in p["shots"]]
        )
    minutes = sum(p["minutes"] for p in per.values())
    out["goal cand. per min"] = gc_n / minutes if minutes else float("nan")
    out["shot cand. per min"] = sc_n / minutes if minutes else float("nan")
    return out


def load_marks(path: Path) -> dict[str, list[tuple[float, str]]]:
    """{segment: [[t_s, outcome], ...]}, or the frozen end-test file (ml/gold/data/
    shot_endtest_marks.json: "segments" and "shots" [{seg, t_s, kind}])."""
    raw = json.loads(path.read_text())
    if isinstance(raw, dict) and "shots" in raw:
        out: dict[str, list[tuple[float, str]]] = {seg: [] for seg in raw.get("segments", [])}
        for sh in raw["shots"]:
            out.setdefault(sh["seg"], []).append((float(sh["t_s"]), str(sh["kind"])))
        return out
    return {k: [(float(t), str(o)) for t, o in v] for k, v in raw.items()}


def score(marks_path: Path, out: Path, boot: int = 2000) -> None:
    marks = load_marks(marks_path)
    per = _per_segment(marks, out)
    games = sorted({p["game"] for p in per.values()})
    by_game = {g: [s for s, p in per.items() if p["game"] == g] for g in games}
    base = _stats(per)
    rnd = random.Random(0)
    samples: dict[str, list[float]] = {k: [] for k in base}
    for _ in range(boot):
        pick = [s for g in (rnd.choice(games) for _ in games) for s in by_game[g]]
        st = _stats({f"{k}#{i}": per[k] for i, k in enumerate(pick)})
        for k, v in st.items():
            if v == v:  # not nan
                samples[k].append(v)
    n_shots = sum(len(p["shots"]) for p in per.values())
    print(f"{len(per)} segments, {len(games)} games, {n_shots} shots")
    report = {}
    for k, v in base.items():
        s = sorted(samples[k])
        lo, hi = (s[int(0.025 * len(s))], s[int(0.975 * len(s)) - 1]) if s else (float("nan"),) * 2
        per_min = "per min" in k
        fmt = (lambda x: f"{x:5.2f}") if per_min else (lambda x: f"{100 * x:5.1f} %")
        print(f"{k:28} {fmt(v)}  [{fmt(lo)}, {fmt(hi)}]")
        report[k] = {"value": v, "lo": lo, "hi": hi}
    counts = {
        o: sum(1 for p in per.values() for oo, _, _ in p["shots"] if oo == o)
        for o in ("goal", "save", "miss")
    }
    print("shots by outcome:", counts)
    (out / "score.json").write_text(
        json.dumps(
            {
                "segments": len(per),
                "games": len(games),
                "shots": n_shots,
                "by_outcome": counts,
                "metrics": report,
            },
            indent=1,
        )
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    o = sub.add_parser("observe")
    o.add_argument("segments", type=Path)
    o.add_argument("out", type=Path)
    o.add_argument("models", type=Path)
    o.add_argument("--ball", type=Path, required=True)
    o.add_argument("--width", type=int, default=960)
    o.add_argument("--every", type=int, default=3)
    dn = sub.add_parser("dense")
    dn.add_argument("segments", type=Path)
    dn.add_argument("marks", type=Path)
    dn.add_argument("out", type=Path)
    dn.add_argument("models", type=Path)
    dn.add_argument("--ball", type=Path, required=True)
    dn.add_argument("--width", type=int, default=960)
    s = sub.add_parser("score")
    s.add_argument("marks", type=Path)
    s.add_argument("out", type=Path)
    a = ap.parse_args()
    if a.cmd == "observe":
        observe(a.segments, a.out, a.models, a.ball, a.width, a.every)
    elif a.cmd == "dense":
        dense(a.segments, a.marks, a.out, a.ball, a.width)
    else:
        score(a.marks, a.out)


if __name__ == "__main__":
    main()
