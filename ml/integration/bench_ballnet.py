"""Ball net alone on a GPU: where the 80 to 120 ms per frame of job 13 go and what is cheaper (job 14
in ml/gpu/JOBS.md, docs/plans/produkt-analyse-integration.md, GPU profile T4).

Each variant runs the same real triplets (t-2, t, t+2 of the product proxy) and reports ms per frame
for the CPU preparation, the net, and both together, plus how often its strongest candidate lies
within 2 px of the baseline's (fp16 and TensorRT must not move the ball):
- f32: the product as it is (`handball_vision.ballnet.BallNet`: float32 input built on the CPU);
- u8: the same net with the uint8 input and the preprocessing in the graph (`ml/ball/onnx_u8.py`);
- u8_iobind: u8 with IO binding: input and output buffers on the GPU allocated once;
- trt_u8: u8 graph on the TensorRT execution provider with fp16 (engine cached in --cache);
- trt_f32: float input on TensorRT fp16, in case the uint8 graph does not go to TensorRT.
Widths 1280 (product) and 960 (the CPU test setting). A variant whose result is in OUT/bench.json
already is skipped (resumable); a variant that fails records its error and the others go on.

    python ml/integration/bench_ballnet.py PROXY.mp4 --f32 hrp1_fp16.onnx --u8 hrp1_fp16_u8.onnx \
        --trt-u8 hrp1_u8.onnx --trt-f32 hrp1.onnx --out DIR [--cache DIR] [--n 120]
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ball"))
from onnx_u8 import U8_INPUT


def read_triplets(video: Path, n: int, gap: int = 2) -> list[list[np.ndarray]]:
    cap = cv2.VideoCapture(str(video))
    frames = []
    while len(frames) < n + 2 * gap:
        ok, f = cap.read()
        if not ok:
            break
        frames.append(f)
    cap.release()
    return [[frames[i], frames[i + gap], frames[i + 2 * gap]] for i in range(len(frames) - 2 * gap)]


def prep_u8(trip: list[np.ndarray], width: int) -> np.ndarray:
    """Resize (only below the proxy width), crop to a multiple of 32, join: H,W,9 uint8."""
    out = []
    for f in trip:
        if f.shape[1] != width:
            h = round(f.shape[0] * width / f.shape[1])
            f = cv2.resize(f, (width, h), interpolation=cv2.INTER_AREA)
        out.append(f[: f.shape[0] // 32 * 32])
    return np.concatenate(out, axis=2)


def top(hm: np.ndarray) -> tuple[float, float]:
    y, x = np.unravel_index(int(hm.argmax()), hm.shape)
    return float(x * 4 + 2), float(y * 4 + 2)


def _preload_tensorrt() -> None:
    """Load the TensorRT libraries of the pip wheel (tensorrt-cu12-libs) before ONNX Runtime asks
    for them, in case LD_LIBRARY_PATH does not point there."""
    import ctypes

    try:
        import tensorrt_libs  # type: ignore[import-not-found]
    except ImportError:
        return
    d = Path(tensorrt_libs.__file__).parent
    for lib in sorted(d.glob("libnvinfer*.so.*")) + sorted(d.glob("libnvonnxparser*.so.*")):
        try:
            ctypes.CDLL(str(lib), mode=ctypes.RTLD_GLOBAL)
        except OSError as exc:
            print("tensorrt preload", lib.name, exc, flush=True)


def trt_providers(cache: Path, name: str) -> list:
    _preload_tensorrt()
    cache.mkdir(parents=True, exist_ok=True)
    shapes = {
        "min": f"{name}:1x512x960x9" if name == U8_INPUT else f"{name}:1x9x512x960",
        "max": f"{name}:1x704x1280x9" if name == U8_INPUT else f"{name}:1x9x704x1280",
    }
    return [
        (
            "TensorrtExecutionProvider",
            {
                "trt_fp16_enable": True,
                "trt_engine_cache_enable": True,
                "trt_engine_cache_path": str(cache),
                "trt_timing_cache_enable": True,
                "trt_profile_min_shapes": shapes["min"],
                "trt_profile_opt_shapes": shapes["max"],
                "trt_profile_max_shapes": shapes["max"],
            },
        ),
        "CUDAExecutionProvider",
        "CPUExecutionProvider",
    ]


def run_variant(
    kind: str, model: Path, trips: list[list[np.ndarray]], width: int, cache: Path
) -> dict:
    import onnxruntime as ort

    t_load = time.perf_counter()
    if kind == "f32":
        from handball_vision.ballnet import BallNet

        net = BallNet([model], width=width)
        sess = net.sessions[0]
    else:
        net = None
        name = U8_INPUT if kind != "trt_f32" else "frames"
        providers = (
            trt_providers(cache, name)
            if kind.startswith("trt")
            else ["CUDAExecutionProvider", "CPUExecutionProvider"]
        )
        sess = ort.InferenceSession(str(model), providers=providers)
    in_name = sess.get_inputs()[0].name
    io = None
    if kind == "u8_iobind":
        x0 = prep_u8(trips[0], width)[None]
        x_gpu = ort.OrtValue.ortvalue_from_numpy(x0, "cuda", 0)
        out_shape = [1, 1, x0.shape[1] // 4, x0.shape[2] // 4]
        y_gpu = ort.OrtValue.ortvalue_from_shape_and_type(out_shape, np.float32, "cuda", 0)
        io = sess.io_binding()
        io.bind_ortvalue_input(in_name, x_gpu)
        io.bind_ortvalue_output(sess.get_outputs()[0].name, y_gpu)

    def prepare(trip: list[np.ndarray]) -> np.ndarray:
        if net is not None:
            return net.prepare(trip)[0][None]
        if kind == "trt_f32":
            x = prep_u8(trip, width)
            h, w = x.shape[:2]
            rgb = x.reshape(h, w, 3, 3)[..., ::-1].reshape(h, w, 9)
            return rgb.transpose(2, 0, 1)[None].astype(np.float32)
        return prep_u8(trip, width)[None]

    def infer(x: np.ndarray) -> np.ndarray:
        if io is not None:
            x_gpu.update_inplace(x)
            sess.run_with_iobinding(io)
            return y_gpu.numpy()
        return sess.run(None, {in_name: x})[0]

    first = time.perf_counter()
    infer(prepare(trips[0]))  # TensorRT builds (or loads) its engine here
    first_s = time.perf_counter() - first
    load_s = first - t_load
    for t in trips[1:4]:
        infer(prepare(t))
    prep_t = net_t = 0.0
    tops = []
    for t in trips:
        a = time.perf_counter()
        x = prepare(t)
        b = time.perf_counter()
        hm = infer(x)[0, 0]
        c = time.perf_counter()
        prep_t += b - a
        net_t += c - b
        tops.append(top(hm))
    n = len(trips)
    return {
        "providers": sess.get_providers()[0],
        "load_s": round(load_s, 1),
        "first_run_s": round(first_s, 1),
        "prep_ms": round(1000 * prep_t / n, 1),
        "net_ms": round(1000 * net_t / n, 1),
        "total_ms": round(1000 * (prep_t + net_t) / n, 1),
        "frames": n,
        "_tops": tops,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video", type=Path)
    ap.add_argument("--f32", type=Path, required=True, help="product file (fp16 net, float input)")
    ap.add_argument("--u8", type=Path, help="the same with uint8 input")
    ap.add_argument("--trt-u8", type=Path, help="fp32 net with uint8 input, for TensorRT fp16")
    ap.add_argument("--trt-f32", type=Path, help="fp32 net, float input, for TensorRT fp16")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--cache", type=Path, default=Path("trt-cache"))
    ap.add_argument("--n", type=int, default=120)
    ap.add_argument("--widths", default="1280,960")
    ap.add_argument("--stop-at", type=float, default=0.0, help="unix time: no new variant after")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    dst = a.out / "bench.json"
    res: dict = json.loads(dst.read_text()) if dst.exists() else {}
    trips = read_triplets(a.video, a.n)
    files = {"f32": a.f32, "u8": a.u8, "u8_iobind": a.u8, "trt_u8": a.trt_u8, "trt_f32": a.trt_f32}
    for width in [int(w) for w in a.widths.split(",")]:
        base_tops = None
        for kind, model in files.items():
            key = f"{kind}_{width}"
            if model is None:
                continue
            if key in res and "error" not in res[key]:
                base_tops = base_tops if kind != "f32" else res[key].get("_tops")
                print("done before:", key, flush=True)
                continue
            if a.stop_at and time.time() > a.stop_at:
                print("stop: time budget used, before", key, flush=True)
                break
            print("run", key, flush=True)
            try:
                r = run_variant(kind, model, trips, width, a.cache)
            except Exception as exc:  # record and go on with the next variant
                r = {"error": f"{type(exc).__name__}: {exc}"[:500]}
            if kind == "f32":
                base_tops = r.get("_tops")
            if base_tops and r.get("_tops"):
                same = sum(
                    math.dist(p, q) * (1280 / width) <= 2
                    for p, q in zip(r["_tops"], base_tops, strict=True)
                )
                r["same_top_as_f32"] = round(same / len(base_tops), 3)
            res[key] = r
            dst.write_text(json.dumps(res, indent=1))
            print(key, {k: v for k, v in r.items() if k != "_tops"}, flush=True)
    summary = {k: {kk: vv for kk, vv in v.items() if kk != "_tops"} for k, v in res.items()}
    (a.out / "bench_summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
