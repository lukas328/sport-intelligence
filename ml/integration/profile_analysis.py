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


def _proxy_cmd(src: Path, dst: Path) -> list[str]:
    """The ingest's proxy command (`handball_worker.media.transcode.proxy_command`, preset of the
    worker settings); the same arguments written out where the worker package is not installed
    (the Modal job)."""
    try:
        from handball_worker.config import WorkerSettings
        from handball_worker.media.transcode import proxy_command

        ws = WorkerSettings()
        cmd = proxy_command(src, dst, ws.ffmpeg, ws.x264_preset)
        return [c for c in cmd if c not in ("-progress", "pipe:1")]
    except ImportError:
        return [
            shutil.which("ffmpeg") or "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-nostdin",
            "-y",
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
            "-movflags",
            "+faststart",
            str(dst),
        ]


def make_proxy(sources: list[Path], work: Path) -> Path:
    joined = sources[0]
    if len(sources) > 1:
        lst = work / "list.txt"
        lst.write_text("".join(f"file '{s.resolve()}'\n" for s in sources))
        joined = work / "joined.mp4"
        subprocess.run(
            [
                shutil.which("ffmpeg") or "ffmpeg",
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
    subprocess.run(_proxy_cmd(joined, out), check=True)
    print(f"proxy {time.perf_counter() - t0:.1f}s", flush=True)
    return out


def run_once(video: Path, models: Path, work: Path, overrides: dict | None = None) -> dict:
    """One run of the analysis job on a proxy video with the CPU-image settings changed by
    `overrides` (JobSettings fields, e.g. detect_every, ball_model); the stage times and what
    came out."""
    import cv2

    from handball_gpu_worker import analysis
    from handball_jobkit import JobSettings

    work.mkdir(parents=True, exist_ok=True)
    s3root = work / "s3"
    LocalS3(s3root).upload_file(str(video), "media", "proxy.mp4")
    analysis.s3_client = lambda *_, **__: LocalS3(s3root)
    fields = {
        "work_dir": str(work / "jobs"),
        "detector_model": str(models / "yolox_s.onnx"),
        "number_det_model": str(models / "ch_PP-OCRv4_det_infer.onnx"),
        "number_rec_model": str(models / "ch_PP-OCRv4_rec_infer.onnx"),
        "reid_model": str(models / "reid.onnx"),
        "role_model": str(models / "roles.onnx"),
        **(overrides or {}),
    }
    settings = JobSettings(**fields)
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
    cap = cv2.VideoCapture(str(video))
    frames, fps = cap.get(cv2.CAP_PROP_FRAME_COUNT), cap.get(cv2.CAP_PROP_FPS)
    cap.release()
    result = result or {}
    stats = result.get("stats") or {}
    return {
        "video_s": round(frames / fps, 1) if fps else None,
        "fps": fps,
        "overrides": overrides or {},
        "wall_s": wall,
        "stage_wall_s": rep.stage_seconds(),
        "timings_s": result.get("timings_s"),
        "needs_calibration": result.get("needs_calibration"),
        "calibration_info": result.get("calibration_info"),
        "tracks": len(result.get("tracks") or []),
        "versions": result.get("versions"),
        "ball_model_status": stats.get("ball_model_status"),
        "observe_counters": stats.get("observe_counters"),
        "numbers": _number_quality(result.get("tracks") or []),
        "scoreboard": _board_quality(result.get("scoreboard")),
        "ball": stats.get("ball"),
        "error": rep.error or result.get("error"),
    }


def _number_quality(tracks: list[dict]) -> dict:
    """Share of tracks with a voted shirt number: all tracks and the longer ones (at least 10 s,
    the players that matter for the stats)."""

    def share(ts: list[dict]) -> float | None:
        return round(sum(t.get("number") is not None for t in ts) / len(ts), 3) if ts else None

    long = [t for t in tracks if (t.get("last_ms", 0) - t.get("first_ms", 0)) >= 10_000]
    return {
        "tracks": len(tracks),
        "with_number": share(tracks),
        "tracks_10s": len(long),
        "with_number_10s": share(long),
        "numbers_10s": sorted({t["number"] for t in long if t.get("number") is not None}),
    }


def _board_quality(board: dict | None) -> dict | None:
    if not isinstance(board, dict):
        return None
    keep = ("source", "readings", "calls", "ocr", "goals", "board_clock")
    return {k: (len(v) if isinstance(v, list) else v) for k, v in board.items() if k in keep}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("videos", type=Path, nargs="+")
    ap.add_argument("--models", type=Path, required=True)
    ap.add_argument("--transcode", action="store_true")
    ap.add_argument("--work", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--set", nargs="*", default=[], help="JobSettings overrides key=value")
    a = ap.parse_args()

    work = a.work or Path(tempfile.mkdtemp(prefix="profile-"))
    work.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    video = make_proxy(a.videos, work) if a.transcode else a.videos[0]
    proxy_s = round(time.perf_counter() - t0, 1) if a.transcode else None
    overrides = dict(kv.split("=", 1) for kv in a.set)
    out = {
        "videos": [str(v) for v in a.videos],
        "proxy_s": proxy_s,
        **run_once(video, a.models, work, overrides),
    }
    a.out.write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps({k: v for k, v in out.items() if k != "ball"}, indent=1, default=str))


if __name__ == "__main__":
    main()
