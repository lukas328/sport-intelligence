"""OWLv2 ball pseudo-labels on Modal for segment batches (same code as the Kaggle kernel,
ml/ball/kaggle/owl_gpu.py): 5-frame bursts every 6 s per segment, boxes per frame. The result goes
to Kaggle as handball-gpu-owl-<date> (one zip: bench_owl.json if bench frames were given, segs/*.json).

usage: modal run ml/gpu/owl_pseudo.py --datasets handball-segs-l01,handball-segs-l02 [--gpu L4]
       [--budget-h 10] [--bench]
Cost: about 2 min per segment on a T4 (0.59 USD/h), so a batch of 20 games (100 segments) is
about 3.5 h, roughly 2 USD; an L4 is faster at a similar cost per segment.
"""

from __future__ import annotations

import datetime as dt

import modal

from common import REPO, base_image, kaggle_download, kaggle_publish, kaggle_secret

app = modal.App("handball-owl")
image = base_image.add_local_python_source("common").add_local_file(
    str(REPO / "ml/ball/kaggle/owl_gpu.py"), "/root/owl_gpu.py"
)


def _run(datasets: str, budget_h: float, bench: bool, slug: str) -> str:
    import os
    import subprocess
    from pathlib import Path

    inp, out = Path("/tmp/in"), Path("/tmp/out")
    names = [d for d in datasets.split(",") if d] + (["handball-ball-bench"] if bench else [])
    kaggle_download(names, inp)
    env = {**os.environ, "OWL_INPUT": str(inp), "OWL_OUT": str(out), "OWL_BUDGET_H": str(budget_h)}
    subprocess.run(["python", "/root/owl_gpu.py"], check=True, env=env)
    return kaggle_publish(out, slug)


@app.function(gpu="T4", image=image, secrets=[kaggle_secret], timeout=24 * 3600)
def run_t4(datasets: str, budget_h: float, bench: bool, slug: str) -> str:
    return _run(datasets, budget_h, bench, slug)


@app.function(gpu="L4", image=image, secrets=[kaggle_secret], timeout=24 * 3600)
def run_l4(datasets: str, budget_h: float, bench: bool, slug: str) -> str:
    return _run(datasets, budget_h, bench, slug)


@app.local_entrypoint()
def main(datasets: str, gpu: str = "T4", budget_h: float = 10.0, bench: bool = False) -> None:
    slug = f"handball-gpu-owl-{dt.datetime.now(dt.timezone.utc):%Y%m%d-%H%M}"
    fn = run_l4 if gpu.upper() == "L4" else run_t4
    print("result dataset:", fn.remote(datasets, budget_h, bench, slug))
