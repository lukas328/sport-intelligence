"""Ball net with uint8 input on its worker thread, inside the full product job on a T4 (job 15 in
ml/gpu/JOBS.md, docs/plans/produkt-analyse-integration.md, GPU profile T4), as a Modal job for the
owner's local session.

Job 14: the ball net alone takes 62 ms per frame at 1280 px with the uint8 input (42 at 960); in
the job it cost 122 ms per frame because it ran in turn with camera motion, detection and shirt
numbers (182 s per 180 s of video without the net). Since PR #67 the net runs on a worker thread.
At best the job then takes max(net, rest) instead of the sum: about 1.55 x video length and
1.02 USD per game at 1280 px on every frame. This job measures it with `ml/integration/
profile_variants.py` (the product's `run_analysis`) on MINUTES of the game of jobs 13 and 14:
lean_u8_1280_e1, lean_u8_960_e1, lean_u8_1280_e2, lean_u8_960_e2, cuda_lean (no net, the rest),
lean_ens_u8_1280_e1 (hr1 + hrp1) last, if the time allows. All with YOLOX on every 3rd frame and
number budget 0.3.

TEST PHASE: hr1 and hrp1 contain DeepSport data (non-commercial); this measures cost only.

Resumable: every finished variant is on the volume handball-gpu-out under the slug; the same call
continues. Stops: no new variant after --budget-min (default 25); a running variant is stopped
2.5 min before Modal's hard end at 30 min, so the Kaggle upload of what is done always happens.
Result: Kaggle dataset handball-gpu-lean-<tag> (summary.json, one json per variant).

Cost estimate (2 min of video): setup about 4 min (Kaggle, export of hr1 and hrp1), the variants
together about 18 min: about 22 min on a T4, 0.25 USD; at most 30 min, 0.33 USD.

usage: modal deploy ml/gpu/profile_lean_gpu.py, then
modal.Function.from_name("handball-profile-lean", "run_t4").spawn(2, "handball-gpu-lean-u8", 25, VARIANTS)
or: modal run --detach ml/gpu/profile_lean_gpu.py
"""

from __future__ import annotations

import modal
from common import REPO, kaggle_download, kaggle_publish, kaggle_secret

app = modal.App("handball-profile-lean")
out_vol = modal.Volume.from_name("handball-gpu-out", create_if_missing=True)

YOLOX_URL = "https://github.com/Megvii-BaseDetection/YOLOX/releases/download/0.1.1rc0/yolox_s.onnx"
YOLOX_SHA = "c5c2d13e59ae883e6af3b45daea64af4833a4951c92d116ec270d9ddbe998063"
OCR_SHA = {
    "ch_PP-OCRv4_det_infer.onnx": "d2a7720d45a54257208b1e13e36a8479894cb74155a5efe29462512d42f49da9",
    "ch_PP-OCRv4_rec_infer.onnx": "48fc40f24f6d2a207a2b1091d3437eb3cc3eb6b676dc3ef9c37384005483683b",
}
GAME = "AT_Cup_Feldkirch_Bregenz_2021"
# proxies of jobs 14 and 13 on the volume (3 and 5 min of the game), cut to MINUTES
PROXIES = ("handball-gpu-bench-ballnet/proxy.mp4", "handball-gpu-profile-game1/proxy.mp4")
TIMEOUT_MIN = 30
VARIANTS = (
    "lean_u8_1280_e1,lean_u8_960_e1,lean_u8_1280_e2,lean_u8_960_e2,cuda_lean,lean_ens_u8_1280_e1"
)

image = (
    # CUDA 12.6 and cuDNN 9 as system libraries, as Dockerfile.cuda and job 14
    modal.Image.from_registry("nvidia/cuda:12.6.3-cudnn-runtime-ubuntu24.04", add_python="3.12")
    .apt_install("ffmpeg", "libgl1", "libglib2.0-0", "curl")
    .pip_install("torch==2.5.1", index_url="https://download.pytorch.org/whl/cpu")
    .pip_install(
        "numpy>=2.1",
        "opencv-python-headless>=4.10,<5",
        "scipy>=1.14",
        "pyarrow>=18",
        "av>=14",
        "httpx>=0.28",
        "boto3>=1.36",
        "structlog>=24.4",
        "pydantic-settings>=2.7",
        "rq>=2.1",
        "redis>=5.2",
        "onnxruntime-gpu==1.22.0",
        "timm==1.0.11",
        "onnx==1.17.0",
        "onnxconverter-common==1.16.0",
        "kaggle==2.2.5",
        "kagglesdk==0.1.38",
        "six",
    )
    .run_commands(
        "mkdir -p /models && curl -LsSf -o /models/yolox_s.onnx " + YOLOX_URL,
        f"echo '{YOLOX_SHA}  /models/yolox_s.onnx' | sha256sum -c -",
        'pip download --no-deps -d /tmp/w rapidocr_onnxruntime==1.4.4 && python -c "import zipfile,glob;'
        " z=zipfile.ZipFile(glob.glob('/tmp/w/*.whl')[0]); [open('/models/'+n.split('/')[-1],'wb')"
        ".write(z.read(n)) for n in z.namelist() if n.endswith(('_PP-OCRv4_det_infer.onnx',"
        "'_PP-OCRv4_rec_infer.onnx'))]\" && rm -rf /tmp/w",
        *[f"echo '{sha}  /models/{name}' | sha256sum -c -" for name, sha in OCR_SHA.items()],
    )
    .env(
        {
            "PYTHONPATH": "/src/vision:/src/jobkit:/src/court:/src/gpu-worker:/src/ml/integration:/src/ml/ball"
        }
    )
    .add_local_python_source("common")
    .add_local_dir(str(REPO / "packages/vision/handball_vision"), "/src/vision/handball_vision")
    .add_local_dir(str(REPO / "packages/jobkit/handball_jobkit"), "/src/jobkit/handball_jobkit")
    .add_local_dir(str(REPO / "packages/court/handball_court"), "/src/court/handball_court")
    .add_local_dir(str(REPO / "packages/court/generated"), "/src/court/generated")
    .add_local_dir(
        str(REPO / "apps/gpu-worker/src/handball_gpu_worker"), "/src/gpu-worker/handball_gpu_worker"
    )
    .add_local_dir(str(REPO / "ml/integration"), "/src/ml/integration")
    .add_local_dir(
        str(REPO / "ml/ball"), "/src/ml/ball", ignore=["**/*.pt", "**/*.zip", "**/__pycache__"]
    )
)


def _check_gpu(model: str) -> None:
    """Fail unless ONNX Runtime really runs on the GPU (it silently falls back to the CPU)."""
    import onnxruntime as ort

    sess = ort.InferenceSession(model, providers=["CUDAExecutionProvider", "CPUExecutionProvider"])
    got = sess.get_providers()
    print("onnxruntime", ort.__version__, "session", got, flush=True)
    if got[0] != "CUDAExecutionProvider":
        raise RuntimeError(f"ONNX Runtime is not on the GPU: {got}")


def _proxy(out, minutes: int):
    """MINUTES of the game of jobs 13 and 14 as a product proxy, cut from their proxy on the volume
    (built from handball-segs-l10 as in job 13 when neither is there)."""
    import subprocess
    from pathlib import Path

    proxy = out / "proxy.mp4"
    if proxy.exists():
        return proxy
    src = next((Path("/vol") / p for p in PROXIES if (Path("/vol") / p).exists()), None)
    if src is None:
        segs = Path("/tmp/in/segs")
        segs.mkdir(parents=True, exist_ok=True)
        from kaggle.api.kaggle_api_extended import KaggleApi

        api = KaggleApi()
        api.authenticate()
        api.dataset_download_file(
            "lukasde1000/handball-segs-l10", f"{GAME}_s0.mp4", path=str(segs), quiet=True
        )
        from profile_analysis import _proxy_cmd

        src = segs / "proxy_full.mp4"
        subprocess.run(_proxy_cmd(segs / f"{GAME}_s0.mp4", src), check=True)
    part = out / "proxy.part.mp4"
    cut = ["ffmpeg", "-loglevel", "error", "-y", "-i", str(src), "-t", str(minutes * 60)]
    subprocess.run([*cut, "-c", "copy", str(part)], check=True)
    part.rename(proxy)
    out_vol.commit()
    return proxy


def _run(minutes: int, slug: str, budget_min: int, variants: str) -> str:
    import json
    import shutil
    import subprocess
    import time
    from pathlib import Path

    t_start = time.time()
    stop_at = t_start + budget_min * 60
    # Modal ends the function at TIMEOUT_MIN; the upload comes last, so a running variant is
    # stopped 2.5 min before (what is done stays on the volume and is published)
    hard_at = t_start + (TIMEOUT_MIN - 2.5) * 60
    out = Path("/vol") / slug
    out.mkdir(parents=True, exist_ok=True)
    models = Path("/tmp/models")
    models.mkdir(parents=True, exist_ok=True)
    for f in Path("/models").iterdir():
        shutil.copy2(f, models / f.name)
    _check_gpu(str(models / "yolox_s.onnx"))
    inp = Path("/tmp/in")
    kaggle_download(["handball-ball-hrmodels"], inp)
    for net, kind in (("hrp1", "hrp"), ("hr1", "hr")):
        pt = next(inp.rglob(f"ball_{net}.pt"))
        onnx_path = models / f"ball_{net}.onnx"
        export = ["python", "/src/ml/ball/export_onnx.py", str(pt), kind, str(onnx_path), "--fp16"]
        subprocess.run(export, check=True)
        fp16 = models / f"ball_{net}_fp16.onnx"
        u8 = models / f"ball_{net}_fp16_u8.onnx"
        subprocess.run(["python", "/src/ml/ball/onnx_u8.py", str(fp16), str(u8), "--check"], check=True)
    proxy = _proxy(out, minutes)
    print(f"setup {time.time() - t_start:.0f} s", flush=True)
    for name in [v for v in variants.split(",") if v]:
        if (out / f"{name}.json").exists():
            continue
        if time.time() > stop_at:
            print(f"budget: {budget_min} min used, stopping before {name}", flush=True)
            break
        cmd = ["python", "/src/ml/integration/profile_variants.py", str(proxy)]
        cmd += ["--models", str(models), "--out", str(out), "--variants", name, "--no-bench"]
        try:
            subprocess.run(cmd, check=True, timeout=max(1.0, hard_at - time.time()))
        except subprocess.TimeoutExpired:
            print(f"hard deadline: {name} stopped, not finished", flush=True)
            break
        out_vol.commit()
    shutil.rmtree(out / "work", ignore_errors=True)
    pub = Path("/tmp/pub")
    shutil.copytree(out, pub, ignore=shutil.ignore_patterns("*.mp4", "work"), dirs_exist_ok=True)
    if (out / "summary.json").exists():
        print((out / "summary.json").read_text(), flush=True)
    print(json.dumps({"minutes_used": round((time.time() - t_start) / 60, 1)}), flush=True)
    return kaggle_publish(pub, slug)


@app.function(
    gpu="T4",
    image=image,
    secrets=[kaggle_secret],
    timeout=TIMEOUT_MIN * 60,
    volumes={"/vol": out_vol},
)
def run_t4(minutes: int, slug: str, budget_min: int, variants: str) -> str:
    return _run(minutes, slug, budget_min, variants)


@app.local_entrypoint()
def main(minutes: int = 2, tag: str = "u8", budget_min: int = 25, variants: str = VARIANTS) -> None:
    slug = f"handball-gpu-lean-{tag}"
    print("result dataset:", run_t4.remote(minutes, slug, min(budget_min, TIMEOUT_MIN - 3), variants))
