"""Cheaper ball net on a T4 (job 14 in ml/gpu/JOBS.md, docs/plans/produkt-analyse-integration.md,
GPU profile T4), as a Modal job for the owner's local session.

Job 13 measured the ball net at 80 to 120 ms per frame on a T4 plus 21 ms of CPU preparation, and
batching gave nothing: with hrp1 on every frame a 60-minute game costs about 3 USD. This job looks
for the cheaper way, in two parts:
1. `ml/integration/bench_ballnet.py`: hrp1 alone on 120 real triplets, at 1280 and 960 px: the
   product as it is, uint8 input with the preprocessing in the graph (`ml/ball/onnx_u8.py`), the
   same with IO binding, and TensorRT fp16 (uint8 and float input; engine cached on the volume).
   Each with ms per frame (CPU preparation, net, total) and whether the strongest candidate stays.
2. `ml/integration/profile_variants.py`: the full product job on MINUTES of the game of job 13 with
   YOLOX on every 3rd frame and number budget 0.3, without ball net (cuda_lean) and with hrp1 on
   every frame (cuda_lean_hrp1).

TEST PHASE: hrp1 contains DeepSport data (non-commercial); this measures cost only.

Resumable: results go to the volume handball-gpu-out under the slug after every variant; the same
command continues. Stops by itself: no new step after --budget-min (default 25) and Modal ends the
function after 30 minutes in any case (what is done stays on the volume). Results: Kaggle dataset
handball-gpu-bench-<tag> (bench.json, bench_summary.json, one json per pipeline variant).

Cost estimate: image build once (CPU), then on the T4 about 3 min setup (Kaggle, export), up to
10 min TensorRT engine build (once, cached), 3 min micro-benchmark, about 8 min for the two
pipeline variants on 3 minutes of video: about 25 min, 0.30 USD; at most 30 min, 0.35 USD.

usage: modal run --detach ml/gpu/bench_ballnet_gpu.py [--minutes 3] [--tag ballnet]
"""

from __future__ import annotations

import modal

from common import REPO, kaggle_download, kaggle_publish, kaggle_secret

app = modal.App("handball-bench-ballnet")
out_vol = modal.Volume.from_name("handball-gpu-out", create_if_missing=True)

YOLOX_URL = "https://github.com/Megvii-BaseDetection/YOLOX/releases/download/0.1.1rc0/yolox_s.onnx"
YOLOX_SHA = "c5c2d13e59ae883e6af3b45daea64af4833a4951c92d116ec270d9ddbe998063"
OCR_SHA = {
    "ch_PP-OCRv4_det_infer.onnx": "d2a7720d45a54257208b1e13e36a8479894cb74155a5efe29462512d42f49da9",
    "ch_PP-OCRv4_rec_infer.onnx": "48fc40f24f6d2a207a2b1091d3437eb3cc3eb6b676dc3ef9c37384005483683b",
}
GAME = "AT_Cup_Feldkirch_Bregenz_2021"
PROXY_13 = "handball-gpu-profile-game1/proxy.mp4"  # the proxy of job 13, if it is still there
SITE = "/usr/local/lib/python3.12/site-packages"
TIMEOUT_MIN = 30

image = (
    # CUDA 12.6 and cuDNN 9 as system libraries, as Dockerfile.cuda (on debian_slim ONNX Runtime fell
    # back to the CPU in the first run of job 13); TensorRT 10 from its pip wheel for the TensorRT
    # execution provider (ONNX Runtime 1.22 is built against TensorRT 10.9).
    modal.Image.from_registry("nvidia/cuda:12.6.3-cudnn-runtime-ubuntu24.04", add_python="3.12")
    .apt_install("ffmpeg", "libgl1", "libglib2.0-0", "curl")
    .pip_install("torch==2.5.1", index_url="https://download.pytorch.org/whl/cpu")
    .pip_install(
        "numpy>=2.1", "opencv-python-headless>=4.10,<5", "scipy>=1.14", "pyarrow>=18", "av>=14",
        "httpx>=0.28", "boto3>=1.36", "structlog>=24.4", "pydantic-settings>=2.7", "rq>=2.1",
        "redis>=5.2",
        "onnxruntime-gpu==1.22.0", "tensorrt-cu12-libs==10.9.0.34",
        "timm==1.0.11", "onnx==1.17.0", "onnxconverter-common==1.16.0",
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
    .env({
        "PYTHONPATH": "/src/vision:/src/jobkit:/src/court:/src/gpu-worker:/src/ml/integration:/src/ml/ball",
        "LD_LIBRARY_PATH": f"{SITE}/tensorrt_libs",
    })
    .add_local_python_source("common")
    .add_local_dir(str(REPO / "packages/vision/handball_vision"), "/src/vision/handball_vision")
    .add_local_dir(str(REPO / "packages/jobkit/handball_jobkit"), "/src/jobkit/handball_jobkit")
    .add_local_dir(str(REPO / "packages/court/handball_court"), "/src/court/handball_court")
    .add_local_dir(str(REPO / "packages/court/generated"), "/src/court/generated")
    .add_local_dir(str(REPO / "apps/gpu-worker/src/handball_gpu_worker"), "/src/gpu-worker/handball_gpu_worker")
    .add_local_dir(str(REPO / "ml/integration"), "/src/ml/integration")
    .add_local_dir(str(REPO / "ml/ball"), "/src/ml/ball", ignore=["**/*.pt", "**/*.zip", "**/__pycache__"])
)


def _check_gpu(model: str) -> list[str]:
    """Fail unless ONNX Runtime really runs on the GPU (it silently falls back to the CPU); report
    whether the TensorRT provider is there (its variants then record an error, the rest goes on)."""
    import onnxruntime as ort

    sess = ort.InferenceSession(model, providers=["CUDAExecutionProvider", "CPUExecutionProvider"])
    got = sess.get_providers()
    print("onnxruntime", ort.__version__, "available", ort.get_available_providers(), "session", got,
          flush=True)
    if got[0] != "CUDAExecutionProvider":
        raise RuntimeError(f"ONNX Runtime is not on the GPU: {got}")
    return ort.get_available_providers()


def _proxy(out, minutes: int):
    """MINUTES of the job 13 game as a product proxy: cut from job 13's proxy on the volume, or
    built from handball-segs-l10 as there."""
    import subprocess
    from pathlib import Path

    proxy = out / "proxy.mp4"
    if proxy.exists():
        return proxy
    src = Path("/vol") / PROXY_13
    if not src.exists():
        segs = Path("/tmp/in/segs")
        segs.mkdir(parents=True, exist_ok=True)
        from kaggle.api.kaggle_api_extended import KaggleApi

        api = KaggleApi()
        api.authenticate()
        for s in range(max(1, -(-minutes // 3))):  # 3-minute segments
            api.dataset_download_file("lukasde1000/handball-segs-l10", f"{GAME}_s{s}.mp4", path=str(segs), quiet=True)
        files = sorted(segs.glob(f"{GAME}_s*.mp4"))
        (segs / "list.txt").write_text("".join(f"file '{f}'\n" for f in files))
        joined = segs / "joined.mp4"
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i",
                        str(segs / "list.txt"), "-c", "copy", str(joined)], check=True)
        from profile_analysis import _proxy_cmd

        src = segs / "proxy_full.mp4"
        subprocess.run(_proxy_cmd(joined, src), check=True)
    part = out / "proxy.part.mp4"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(src), "-t", str(minutes * 60),
                    "-c", "copy", str(part)], check=True)
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
    # hard deadline for running steps: Modal kills the function at TIMEOUT_MIN, and the Kaggle upload
    # only happens at the end, so a step still running then would lose everything; 2.5 min stay for it
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
    pt = next(inp.rglob("ball_hrp1.pt"))
    hrp1 = models / "ball_hrp1.onnx"
    subprocess.run(["python", "/src/ml/ball/export_onnx.py", str(pt), "hrp", str(hrp1), "--fp16"], check=True)
    fp16 = models / "ball_hrp1_fp16.onnx"
    for src, dst in ((fp16, models / "ball_hrp1_fp16_u8.onnx"), (hrp1, models / "ball_hrp1_u8.onnx")):
        subprocess.run(["python", "/src/ml/ball/onnx_u8.py", str(src), str(dst), "--check"], check=True)
    proxy = _proxy(out, minutes)
    print(f"setup {time.time() - t_start:.0f} s", flush=True)

    # 1. ball net alone; the TensorRT engines are cached on the volume for a restart
    try:
        subprocess.run(
            ["python", "/src/ml/integration/bench_ballnet.py", str(proxy),
             "--f32", str(fp16), "--u8", str(models / "ball_hrp1_fp16_u8.onnx"),
             "--trt-u8", str(models / "ball_hrp1_u8.onnx"), "--trt-f32", str(hrp1),
             "--out", str(out), "--cache", str(out / "trt-cache"), "--stop-at", str(stop_at)],
            check=False, timeout=max(1.0, hard_at - time.time()),
        )
    except subprocess.TimeoutExpired:
        print("hard deadline: bench stopped", flush=True)
    out_vol.commit()

    # 2. the full job with the lean settings
    for name in [v for v in variants.split(",") if v]:
        if (out / f"{name}.json").exists():
            continue
        if time.time() > stop_at:
            print(f"budget: {budget_min} min used, stopping before {name}", flush=True)
            break
        try:
            subprocess.run(
                ["python", "/src/ml/integration/profile_variants.py", str(proxy), "--models", str(models),
                 "--out", str(out), "--variants", name, "--no-bench"],
                check=True, timeout=max(1.0, hard_at - time.time()),
            )
        except subprocess.TimeoutExpired:
            print(f"hard deadline: {name} stopped, not finished", flush=True)
            break
        out_vol.commit()
    shutil.rmtree(out / "work", ignore_errors=True)
    pub = Path("/tmp/pub")
    shutil.copytree(out, pub, ignore=shutil.ignore_patterns("*.mp4", "work", "trt-cache"), dirs_exist_ok=True)
    for f in ("bench_summary.json", "summary.json"):
        if (out / f).exists():
            print(f, (out / f).read_text(), flush=True)
    print(json.dumps({"minutes_used": round((time.time() - t_start) / 60, 1)}), flush=True)
    return kaggle_publish(pub, slug)


@app.function(gpu="T4", image=image, secrets=[kaggle_secret], timeout=TIMEOUT_MIN * 60,
              volumes={"/vol": out_vol})
def run_t4(minutes: int, slug: str, budget_min: int, variants: str) -> str:
    return _run(minutes, slug, budget_min, variants)


@app.local_entrypoint()
def main(minutes: int = 3, tag: str = "ballnet", budget_min: int = 25,
         variants: str = "cuda_lean,cuda_lean_hrp1") -> None:
    slug = f"handball-gpu-bench-{tag}"
    print("result dataset:", run_t4.remote(minutes, slug, min(budget_min, TIMEOUT_MIN - 3), variants))
