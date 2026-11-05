"""Goal candidates on the product path, end to end, against the overlay labels.

The template was learned from the research pass (`seg_extract.py`: YOLOX-m at 2 Hz on the 60 fps
segment, phase-correlation pan). The product sees something else: the worker's analysis proxy
(1280 px, 25 fps, CRF 26) and one observation pass (`observe.observe`: the rotation-model camera
motion on every frame, YOLOX-s on every 3rd frame), from which `goalcandidates` samples the
people at 2 Hz. This script runs that path on the labelled segments and compares it with the
research signals on the same segments.

observe: per segment, the worker's proxy (`transcode.proxy_command` settings) and the observation
  pass; stores `<stem>.obs.npz` and `<stem>.motion.npz` (`observe.save_observations`,
  `CameraMotion.save`), deletes the proxy. `--cheap` runs the detector only on the frames that
  `goalcandidates` samples from the every-3rd-frame detections (replicated online) plus every 6th
  frame: the same 2 Hz people at about 40 % of the detector cost.
eval: recall at 1 / 2 / 4 candidates per minute, peak - goal, window AUC, per game, for the
  research signals and the product signals with leave-one-game-out templates, channel swaps
  (which source hurts), and the no-play mask on the break windows below.

usage: nice -n 10 uv run --project packages/vision python ml/goals/product_path.py observe OUT SEG.mp4 [...] [--cheap]
       uv run --project packages/vision python ml/goals/product_path.py eval OUT <scratch>/goals_raw/cache \
         <scratch>/goals_raw/labels.json
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "packages/vision"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import goal_template as gt  # noqa: E402
import seg_eval as se  # noqa: E402

from handball_vision import goalcandidates as gc  # noqa: E402
from handball_vision import observe as ob  # noqa: E402
from handball_vision.motion import CameraMotion  # noqa: E402

# no play in the labelled footage, eyeballed on the 1 Hz thumbnails of the research cache (+-5 s)
BREAKS = {
    "CH_NLB_SGWaedenswilHorgen_BSVStans_2022-11-05_s0": [(0, 118)],  # before the game
    "CH_NLB_SGWaedenswilHorgen_BSVStans_2022-11-05_s2": [(25, 180)],  # half-time, replays
    "CH_NLB_SGWaedenswilHorgen_Chenois_2023-05-13_s2": [(0, 180)],  # half-time
    "CH_NLB_SGWaedenswilHorgen_Chenois_2023-05-13_s4": [(0, 180)],  # after the game
    "CH_NLB_SGWaedenswilHorgen_FortitudoGossau_2023-09-23.f298_s2": [(0, 180)],  # half-time
    "CH_NLB_SGWaedenswilHorgen_HSGBadenEndingen_2023-11-19_s2": [(0, 180)],  # half-time
    "CH_NLB_SGWaedenswilHorgen_HCArbon_2023-12-10_s0": [(0, 157)],  # before the game
    "CH_NLB_SGWaedenswilHorgen_HSGBadenEndingen_2023-11-19_s1": [(110, 170)],  # team time-out
    "CH_NLB_SGWaedenswilHorgen_Emmen_2023-09-03_s4": [(78, 135)],  # team time-out
    "CH_NLB_SGWaedenswilHorgen_HCArbon_2023-12-10_s4": [(44, 118)],  # team time-out
}
PANNING_GAMES = True  # every labelled game is filmed by an operated, panning camera


# --- observe --------------------------------------------------------------------------------------


def proxy(src: Path, dst: Path, threads: int) -> None:
    """The worker's analysis proxy (apps/worker media/transcode.proxy_command)."""
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostdin", "-y", "-loglevel", "error", "-threads", str(threads),
         "-i", str(src), "-vf", "scale=1280:-2,fps=25", "-an", "-c:v", "libx264", "-preset",
         "veryfast", "-crf", "26", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(dst)],
        check=True,
    )


def observe_cheap(path: Path, detector: Any, detect_every: int = 3) -> ob.Observations:
    """`observe.observe` reduced to what the goal candidates use: the camera motion on every frame
    and the detector on the frames `goalcandidates` samples at 2 Hz from the every-3rd-frame
    detections, plus every 2nd detection frame."""
    from handball_vision.motion import MotionEstimator
    from handball_vision.pipeline import _open, iter_frames

    _, _, fps, total = _open(path)
    est = MotionEstimator(keep_every=max(1, total // 30) if total else 25)
    frames, timings = [], defaultdict(float)
    next_t, n = 0.0, -1
    for n, frame in enumerate(iter_frames(path)):
        t0 = time.perf_counter()
        est.add(frame)
        timings["camera_motion"] += time.perf_counter() - t0
        if n % detect_every:
            continue
        t = n / fps
        want = t >= next_t - 0.5 / fps
        if not want and n % (2 * detect_every):
            continue
        t0 = time.perf_counter()
        found = detector.detect([frame])[0]
        timings["detection"] += time.perf_counter() - t0
        people = [d for d in found if d.cls != "ball"]
        if want and people:
            next_t = max(next_t + gc.PEOPLE_DT, t + 0.5 * gc.PEOPLE_DT)
        balls = [d for d in found if d.cls == "ball"]
        frames.append(ob.FrameObservation(n, people, [None] * len(people), balls))
    t0 = time.perf_counter()
    motion = est.finish()
    timings["camera_motion"] += time.perf_counter() - t0
    motion.samples = []
    return ob.Observations(motion, frames, {}, fps, n + 1, dict(timings), detector.source)


def cmd_observe(a: argparse.Namespace) -> None:
    import cv2

    from handball_vision.detection import YoloxDetector

    cv2.setNumThreads(a.threads)
    det = YoloxDetector(a.model, threads=a.threads)
    a.out.mkdir(parents=True, exist_ok=True)
    for v in a.videos:
        if (a.out / f"{v.stem}.obs.npz").exists():
            continue
        tmp = a.out / f"{v.stem}.proxy.mp4"
        t0 = time.perf_counter()
        proxy(v, tmp, a.threads)
        t1 = time.perf_counter()
        if a.cheap:
            obs = observe_cheap(tmp, det)
        else:
            obs = ob.observe(tmp, det, detect_every=3, segment_every=10**9)
        obs.motion.panorama = None
        obs.motion.save(a.out / f"{v.stem}.motion.npz")
        ob.save_observations(obs, a.out / f"{v.stem}.obs.npz")
        tmp.unlink()
        info = {"stem": v.stem, "cheap": a.cheap, "proxy_s": round(t1 - t0, 1),
                "timings": {k: round(x, 1) for k, x in obs.timings_s.items()},
                "moving": obs.motion.moving}
        (a.out / f"{v.stem}.info.json").write_text(json.dumps(info))
        print(json.dumps(info), flush=True)


# --- eval -----------------------------------------------------------------------------------------


def product_signals(obs_dir: Path, stem: str) -> tuple[dict[str, np.ndarray], bool]:
    motion = CameraMotion.load(obs_dir / f"{stem}.motion.npz")
    obs = ob.load_observations(obs_dir / f"{stem}.obs.npz", motion)
    return gc.signals(*gc.inputs_from_observations(obs)), bool(motion.moving)


def logo_templates(sigs: dict, refs: dict, game: dict) -> dict[str, gc.Template]:
    ex: dict[str, list] = defaultdict(list)
    for k, s in sigs.items():
        ex[game[k]] += gt.profile(s, refs.get(k, []))
    out = {}
    for g in set(game.values()):
        prof = np.mean([e for gg, v in ex.items() if gg != g for e in v], axis=0)
        out[g] = gc.Template.from_dict(gt.template_dict(prof, "logo", {}))
    return out


def measure(series: dict, sigs: dict, refs: dict, stems: list[str], play: dict | None = None
            ) -> dict[str, Any]:
    row: dict[str, Any] = {"goals": sum(len(refs[k]) for k in stems)}
    cands = {k: gc.pick(sigs[k]["t"], series[k], play=None if play is None else play[k])
             for k in stems}
    for r in gc.RATES:
        hits, errs = 0, []
        for k in stems:
            h, e = se.match([c.t for c in cands[k] if c.rate <= r], refs[k])
            hits += h
            errs += e
        row[f"r{r}"] = hits / max(row["goals"], 1)
        if r == gc.DEFAULT_RATE:
            row["err"] = (float(np.median(errs)), float(np.subtract(*np.percentile(errs, [75, 25]))))
    row["auc"] = se.window_auc({k: series[k] for k in stems},
                               {k: {"x": {"t": sigs[k]["t"]}} for k in stems}, refs)
    row["n_cands"] = {r: sum(1 for k in stems for c in cands[k] if c.rate <= r) for r in gc.RATES}
    row["cands"] = cands
    return row


def fmt(r: dict) -> str:
    return (f"{r['r1']:.2f} / {r['r2']:.2f} / {r['r4']:.2f} | {r['err'][0]:+.1f} s ({r['err'][1]:.1f})"
            f" | {r['auc']:.3f}")


def swap(base: dict, donor: dict, chans: tuple[str, ...]) -> dict:
    out = {}
    for k in base:
        n = min(len(base[k]["t"]), len(donor[k]["t"]))
        out[k] = {c: (donor[k] if c in chans else base[k])[c][:n] for c in base[k]}
    return out


def cmd_eval(a: argparse.Namespace) -> None:
    labels = json.loads(a.labels.read_text())
    delay, _ = se.log_delay(labels)
    refs, game = {}, {}
    for stem, lab in sorted(labels.items()):
        if not (a.obs / f"{stem}.obs.npz").exists() or not (a.cache / f"{stem}.npz").exists():
            continue
        goals, src = se.reference(lab, delay)
        if src == "none":
            continue
        dur = lab["duration_s"]
        refs[stem] = [g for g in goals if gt.EDGE_MARGIN_S <= g <= dur - gt.EDGE_MARGIN_S]
        game[stem] = lab["game"]
    use = sorted(refs)
    test = [k for k in use if game[k] not in se.DEV_GAMES]
    print(f"{len(use)} labelled segments, {sum(len(refs[k]) for k in use)} goals, "
          f"{len(set(game.values()))} games ({len(test)} test segments)")
    res = {k: gt.cache_signals(np.load(a.cache / f"{k}.npz")) for k in use}
    prod, moving = {}, {}
    for k in use:
        prod[k], moving[k] = product_signals(a.obs, k)
    t_res = logo_templates(res, refs, game)
    t_prod = logo_templates(prod, refs, game)

    def score(sigs: dict, tm: dict) -> dict:
        return {k: gc.score(sigs[k], tm[game[k]]) for k in sigs}

    rows = {
        "research signals, research template": (res, score(res, t_res)),
        "product signals, research template": (prod, score(prod, t_res)),
        "product signals, product template": (prod, score(prod, t_prod)),
        "product pan + research people, research template":
            (sw := swap(res, prod, ("pan",)), score(sw, t_res)),
        "research pan + product people, research template":
            (sw2 := swap(prod, res, ("pan",)), score(sw2, t_res)),
    }
    print("\n| signals, template (leave-one-game-out) | recall @1 / 2 / 4 | peak - goal (IQR) | AUC "
          "| test recall | test AUC |\n|---|---|---|---|---|---|")
    out = {}
    for name, (sigs, ser) in rows.items():
        r_all = measure(ser, sigs, refs, use)
        r_test = measure(ser, sigs, refs, test)
        out[name] = r_all
        print(f"| {name} | {fmt(r_all)} | {r_test['r1']:.2f} / {r_test['r2']:.2f} / "
              f"{r_test['r4']:.2f} | {r_test['auc']:.3f} |")
    print("\n| game | goals | research @1/2/4, peak - goal, AUC | product (product template) |\n"
          "|---|---|---|---|")
    for g in sorted(set(game.values())):
        ks = [k for k in use if game[k] == g]
        a1 = measure(rows["research signals, research template"][1], res, refs, ks)
        a2 = measure(rows["product signals, product template"][1], prod, refs, ks)
        name = g.replace("CH_NLB_", "").replace("SGWaedenswilHorgen", "").strip("_")
        dev = " (dev)" if g in se.DEV_GAMES else ""
        print(f"| {name}{dev} | {a1['goals']} | {fmt(a1)} | {fmt(a2)} |")

    # no play: break windows (labelled or not) and labelled play
    stems = sorted(p.name[: -len(".obs.npz")] for p in a.obs.glob("*.obs.npz"))
    flagged = {"break": [0.0, 0.0], "play": [0.0, 0.0]}
    lost, removed, kept = [], 0, 0
    for k in stems:
        s, mv = (prod[k], moving[k]) if k in prod else product_signals(a.obs, k)
        idle = gc.no_play(s, mv or PANNING_GAMES)
        t = s["t"]
        brk = np.zeros(len(t), bool)
        for lo, hi in BREAKS.get(k, []):
            brk |= (t >= lo) & (t <= hi)
        for name, m in (("break", brk), ("play", ~brk)):
            flagged[name][0] += float(m.sum()) * gc.DT
            flagged[name][1] += float((m & idle).sum()) * gc.DT
        for g in refs.get(k, []):
            if idle[(t > g - 3) & (t < g + 8)].any():
                lost.append((k, g))
        if k in BREAKS:
            sc = gc.score(s, t_prod[game[k]] if k in game else gc.load_template())
            before = [c for c in gc.pick(t, sc) if c.rate <= gc.DEFAULT_RATE]
            after = [c for c in gc.pick(t, sc, play=~idle) if c.rate <= gc.DEFAULT_RATE]
            inb = [any(lo <= c.t <= hi for lo, hi in BREAKS[k]) for c in before]
            removed += sum(inb) - sum(any(lo <= c.t <= hi for lo, hi in BREAKS[k]) for c in after)
            kept += sum(inb)
    print(f"\nno play: {flagged['break'][1] / 60:.1f} of {flagged['break'][0] / 60:.1f} break minutes "
          f"flagged, {flagged['play'][1] / 60:.1f} of {flagged['play'][0] / 60:.1f} play minutes; "
          f"goals within 3 s before / 8 s after a flagged point: {len(lost)} {lost}; "
          f"candidates at {gc.DEFAULT_RATE}/min in break windows: {kept} -> {kept - removed}")
    if a.out:
        a.out.write_text(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "cands"}
                                     for k, v in out.items()}, indent=1))


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    o = sub.add_parser("observe")
    o.add_argument("out", type=Path)
    o.add_argument("videos", nargs="+", type=Path)
    o.add_argument("--cheap", action="store_true")
    o.add_argument("--threads", type=int, default=2)
    o.add_argument("--model", type=Path, default=ROOT / "data/models/yolox_s.onnx")
    e = sub.add_parser("eval")
    e.add_argument("obs", type=Path)
    e.add_argument("cache", type=Path)
    e.add_argument("labels", type=Path)
    e.add_argument("--out", type=Path)
    a = ap.parse_args()
    cmd_observe(a) if a.cmd == "observe" else cmd_eval(a)


if __name__ == "__main__":
    main()
