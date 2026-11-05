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
  `goalcandidates` samples from the every-3rd-frame detections (replicated online): the same
  2 Hz people inputs (the detector has no state) at a quarter of the detector cost.
eval: recall at 1 / 2 / 4 candidates per minute, peak - goal, window AUC, per game, for the
  research signals and the product signals with leave-one-game-out templates, channel swaps
  (which source hurts), and the no-play mask on the break windows below. Labels: the overlay
  (`seg_labels.py` on research caches, or on `seg_extract.py --no-det` caches of other games:
  `--more-labels`), else the official log (`segment_clock.py --labels`, `--log-labels`).

usage: nice -n 10 uv run --project packages/vision python ml/goals/product_path.py observe OUT SEG.mp4 [...] [--cheap]
       uv run --project packages/vision python ml/goals/product_path.py eval <scratch>/goals_raw/cache \
         <scratch>/goals_raw/labels.json --obs OUT [OUT2 ...] [--more-labels LABELS2.json]
"""

from __future__ import annotations

import argparse
import json
import re
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
    # found by the people-spread rule (`gc.bunched`) and confirmed on the thumbnails
    "CH_NLB_SGWaedenswilHorgen_Chenois_2023-05-13_s3": [(155, 180)],  # team time-out
    "CH_NLB_SGWaedenswilHorgen_Emmen_2022-11-17_s4": [(0, 27)],  # clock stopped, injury
    "CH_NLB_PlayoffFinal4_SGWaedenswilHorgen_Kreuzlingen_2022-05-29_s4": [(80, 104)],  # clock stopped
}
GOAL_KINDS = ("goal", "penalty_goal")
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
    detections."""
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
        if not want:
            continue
        t0 = time.perf_counter()
        found = detector.detect([frame])[0]
        timings["detection"] += time.perf_counter() - t0
        people = [d for d in found if d.cls != "ball"]
        if people:
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


def product_signals(obs_dirs: list[Path], stem: str) -> tuple[dict[str, np.ndarray], bool] | None:
    for d in obs_dirs:
        if (d / f"{stem}.obs.npz").exists():
            motion = CameraMotion.load(d / f"{stem}.motion.npz")
            obs = ob.load_observations(d / f"{stem}.obs.npz", motion)
            return gc.signals(*gc.inputs_from_observations(obs)), bool(motion.moving)
    return None


def log_labels(label_dir: Path) -> dict[str, dict]:
    """Segment labels from the official logs (`segment_clock.py --labels`) in the form of
    `seg_labels.py`, without an overlay reading: for segments without a research cache."""
    out = {}
    for f in sorted(label_dir.glob("*.json")):
        d = json.loads(f.read_text())
        for seg in d["segments"]:
            if not seg.get("clock_source"):
                continue
            stem = Path(seg["file"]).stem
            goals = [{"t": e["segment_ms"] / 1000, "score": e.get("score"),
                      "anchor_gap_s": e.get("anchor_gap_s")}
                     for e in d["entries"] if e["segment"] == seg["file"] and e["kind"] in GOAL_KINDS]
            out[stem] = {"game": re.sub(r"\.f\d+$", "", d["name"]), "clock_source": seg["clock_source"], "score_reads": 0,
                         "overlay_goals": [], "log_goals": goals}
    return out


def logo_templates(sigs: dict, refs: dict, game: dict, games: set[str]) -> dict[str, gc.Template]:
    """For every game in `games`: a template from the goals in `sigs` of all other games."""
    ex: dict[str, list] = defaultdict(list)
    for k, s in sigs.items():
        ex[game[k]] += gt.profile(s, refs.get(k, []))
    out = {}
    for g in games:
        prof = np.mean([e for gg, v in ex.items() if gg != g for e in v], axis=0)
        out[g] = gc.Template.from_dict(gt.template_dict(prof, "logo", {}))
    return out


def measure(series: dict, sigs: dict, refs: dict, stems: list[str], play: dict | None = None
            ) -> dict[str, Any]:
    row: dict[str, Any] = {"goals": sum(len(refs[k]) for k in stems),
                           "minutes": sum(float(sigs[k]["t"][-1]) for k in stems) / 60}
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
            row["err"] = ((float(np.median(errs)), float(np.subtract(*np.percentile(errs, [75, 25]))))
                          if errs else (float("nan"), float("nan")))
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


def short(g: str) -> str:
    if not g.startswith("CH_NLB_"):
        return g
    for a in ("CH_NLB_", "PlayoffFinal4_", "PlayoffFinal_", "SGWaedenswilHorgen_", "_SGWaedenswilHorgen"):
        g = g.replace(a, "")
    return g


def cmd_eval(a: argparse.Namespace) -> None:
    labels = json.loads(a.labels.read_text())
    delay, _ = se.log_delay(labels)
    extra = json.loads(a.more_labels.read_text()) if a.more_labels else {}
    logs = log_labels(a.log_labels)
    prod, moving, refs, game, research = {}, {}, {}, {}, set()
    for stem in sorted(set(labels) | set(extra) | set(logs)):
        lab = labels.get(stem) or extra.get(stem) or logs[stem]
        got = product_signals(a.obs, stem)
        if got is None:
            continue
        s, mv = got
        dur = float(s["t"][-1])
        goals, src = se.reference({"duration_s": dur, **lab}, delay)
        if src == "none":
            continue
        prod[stem], moving[stem] = s, mv
        refs[stem] = [g for g in goals if gt.EDGE_MARGIN_S <= g <= dur - gt.EDGE_MARGIN_S]
        game[stem] = lab["game"]
        if stem in labels and (a.cache / f"{stem}.npz").exists():
            research.add(stem)
    games = set(game.values())
    cam = {g: "panning" if any(moving[k] for k in game if game[k] == g) else "fixed" for g in games}
    use_r = sorted(research)
    test_r = [k for k in use_r if game[k] not in se.DEV_GAMES]
    print(f"{len(prod)} labelled segments with a product pass ({sum(len(refs[k]) for k in prod)} goals, "
          f"{len(games)} games); research set {len(use_r)} segments, {sum(len(refs[k]) for k in use_r)} "
          f"goals, {len({game[k] for k in use_r})} games; log delay {delay:+.1f} s")
    res = {k: gt.cache_signals(np.load(a.cache / f"{k}.npz")) for k in use_r}
    t_res = logo_templates(res, refs, game, games)  # learned on the research set only
    t_prod = logo_templates(prod, refs, game, games)  # learned on every labelled product pass
    shipped = gc.load_template()

    def score(sigs: dict, tm: dict | gc.Template) -> dict:
        return {k: gc.score(sigs[k], tm if isinstance(tm, gc.Template) else tm[game[k]])
                for k in sigs}

    def idle(sigs: dict) -> dict:
        return {k: ~gc.no_play(sigs[k], cam[game[k]] == "panning") for k in sigs}

    pr = {k: prod[k] for k in use_r}
    rows = {
        "research signals, research template": (res, score(res, t_res), None),
        "product signals, research template": (pr, score(pr, t_res), None),
        "product signals, product template": (pr, score(pr, t_prod), None),
        "product signals, research template, no-play mask": (pr, score(pr, t_res), idle(pr)),
        "product pan + research people, research template":
            (sw := swap(res, pr, ("pan",)), score(sw, t_res), None),
        "research pan + product people, research template":
            (sw2 := swap(pr, res, ("pan",)), score(sw2, t_res), None),
    }
    print("\nResearch set, leave-one-game-out templates (shipped selection; recall at 1 / 2 / 4 per "
          "minute, peak - goal at 2 per minute, window AUC)\n\n| signals, template | all: recall | "
          "peak - goal (IQR) | AUC | test: recall | test AUC |\n|---|---|---|---|---|---|")
    out: dict[str, Any] = {}
    for name, (sigs, ser, play) in rows.items():
        r_all = measure(ser, sigs, refs, use_r, play)
        r_test = measure(ser, sigs, refs, test_r, play)
        out[name] = r_all
        print(f"| {name} | {fmt(r_all)} | {r_test['r1']:.2f} / {r_test['r2']:.2f} / "
              f"{r_test['r4']:.2f} | {r_test['auc']:.3f} |")

    # every game: product path as shipped (no-play mask), template held out from the game
    ser_r, ser_p, ser_s = score(prod, t_res), score(prod, t_prod), score(prod, shipped)
    play = idle(prod)
    print("\nEvery labelled game, product path with the no-play mask (recall @1 / 2 / 4 | peak - goal "
          "| AUC); research template = learned on the research set without the game\n\n| game | "
          "camera | labels | goals / min | research path (research set only) | product, research "
          "template | product, product template (LOGO) |\n|---|---|---|---|---|---|---|")
    groups: dict[str, list[str]] = defaultdict(list)
    for g in sorted(games, key=lambda g: (g not in {game[k] for k in use_r}, cam[g], g)):
        ks = sorted(k for k in prod if game[k] == g)
        rr = [k for k in ks if k in research]
        c1 = fmt(measure(score({k: res[k] for k in rr}, t_res), res, refs, rr)) if rr else "-"
        m_r = measure(ser_r, prod, refs, ks, play)
        m_p = measure(ser_p, prod, refs, ks, play)
        src = "overlay" if any(labels.get(k, extra.get(k, {})).get("overlay_goals") for k in ks) else "log"
        dev = " (dev)" if g in se.DEV_GAMES else ""
        print(f"| {short(g)}{dev} | {cam[g]} | {src} | {m_r['goals']} / {m_r['minutes']:.0f} | {c1} | "
              f"{fmt(m_r)} | {fmt(m_p)} |")
        set_name = "research set (13 SG W/H games)" if rr else f"new games, {cam[g]} camera"
        groups[set_name] += ks
        groups[f"all, {cam[g]} camera"] += ks
    print("\n| set | segments | goals / min | product, research template | product, product template "
          "(LOGO) | product, shipped template |\n|---|---|---|---|---|---|")
    for name, ks in sorted(groups.items()):
        m_r = measure(ser_r, prod, refs, ks, play)
        m_p = measure(ser_p, prod, refs, ks, play)
        m_s = measure(ser_s, prod, refs, ks, play)
        out[f"set: {name}"] = m_r
        print(f"| {name} | {len(ks)} | {m_r['goals']} / {m_r['minutes']:.0f} | {fmt(m_r)} | {fmt(m_p)} "
              f"| {fmt(m_s)} |")

    # no play: break windows (labelled or not) and labelled play
    stems = sorted({p.name[: -len(".obs.npz")] for d in a.obs for p in d.glob("*.obs.npz")})
    tally = {n: {"break": 0.0, "play": 0.0, "lost": []} for n in ("parked", "bunched", "no_play")}
    tot = {"break": 0.0, "play": 0.0}
    cands = {"none": 0, "parked": 0, "no_play": 0}
    for k in stems:
        got = (prod[k], moving[k]) if k in prod else product_signals(a.obs, k)
        assert got is not None
        s, mv = got
        g = game.get(k)
        panning = cam[g] == "panning" if g in cam else (mv or PANNING_GAMES)
        t = s["t"]
        brk = np.zeros(len(t), bool)
        for lo, hi in BREAKS.get(k, []):
            brk |= (t >= lo) & (t <= hi)
        tot["break"] += float(brk.sum()) * gc.DT
        tot["play"] += float((~brk).sum()) * gc.DT
        masks = {"parked": gc.parked(s, panning), "bunched": gc.bunched(s)}
        masks["no_play"] = masks["parked"] | masks["bunched"]
        for n, m in masks.items():
            tally[n]["break"] += float((brk & m).sum()) * gc.DT
            tally[n]["play"] += float((~brk & m).sum()) * gc.DT
            tally[n]["lost"] += [(k, g0) for g0 in refs.get(k, []) if m[(t > g0 - 3) & (t < g0 + 8)].any()]
        if k in BREAKS:
            sc = gc.score(s, t_res[g] if g in t_res else shipped)
            for n, m in (("none", None), ("parked", masks["parked"]), ("no_play", masks["no_play"])):
                found = gc.pick(t, sc, play=None if m is None else ~m)
                cands[n] += sum(any(lo <= c.t <= hi for lo, hi in BREAKS[k])
                                for c in found if c.rate <= gc.DEFAULT_RATE)
    print(f"\nNo play on {len(stems)} segments with a product pass: {tot['break'] / 60:.1f} break "
          f"minutes (half-time, before / after the game, time-outs, stoppages; eyeballed), "
          f"{tot['play'] / 60:.1f} other minutes\n\n| rule | break minutes flagged | other minutes "
          f"flagged | goals within -3..+8 s of a flagged point |\n|---|---|---|---|")
    for n, v in tally.items():
        print(f"| {n} | {v['break'] / 60:.1f} | {v['play'] / 60:.2f} | {len(v['lost'])} {v['lost']} |")
    print(f"\ncandidates at {gc.DEFAULT_RATE}/min in the break windows: none {cands['none']}, parked "
          f"{cands['parked']}, parked or bunched {cands['no_play']}")
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
    e.add_argument("cache", type=Path, help="research caches (seg_extract.py)")
    e.add_argument("labels", type=Path, help="seg_labels.py output for the research caches")
    e.add_argument("--obs", type=Path, nargs="+", required=True, help="observe outputs")
    e.add_argument("--more-labels", type=Path, help="seg_labels.py output for other caches "
                   "(overlay reading of segments without people, seg_extract.py --no-det)")
    e.add_argument("--log-labels", type=Path, default=ROOT / "ml/data/segment_labels")
    e.add_argument("--out", type=Path)
    a = ap.parse_args()
    cmd_observe(a) if a.cmd == "observe" else cmd_eval(a)


if __name__ == "__main__":
    main()
