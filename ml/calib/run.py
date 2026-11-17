"""Run the product's observation pass and automatic calibration on the calibration test set (research).

    uv run --project packages/vision python ml/calib/run.py observe CACHE [--ids c000 c001] [--jobs 2]
    uv run --project packages/vision python ml/calib/run.py calibrate CACHE OUT_JSON [--ids ...]

observe: per piece of ml/calib/testset.json the segment from Kaggle (single file), the worker's
  analysis proxy (1280 px, 25 fps, crf 26, `transcode.proxy_command`) of the piece, the product's
  `observe.observe` with YOLOX-S (people every 3rd frame, markings every 90th, as the worker) and
  stores `<id>.obs.npz`, `<id>.motion.npz`, `<id>.hall.jpg` (hall image) and `<id>.frames/` (the
  frames at the camera's turning points, for the truth). Cached: a piece already done is skipped.
calibrate: `observe.auto_calibrate` on each cached piece (seconds per piece, no video needed);
  writes per piece ok / reason / court homography (court m -> hall px) / info.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import traceback
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "packages/vision"))

KAGGLE_USER = "lukasde1000"
DEFAULT_MODEL = Path("models/yolox_s.onnx")


def pieces(ids: list[str] | None) -> list[dict[str, Any]]:
    ps = json.loads((HERE / "testset.json").read_text())["pieces"]
    return [p for p in ps if not ids or p["id"] in ids]


def download(p: dict[str, Any], dst: Path) -> None:
    url = (
        f"https://www.kaggle.com/api/v1/datasets/download/{KAGGLE_USER}/{p['dataset']}/{p['file']}"
    )
    for attempt in range(4):
        r = subprocess.run(["curl", "-sSfL", "-o", str(dst), url], capture_output=True, text=True)  # noqa: S607
        if r.returncode == 0:
            return
        time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"download failed: {p['file']}: {r.stderr.strip()}")


def proxy(src: Path, dst: Path, start: float, dur: float, threads: int) -> None:
    """The worker's analysis proxy of one piece (apps/worker media/transcode.proxy_command)."""
    subprocess.run(
        [  # noqa: S607
            "ffmpeg",
            "-hide_banner",
            "-nostdin",
            "-y",
            "-loglevel",
            "error",
            "-threads",
            str(threads),
            "-ss",
            str(start),
            "-t",
            str(dur),
            "-i",
            str(src),
            "-vf",
            "scale=1280:-2,fps=25",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "26",
            "-pix_fmt",
            "yuv420p",
            str(dst),
        ],
        check=True,
    )


def turning_frames(motion: Any, n_frames: int) -> list[int]:
    """Frames for the truth: for a moving camera the leftmost and rightmost view (pan extremes)
    and the middle one, for a fixed camera the middle frame."""
    if not motion.moving:
        return [n_frames // 2]
    yaw = []
    for i in range(0, n_frames, 5):
        r = motion._r(i)
        if r is None:
            continue
        z = (motion.ref_r @ r.T)[:, 2]  # the frame's optical axis on the canvas
        yaw.append((float(np.arctan2(z[0], z[2])), i))
    if not yaw:
        return [n_frames // 2]
    yaw.sort()
    lo, hi = yaw[0][1], yaw[-1][1]
    mid = min(yaw, key=lambda t: abs(t[0] - (yaw[0][0] + yaw[-1][0]) / 2))[1]
    return sorted({lo, mid, hi})


def observe_one(p: dict[str, Any], cache: Path, model: Path, threads: int) -> str:
    import cv2

    from handball_vision import observe as ob
    from handball_vision.detection import YoloxDetector

    pid = p["id"]
    if (cache / f"{pid}.obs.npz").exists():
        return f"{pid} cached"
    cv2.setNumThreads(threads)
    t0 = time.perf_counter()
    seg = cache / f"{pid}.seg.mp4"
    vid = cache / f"{pid}.proxy.mp4"
    try:
        download(p, seg)
        proxy(seg, vid, p["start_s"], p["dur_s"], threads)
        seg.unlink()
        det = YoloxDetector(model, threads=threads)
        obs = ob.observe(vid, det, detect_every=3, segment_every=90)
        frames_dir = cache / f"{pid}.frames"
        frames_dir.mkdir(exist_ok=True)
        want = turning_frames(obs.motion, obs.total)
        cap = cv2.VideoCapture(str(vid))
        for i in want:
            cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            ok, im = cap.read()
            if ok:
                cv2.imwrite(str(frames_dir / f"{i:05d}.jpg"), im, [cv2.IMWRITE_JPEG_QUALITY, 92])
        cv2.imwrite(str(cache / f"{pid}.hall.jpg"), obs.motion.background())
        obs.motion.save(cache / f"{pid}.motion.npz")
        # the hall image's sample frames, so a corrected motion can render the hall again
        np.savez_compressed(
            cache / f"{pid}.samples.npz",
            index=np.array([i for i, _ in obs.motion.samples]),
            frames=np.stack([f for _, f in obs.motion.samples]),
        )
        ob.save_observations(obs, cache / f"{pid}.obs.npz")
        (cache / f"{pid}.timings.json").write_text(json.dumps(obs.timings_s))
    finally:
        seg.unlink(missing_ok=True)
        vid.unlink(missing_ok=True)
    return f"{pid} done in {time.perf_counter() - t0:.0f} s"


def observe(a: argparse.Namespace) -> None:
    a.cache.mkdir(parents=True, exist_ok=True)
    todo = pieces(a.ids)
    threads = max(1, 4 // a.jobs)
    with ProcessPoolExecutor(a.jobs) as ex:
        futs = {ex.submit(observe_one, p, a.cache, a.model, threads): p["id"] for p in todo}
        for f, pid in futs.items():
            try:
                print(f.result(), flush=True)
            except Exception:
                print(pid, "FAILED", traceback.format_exc(limit=2), flush=True)


def load(cache: Path, pid: str) -> tuple[Any, Any]:
    import cv2

    from handball_vision import observe as ob
    from handball_vision.motion import CameraMotion

    motion = CameraMotion.load(cache / f"{pid}.motion.npz")
    samples = cache / f"{pid}.samples.npz"
    if samples.exists():
        z = np.load(samples)
        motion.samples = [(int(i), f) for i, f in zip(z["index"], z["frames"], strict=True)]
    obs = ob.load_observations(cache / f"{pid}.obs.npz", motion)
    hall = cv2.imread(str(cache / f"{pid}.hall.jpg"))
    return obs, hall


def calibrate_one(cache: Path, pid: str) -> dict[str, Any]:
    from handball_vision import observe as ob
    from handball_vision.calibration import CalibrationError

    obs, hall = load(cache, pid)
    hall = obs.motion.background()  # the worker calibrates on the rendered hall image
    t0 = time.perf_counter()
    out: dict[str, Any] = {"id": pid, "moving": bool(obs.motion.moving)}
    try:
        calib, info = ob.auto_calibrate(obs, hall)
        out.update(
            ok=True,
            homography=calib.homography.tolist(),
            info=info,
            focals=[float(obs.motion.focals[0])],
            canvas_f=float(obs.motion.canvas_f),
        )
        # frame px -> court m for each truth frame (camera motion, then the court)
        maps = {}
        for f in sorted((cache / f"{pid}.frames").glob("*.jpg")):
            i = int(f.stem)
            h = obs.motion.frame_to_canvas(i) if obs.motion.moving else np.eye(3)
            if h is not None:
                m = calib.inverse @ np.asarray(h, dtype=np.float64)
                maps[str(i)] = (m / m[2, 2]).tolist()
        out["frame_to_court"] = maps
    except CalibrationError as exc:
        out.update(ok=False, reason=getattr(exc, "reason", "court"), error=str(exc)[:400])
    out["seconds"] = round(time.perf_counter() - t0, 1)
    return out


def calibrate(a: argparse.Namespace) -> None:
    ids = [p["id"] for p in pieces(a.ids) if (a.cache / f"{p['id']}.obs.npz").exists()]
    with ProcessPoolExecutor(a.jobs) as ex:
        res = list(ex.map(calibrate_one, [a.cache] * len(ids), ids))
    for r in res:
        print(r["id"], "ok" if r["ok"] else r["reason"], r["seconds"], "s")
    a.out.write_text(json.dumps({"results": res}, indent=1) + "\n")
    print(sum(r["ok"] for r in res), "of", len(res), "calibrated")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("observe")
    p.add_argument("cache", type=Path)
    p.add_argument("--ids", nargs="*")
    p.add_argument("--jobs", type=int, default=2)
    p.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    p.set_defaults(fn=observe)
    p = sub.add_parser("calibrate")
    p.add_argument("cache", type=Path)
    p.add_argument("out", type=Path)
    p.add_argument("--ids", nargs="*")
    p.add_argument("--jobs", type=int, default=4)
    p.set_defaults(fn=calibrate)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
