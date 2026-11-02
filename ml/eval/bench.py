"""Benchmark (BRIEF 6.3 point 7): time and throughput per pipeline stage on a synthetic clip.

    uv run python ml/eval/bench.py [--seconds 120]

Reports seconds per stage, frames per second and the projected time for a 60-minute match.
Budget: 60 min video in <= 45 min on one L4-class GPU; here measured on the CPU of this machine.
"""

from __future__ import annotations

import argparse
import os
import platform
import tempfile
import time
from pathlib import Path

from handball_vision.pipeline import analyse_video
from handball_vision.synthetic import SyntheticConfig, SyntheticMatch


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=120)
    args = ap.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        m = SyntheticMatch(SyntheticConfig(seconds=args.seconds))
        video = Path(tmp) / "bench.mp4"
        m.write(video)
        k = m.cfg.kits
        t0 = time.perf_counter()
        res = analyse_video(
            video,
            {
                "home": k.home,
                "home_gk": k.home_gk,
                "away": k.away,
                "away_gk": k.away_gk,
                "referee": k.referee,
            },
        )
        total = time.perf_counter() - t0
    print(f"machine: {platform.processor() or platform.machine()}, {os.cpu_count()} cpus, no GPU")
    print(
        f"video: {args.seconds:.0f} s at 25 fps, 1280x720 analysis proxy; detector: {res.detector_source}\n"
    )
    print("| stage | seconds | share |\n|---|---|---|")
    for stage, sec in sorted(res.timings_s.items(), key=lambda kv: -kv[1]):
        print(f"| {stage} | {sec:.2f} | {sec / total:.0%} |")
    print(f"| total | {total:.2f} | 100% |\n")
    print(
        f"throughput: {res.frames / total:.1f} frames/s, realtime factor {total / args.seconds:.2f}"
    )
    print(f"projected for 60 min: {total / args.seconds * 60:.0f} min (budget 45 min)")


if __name__ == "__main__":
    main()
