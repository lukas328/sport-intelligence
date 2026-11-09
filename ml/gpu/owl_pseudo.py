"""OWLv2 ball pseudo-labels on Modal for segment batches (same code as the Kaggle kernel,
ml/ball/kaggle/owl_gpu.py): 5-frame bursts every 6 s per segment, boxes per frame. The result goes
to Kaggle as handball-gpu-owl-<date> (bench_owl.json, segs/*.json).

usage: modal run --detach ml/gpu/owl_pseudo.py --datasets handball-segs-l01,handball-segs-l02
       [--gpu L4] [--budget-h 10] [--bench] [--resume-from handball-gpu-owl-20261105-1449]

--resume-from continues an earlier run: its segs/*.json are copied into the new result first (from
the Modal volume, else from its Kaggle dataset), and owl_gpu.py skips every segment that already has
one. The new dataset then holds the earlier and the new segments together.

Cost: measured about 210 s per segment on a T4 (2026-11-05, 30 bursts per segment), so 100
segments are about 6 h, roughly 3.5 to 4 USD on Modal. An L4 should be faster, not yet measured.
"""

from __future__ import annotations

import datetime as dt

import modal

from common import REPO, base_image, kaggle_download, kaggle_publish, kaggle_secret

app = modal.App("handball-owl")
# Results are also kept on this volume, so a failed Kaggle upload after hours of GPU loses nothing:
# modal volume get handball-gpu-out <slug> .
out_vol = modal.Volume.from_name("handball-gpu-out", create_if_missing=True)
image = base_image.add_local_python_source("common").add_local_file(
    str(REPO / "ml/ball/kaggle/owl_gpu.py"), "/root/owl_gpu.py"
)


def _seed_from(prev: str, out) -> int:
    """Copy the segs/*.json of an earlier run into out/segs; returns how many were copied."""
    import shutil
    from pathlib import Path

    src = Path("/vol") / prev / "segs"
    if not src.is_dir():
        # not on the volume (older run or volume cleared): take the published Kaggle dataset
        tmp = Path("/tmp/prev")
        kaggle_download([prev], tmp)
        found = list(tmp.rglob("segs"))
        if not found:
            raise RuntimeError(f"{prev}: no segs/ folder on the volume or on Kaggle")
        src = found[0]
    dst = out / "segs"
    dst.mkdir(parents=True, exist_ok=True)
    n = 0
    for f in src.glob("*.json"):
        if not (dst / f.name).exists():
            shutil.copy2(f, dst / f.name)
            n += 1
    return n


def _run(datasets: str, budget_h: float, bench: bool, slug: str, resume_from: str) -> str:
    import os
    import subprocess
    from pathlib import Path

    inp, out = Path("/tmp/in"), Path("/vol") / slug
    if resume_from:
        print(f"resume from {resume_from}: {_seed_from(resume_from, out)} segments taken over",
              flush=True)
    names = [d for d in datasets.split(",") if d] + (["handball-ball-bench"] if bench else [])
    kaggle_download(names, inp)
    env = {**os.environ, "OWL_INPUT": str(inp), "OWL_OUT": str(out), "OWL_BUDGET_H": str(budget_h)}
    try:
        subprocess.run(["python", "/root/owl_gpu.py"], check=True, env=env)
    finally:
        out_vol.commit()
    return kaggle_publish(out, slug)


@app.function(gpu="T4", image=image, secrets=[kaggle_secret], timeout=24 * 3600,
              volumes={"/vol": out_vol})
def run_t4(datasets: str, budget_h: float, bench: bool, slug: str, resume_from: str = "") -> str:
    return _run(datasets, budget_h, bench, slug, resume_from)


@app.function(gpu="L4", image=image, secrets=[kaggle_secret], timeout=24 * 3600,
              volumes={"/vol": out_vol})
def run_l4(datasets: str, budget_h: float, bench: bool, slug: str, resume_from: str = "") -> str:
    return _run(datasets, budget_h, bench, slug, resume_from)


@app.local_entrypoint()
def main(datasets: str, gpu: str = "T4", budget_h: float = 10.0, bench: bool = False,
         resume_from: str = "") -> None:
    slug = f"handball-gpu-owl-{dt.datetime.now(dt.timezone.utc):%Y%m%d-%H%M}"
    fn = run_l4 if gpu.upper() == "L4" else run_t4
    print("result dataset:", fn.remote(datasets, budget_h, bench, slug, resume_from))
