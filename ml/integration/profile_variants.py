"""Runtime of the analysis job under several settings, for the GPU decision (docs/plans/
produkt-analyse-integration.md steps 3 and 4). Each variant is one full `run_analysis` on the same
proxy (`profile_analysis.run_once`); a variant whose result file already exists in OUT is skipped,
so an interrupted run continues where it stopped (Modal preemption).

Variants (JobSettings overrides on top of the CPU image settings):
- cpu_image: the settings deployed on Azure staging (detect every 3rd frame, numbers every 6th), no
  ball net (on a GPU machine the models still run on the GPU: the settings, not the hardware);
- cuda_image: the settings of Dockerfile.cuda (detect every frame, numbers every 3rd), no ball net;
- cuda_ball_ens: cuda_image + ball nets hr1 + hrp1 (fp16) on every frame;
- cuda_ball_hrp1: cuda_image + hrp1 only (fp16);
- cuda_ball_ens_lean: the ensemble with detection every 3rd frame and numbers every 6th (the
  cheapest setting that keeps the ball on every frame);
- cuda_lean: detection every 3rd frame, numbers on every detection frame with budget 0.3, no ball
  net (job 14: the GPU job without the full-rate detection of cuda_image);
- cuda_lean_hrp1: cuda_lean + hrp1 (fp16) on every frame.
`bench_nets` also times the ball nets alone (fp32/fp16, batch 1/4/8) on real triplets.

The cost per game is wall time x price per second, scaled from the profiled minutes to 60
minutes of video. Prices (USD per hour): Modal T4 0.59 (JOBS.md measured about 0.66 with
overheads), Azure Container Apps serverless T4 in switzerlandnorth 0.37 for the GPU plus 4 vCPU and
16 GiB about 0.90 in all (docs/plans/gpu-analyse.md on the UX branch, 2026-11-16).

    uv run python ml/integration/profile_variants.py PROXY.mp4 --models DIR --out DIR [--variants a,b]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from profile_analysis import run_once  # noqa: E402

PRICE_USD_H = {"modal_t4": 0.66, "azure_t4_4vcpu_16gib": 0.90}


def variants(models: Path) -> dict[str, dict[str, object]]:
    ens = f"{models / 'ball_hr1_fp16.onnx'},{models / 'ball_hrp1_fp16.onnx'}"
    cuda = {"detect_every": 1, "number_every": 3}
    lean = {"detect_every": 3, "number_every": 3, "number_budget": 0.3}
    return {
        "cpu_image": {},
        "cuda_image": cuda,
        "cuda_ball_ens": {**cuda, "ball_model": ens},
        "cuda_ball_hrp1": {**cuda, "ball_model": str(models / "ball_hrp1_fp16.onnx")},
        "cuda_ball_ens_lean": {"ball_model": ens},
        "cuda_lean": lean,
        "cuda_lean_hrp1": {**lean, "ball_model": str(models / "ball_hrp1_fp16.onnx")},
    }


def bench_nets(video: Path, models: Path, n: int = 120) -> dict[str, float]:
    """ms per frame of each ball net file alone, per batch size, on the first n triplets."""
    import cv2

    from handball_vision.ballnet import BallNet

    cap = cv2.VideoCapture(str(video))
    frames = []
    while len(frames) < n + 4:
        ok, f = cap.read()
        if not ok:
            break
        frames.append(f)
    cap.release()
    trips = [[frames[i], frames[i + 2], frames[i + 4]] for i in range(len(frames) - 4)]
    out: dict[str, float] = {}
    for name in ("ball_hr1", "ball_hrp1", "ball_hr1_fp16", "ball_hrp1_fp16"):
        path = models / f"{name}.onnx"
        if not path.is_file():
            continue
        net = BallNet([path])
        out[f"{name}_providers"] = net.sessions[0].get_providers()[0]  # type: ignore[assignment]
        for b in (1, 4, 8):
            net.run(trips[:b])  # warm-up
            t0 = time.perf_counter()
            for i in range(0, len(trips) - b + 1, b):
                net.run(trips[i : i + b])
            done = (len(trips) // b) * b
            out[f"{name}_b{b}_ms"] = round(1000 * (time.perf_counter() - t0) / max(1, done), 1)
    return out


def cost(res: dict) -> dict[str, float]:
    video_s = res.get("video_s") or 0
    if not video_s:
        return {}
    per_game_s = res["wall_s"] * 3600 / video_s  # 60 minutes of video
    out = {"wall_per_game_min": round(per_game_s / 60, 1)}
    for k, usd_h in PRICE_USD_H.items():
        out[f"usd_per_game_{k}"] = round(per_game_s / 3600 * usd_h, 2)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video", type=Path, help="product proxy (1280 px, 25 fps)")
    ap.add_argument("--models", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--variants", default="")
    ap.add_argument("--no-bench", action="store_true")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    allv = variants(a.models)
    names = [v for v in a.variants.split(",") if v] or list(allv)
    if not a.no_bench and not (a.out / "bench_nets.json").exists():
        b = bench_nets(a.video, a.models)
        (a.out / "bench_nets.json").write_text(json.dumps(b, indent=1))
        print("bench", b, flush=True)
    for name in names:
        dst = a.out / f"{name}.json"
        if dst.exists():
            print("done before:", name, flush=True)
            continue
        print("run", name, allv[name], flush=True)
        res = run_once(a.video, a.models, a.out / "work" / name, allv[name])
        res["cost"] = cost(res)
        dst.write_text(json.dumps(res, indent=1, default=str))  # last: counts as done
        print(name, res["wall_s"], "s", res["cost"], res.get("timings_s"), flush=True)
    summary = {}
    for name in allv:  # every variant finished so far, also from earlier calls
        p = a.out / f"{name}.json"
        if p.exists():
            r = json.loads(p.read_text())
            summary[name] = {"wall_s": r["wall_s"], "timings_s": r["timings_s"], **r["cost"]}
    (a.out / "summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
