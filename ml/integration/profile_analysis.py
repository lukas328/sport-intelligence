"""Run the product's analysis job (`handball_gpu_worker.analysis.run_analysis`, learned path)
locally on one video and record the wall time per stage (docs/plans/produkt-analyse-integration.md
step 1). S3 and the API reporter are replaced by local stand-ins; everything else is the product
code with the settings of the CPU image (HB_DETECT_EVERY etc. from the environment).

The input should be a product proxy (1280 px, 25 fps, crf 26); `--transcode` makes one with the
product's own transcode (`handball_worker.media.transcode`), from one or more files in order.

    uv run python ml/integration/profile_analysis.py VIDEO [VIDEO ...] --models DIR --out run.json
"""

import argparse
import json
import shutil
import subprocess
import tempfile
import time
from pathlib import Path


class LocalS3:
    """download_file / upload_file against a local directory (bucket/key -> root/bucket/key)."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def _path(self, bucket: str, key: str) -> Path:
        return self.root / bucket / key

    def download_file(self, bucket, key, dest, Config=None):  # noqa: N803
        src = self._path(bucket, key)
        if not src.exists():
            raise FileNotFoundError(f"{bucket}/{key}")
        shutil.copyfile(src, dest)

    def upload_file(self, src, bucket, key, Config=None, ExtraArgs=None):  # noqa: N803
        p = self._path(bucket, key)
        p.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, p)

    def put_object(self, Bucket, Key, Body, **_):  # noqa: N803
        p = self._path(Bucket, Key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(Body if isinstance(Body, bytes) else Body.read())

    def get_object(self, Bucket, Key, **_):  # noqa: N803
        import io

        return {"Body": io.BytesIO(self._path(Bucket, Key).read_bytes())}


class LocalReporter:
    def __init__(self) -> None:
        self.t0 = time.perf_counter()
        self.marks: list[tuple[str, float]] = []
        self.result = None
        self.error = None

    def stage(self, name: str) -> None:
        self.marks.append((name, time.perf_counter() - self.t0))
        print(f"[{self.marks[-1][1]:8.1f}s] stage {name}", flush=True)

    def fraction(self, f: float) -> None:
        pass

    def succeed(self, result) -> None:
        self.marks.append(("end", time.perf_counter() - self.t0))
        self.result = result

    def fail(self, error: str) -> None:
        self.marks.append(("end", time.perf_counter() - self.t0))
        self.error = error

    def stage_seconds(self) -> dict[str, float]:
        return {
            a: round(tb - ta, 1)
            for (a, ta), (_, tb) in zip(self.marks, self.marks[1:], strict=False)
        }


def make_proxy(sources: list[Path], work: Path) -> Path:
    from handball_worker.config import WorkerSettings
    from handball_worker.media.transcode import proxy_command

    joined = sources[0]
    if len(sources) > 1:
        lst = work / "list.txt"
        lst.write_text("".join(f"file '{s.resolve()}'\n" for s in sources))
        joined = work / "joined.mp4"
        subprocess.run(
            [
                WorkerSettings().ffmpeg,
                "-loglevel",
                "error",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(lst),
                "-c",
                "copy",
                str(joined),
            ],
            check=True,
        )
    out = work / "proxy.mp4"
    t0 = time.perf_counter()
    ws = WorkerSettings()
    cmd = [
        c
        for c in proxy_command(joined, out, ws.ffmpeg, ws.x264_preset)
        if c not in ("-progress", "pipe:1")
    ]
    subprocess.run(cmd, check=True)
    print(f"proxy {time.perf_counter() - t0:.1f}s", flush=True)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("videos", type=Path, nargs="+")
    ap.add_argument("--models", type=Path, required=True)
    ap.add_argument("--transcode", action="store_true")
    ap.add_argument("--work", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()

    from handball_gpu_worker import analysis
    from handball_jobkit import JobSettings

    work = a.work or Path(tempfile.mkdtemp(prefix="profile-"))
    work.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    video = make_proxy(a.videos, work) if a.transcode else a.videos[0]
    proxy_s = round(time.perf_counter() - t0, 1) if a.transcode else None
    s3root = work / "s3"
    LocalS3(s3root).upload_file(str(video), "media", "proxy.mp4")
    analysis.s3_client = lambda *_, **__: LocalS3(s3root)
    settings = JobSettings(
        work_dir=str(work / "jobs"),
        detector_model=str(a.models / "yolox_s.onnx"),
        number_det_model=str(a.models / "ch_PP-OCRv4_det_infer.onnx"),
        number_rec_model=str(a.models / "ch_PP-OCRv4_rec_infer.onnx"),
        reid_model=str(a.models / "reid.onnx"),
        role_model=str(a.models / "roles.onnx"),
    )
    rep = LocalReporter()
    t1 = time.perf_counter()
    try:
        result = analysis.run_analysis(
            "profile",
            "org",
            "match",
            "asset",
            "media",
            "proxy.mp4",
            "p/",
            {"home": "#ffffff", "away": "#000000"},
            settings=settings,
            reporter=rep,
        )
    except Exception as exc:  # report what ran
        result = rep.result or {"error": f"{type(exc).__name__}: {exc}"}
    wall = round(time.perf_counter() - t1, 1)
    import cv2

    cap = cv2.VideoCapture(str(video))
    frames, fps = cap.get(cv2.CAP_PROP_FRAME_COUNT), cap.get(cv2.CAP_PROP_FPS)
    cap.release()
    out = {
        "videos": [str(v) for v in a.videos],
        "video_s": round(frames / fps, 1) if fps else None,
        "fps": fps,
        "settings": {"detect_every": settings.detect_every, "number_every": settings.number_every},
        "proxy_s": proxy_s,
        "wall_s": wall,
        "stage_wall_s": rep.stage_seconds(),
        "timings_s": (result or {}).get("timings_s"),
        "needs_calibration": (result or {}).get("needs_calibration"),
        "calibration_info": (result or {}).get("calibration_info"),
        "tracks": len((result or {}).get("tracks") or []),
        "ball": ((result or {}).get("stats") or {}).get("ball"),
        "error": rep.error or (result or {}).get("error"),
    }
    a.out.write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps({k: v for k, v in out.items() if k != "ball"}, indent=1, default=str))


if __name__ == "__main__":
    main()
