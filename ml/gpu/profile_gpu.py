"""Runtime and cost of the product analysis on a GPU (docs/plans/produkt-analyse-integration.md
steps 3 and 4), as a Modal job for the owner's local session (ml/gpu/JOBS.md).

Runs `ml/integration/profile_variants.py` (the product's `run_analysis` with local stand-ins for
S3 and the API, several settings, plus a ball-net micro-benchmark) on one T4, on MINUTES of a real
game (default 5: segments of AT_Cup_Feldkirch_Bregenz_2021 from handball-segs-l10, the game of the
CPU profile). The product code (packages/vision, packages/jobkit, packages/court,
apps/gpu-worker) is copied into the image as it is in the repo; ONNX Runtime with CUDA as in
Dockerfile.cuda. The ball nets are exported to ONNX in the container from the Kaggle dataset
handball-ball-hrmodels (`ml/ball/export_onnx.py`, checkpoints with weights_only=True).

TEST PHASE: hr1 and hrp1 contain DeepSport data (non-commercial); this measures cost only.

Resumable: each finished variant is written to the volume handball-gpu-out under the slug and
skipped on a restart; the same command continues. At the end everything goes to Kaggle as
handball-gpu-profile-<tag> (summary.json, one json per variant, bench_nets.json).

Cost estimate (5 min of video, 5 variants): the CPU chain takes 4.4 x video length on 4 cores; on
a T4 with the detection on the GPU we expect about 1 to 2 x per variant without the ball nets and
up to 3 x with both nets on every frame (two HRNets at 1280 x 704). Together about 1 h on a T4
including setup: about 0.70 USD on Modal. --budget-min stops before a variant that would exceed it.

usage: modal run --detach ml/gpu/profile_gpu.py [--minutes 5] [--tag game1] [--variants ...]
"""

from __future__ import annotations

import modal

from common import REPO, kaggle_download, kaggle_publish, kaggle_secret

app = modal.App("handball-profile")
out_vol = modal.Volume.from_name("handball-gpu-out", create_if_missing=True)

YOLOX_URL = "https://github.com/Megvii-BaseDetection/YOLOX/releases/download/0.1.1rc0/yolox_s.onnx"
YOLOX_SHA = "c5c2d13e59ae883e6af3b45daea64af4833a4951c92d116ec270d9ddbe998063"
OCR_SHA = {
    "ch_PP-OCRv4_det_infer.onnx": "d2a7720d45a54257208b1e13e36a8479894cb74155a5efe29462512d42f49da9",
    "ch_PP-OCRv4_rec_infer.onnx": "48fc40f24f6d2a207a2b1091d3437eb3cc3eb6b676dc3ef9c37384005483683b",
}
GAME = "AT_Cup_Feldkirch_Bregenz_2021"

image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("ffmpeg", "tesseract-ocr", "libgl1", "libglib2.0-0", "curl")
    .pip_install(
        # product dependencies (packages/*/pyproject.toml, apps/gpu-worker/pyproject.toml)
        "numpy>=2.1", "opencv-python-headless>=4.10,<5", "scipy>=1.14", "pyarrow>=18", "av>=14",
        "httpx>=0.28", "boto3>=1.36", "structlog>=24.4", "pydantic-settings>=2.7", "rq>=2.1",
        "redis>=5.2",
        # ONNX Runtime with CUDA 12 as in Dockerfile.cuda (with the CUDA and cuDNN wheels)
        "onnxruntime-gpu[cuda,cudnn]>=1.20,<1.24",
        # export of the ball nets inside the container, on the CPU
        "torch==2.5.1", "timm==1.0.11", "onnx==1.17.0", "onnxconverter-common==1.14.0",
        "kaggle==2.2.5", "kagglesdk==0.1.38", "six",
    )
    .run_commands(
        "mkdir -p /models && curl -LsSf -o /models/yolox_s.onnx " + YOLOX_URL,
        f"echo '{YOLOX_SHA}  /models/yolox_s.onnx' | sha256sum -c -",
        "pip download --no-deps -d /tmp/w rapidocr_onnxruntime==1.4.4 && python -c \"import zipfile,glob;"
        " z=zipfile.ZipFile(glob.glob('/tmp/w/*.whl')[0]); [open('/models/'+n.split('/')[-1],'wb')"
        ".write(z.read(n)) for n in z.namelist() if n.endswith(('_PP-OCRv4_det_infer.onnx',"
        "'_PP-OCRv4_rec_infer.onnx'))]\" && rm -rf /tmp/w",
        *[f"echo '{sha}  /models/{name}' | sha256sum -c -" for name, sha in OCR_SHA.items()],
    )
    .env({"PYTHONPATH": "/src/vision:/src/jobkit:/src/court:/src/gpu-worker:/src/ml/integration:/src/ml/ball"})
    .add_local_python_source("common")
    .add_local_dir(str(REPO / "packages/vision/handball_vision"), "/src/vision/handball_vision")
    .add_local_dir(str(REPO / "packages/jobkit/handball_jobkit"), "/src/jobkit/handball_jobkit")
    .add_local_dir(str(REPO / "packages/court/handball_court"), "/src/court/handball_court")
    .add_local_dir(str(REPO / "packages/court/generated"), "/src/court/generated")
    .add_local_dir(str(REPO / "apps/gpu-worker/src/handball_gpu_worker"), "/src/gpu-worker/handball_gpu_worker")
    .add_local_dir(str(REPO / "ml/integration"), "/src/ml/integration")
    .add_local_dir(str(REPO / "ml/ball"), "/src/ml/ball", ignore=["**/*.pt", "**/*.zip", "**/__pycache__"])
)


def _run(minutes: int, slug: str, variants: str, budget_min: int) -> str:
    import json
    import shutil
    import subprocess
    import time
    from pathlib import Path

    t_start = time.time()
    out = Path("/vol") / slug
    out.mkdir(parents=True, exist_ok=True)
    work, models = Path("/tmp/work"), Path("/tmp/models")
    models.mkdir(parents=True, exist_ok=True)
    for f in Path("/models").iterdir():
        shutil.copy2(f, models / f.name)
    inp = Path("/tmp/in")
    kaggle_download(["handball-ball-hrmodels"], inp)
    for net, kind in (("hr1", "hr"), ("hrp1", "hrp")):
        pt = next(inp.rglob(f"ball_{net}.pt"))
        subprocess.run(
            ["python", "/src/ml/ball/export_onnx.py", str(pt), kind, str(models / f"ball_{net}.onnx"), "--fp16"],
            check=True,
        )
    proxy = out / "proxy.mp4"
    if not proxy.exists():
        segs = inp / "segs"
        segs.mkdir(parents=True, exist_ok=True)
        n = max(1, -(-minutes // 3))  # 3-minute segments
        from kaggle.api.kaggle_api_extended import KaggleApi

        api = KaggleApi()
        api.authenticate()
        for s in range(n):
            api.dataset_download_file("lukasde1000/handball-segs-l10", f"{GAME}_s{s}.mp4", path=str(segs), quiet=True)
        files = sorted(segs.glob(f"{GAME}_s*.mp4"))
        lst = segs / "list.txt"
        lst.write_text("".join(f"file '{f}'\n" for f in files))
        joined = segs / "joined.mp4"
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
                        "-t", str(minutes * 60), "-c", "copy", str(joined)], check=True)
        from profile_analysis import _proxy_cmd

        t0 = time.time()
        subprocess.run(_proxy_cmd(joined, proxy.with_suffix(".part.mp4")), check=True)
        proxy.with_suffix(".part.mp4").rename(proxy)
        (out / "proxy_s.txt").write_text(f"{time.time() - t0:.1f}")
        out_vol.commit()
    names = [v for v in variants.split(",") if v]
    for name in names:
        if (out / f"{name}.json").exists():
            continue
        used = (time.time() - t_start) / 60
        if used > budget_min:
            print(f"budget: {used:.0f} of {budget_min} min used, stopping before {name}", flush=True)
            break
        subprocess.run(
            ["python", "/src/ml/integration/profile_variants.py", str(proxy), "--models", str(models),
             "--out", str(out), "--variants", name],
            check=True,
            cwd=str(work.parent),
        )
        out_vol.commit()
    shutil.rmtree(out / "work", ignore_errors=True)
    pub = Path("/tmp/pub")
    shutil.copytree(out, pub, ignore=shutil.ignore_patterns("*.mp4", "work"), dirs_exist_ok=True)
    print(json.dumps(json.loads((out / "summary.json").read_text()) if (out / "summary.json").exists() else {}, indent=1))
    return kaggle_publish(pub, slug)


@app.function(gpu="T4", image=image, secrets=[kaggle_secret], timeout=4 * 3600, volumes={"/vol": out_vol})
def run_t4(minutes: int, slug: str, variants: str, budget_min: int) -> str:
    return _run(minutes, slug, variants, budget_min)


@app.local_entrypoint()
def main(
    minutes: int = 5,
    tag: str = "game1",
    variants: str = "cuda_image,cuda_ball_ens,cuda_ball_hrp1,cuda_ball_ens_lean,cpu_image",
    budget_min: int = 90,
) -> None:
    slug = f"handball-gpu-profile-{tag}"
    print("result dataset:", run_t4.remote(minutes, slug, variants, budget_min))
