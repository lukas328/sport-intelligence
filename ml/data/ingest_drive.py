"""Ingest game videos from a shared Google Drive folder into training segments on Kaggle.

Per game (one at a time, the disk is small): download the video (and its info JSON), cut a few
3-minute segments spread over the game (1280 wide), delete the full video, collect the segments
in a batch; a full batch becomes its own private Kaggle dataset (`handball-segs-bNN`), so GPU jobs
can mount the batches without re-uploading earlier ones. A state file makes it resumable; with
`--watch` it polls the folder for new games.

usage: python ml/data/ingest_drive.py FOLDER_URL WORKDIR [--watch 600] [--batch 10]
       [--pieces 5] [--seconds 180] [--min-free-gb 4]
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

FRACTIONS = (0.15, 0.30, 0.50, 0.70, 0.85)


def free_gb(path: Path) -> float:
    return shutil.disk_usage(path).free / 1e9


def probe(video: Path) -> dict[str, Any]:
    out = subprocess.run(  # noqa: S603
        [  # noqa: S607
            "ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
            "stream=width,height,r_frame_rate,codec_name:format=duration", "-of", "json",
            str(video),
        ],
        capture_output=True, text=True, check=True,
    ).stdout
    j = json.loads(out)
    s = j["streams"][0]
    a, b = s["r_frame_rate"].split("/")
    return {
        "duration_s": float(j["format"]["duration"]),
        "width": int(s["width"]),
        "height": int(s["height"]),
        "fps": round(float(a) / float(b), 3),
        "codec": s.get("codec_name"),
    }


def cut(video: Path, out: Path, start: float, seconds: float) -> None:
    subprocess.run(  # noqa: S603
        [  # noqa: S607
            "ffmpeg", "-v", "error", "-y", "-ss", f"{start:.2f}", "-t", f"{seconds:.2f}",
            "-i", str(video), "-an", "-vf", "scale='min(1280,iw)':-2", "-c:v", "libx264",
            "-preset", "veryfast", "-crf", "25", str(out),
        ],
        check=True,
    )


def listing(folder: str) -> dict[str, dict[str, str]]:
    import gdown  # type: ignore[import-untyped]

    files = gdown.download_folder(folder, skip_download=True, quiet=True) or []
    games: dict[str, dict[str, str]] = {}
    for f in files:
        name = Path(f.path).name
        if name.endswith(".info.json"):
            games.setdefault(name[: -len(".info.json")], {})["info"] = f.id
        elif name.lower().endswith((".mp4", ".mkv", ".webm", ".mov")):
            games.setdefault(Path(name).stem, {})["video"] = f.id
    return games


def kaggle_upload(batch_dir: Path, slug: str, title: str) -> str:
    meta = {"title": title, "id": f"{os.environ['KAGGLE_USERNAME']}/{slug}",
            "licenses": [{"name": "other"}]}
    (batch_dir / "dataset-metadata.json").write_text(json.dumps(meta))
    res = subprocess.run(  # noqa: S603
        ["kaggle", "datasets", "create", "-p", str(batch_dir)],  # noqa: S607
        capture_output=True, text=True,
    )
    return (res.stdout + res.stderr).strip().splitlines()[-1] if (res.stdout + res.stderr) else ""


def run_once(a: argparse.Namespace, state: dict[str, Any]) -> int:
    import gdown

    games = listing(a.folder)
    work = Path(a.workdir)
    done = 0
    for name, ids in sorted(games.items()):
        if name in state["games"] or "video" not in ids:
            continue
        if free_gb(work) < a.min_free_gb:
            print(f"only {free_gb(work):.1f} GB free, waiting", flush=True)
            break
        batch = work / f"batch_{state['batch']:02d}"
        batch.mkdir(parents=True, exist_ok=True)
        tmp = work / "tmp" / f"{name}.mp4"
        tmp.parent.mkdir(exist_ok=True)
        print(f"{name}: downloading", flush=True)
        gdown.download(id=ids["video"], output=str(tmp), quiet=True)
        if "info" in ids:
            gdown.download(id=ids["info"], output=str(batch / f"{name}.info.json"), quiet=True)
        try:
            meta = probe(tmp)
            pieces = []
            for k, f in enumerate(FRACTIONS[: a.pieces]):
                start = max(0.0, meta["duration_s"] * f)
                seg = batch / f"{name}_s{k}.mp4"
                cut(tmp, seg, start, a.seconds)
                pieces.append({"file": seg.name, "start_s": round(start, 2)})
            state["games"][name] = {**meta, "batch": batch.name, "segments": pieces}
            print(f"{name}: {meta['width']}x{meta['height']} {meta['fps']} fps, "
                  f"{meta['duration_s'] / 60:.0f} min, {len(pieces)} segments", flush=True)
        except (subprocess.CalledProcessError, KeyError, ValueError) as exc:
            state["games"][name] = {"error": str(exc)[:200]}
            print(f"{name}: failed {exc}", flush=True)
        finally:
            tmp.unlink(missing_ok=True)
        (batch / "index.json").write_text(json.dumps(
            {n: g for n, g in state["games"].items() if g.get("batch") == batch.name}, indent=1))
        done += 1
        save(work, state)
        if sum(1 for g in state["games"].values() if g.get("batch") == batch.name) >= a.batch:
            flush(work, state)
    return done


def flush(work: Path, state: dict[str, Any]) -> None:
    batch = work / f"batch_{state['batch']:02d}"
    if not batch.exists() or not any(batch.glob("*.mp4")):
        return
    slug = f"handball-segs-b{state['batch']:02d}"
    print(f"uploading {batch.name} as {slug}: {kaggle_upload(batch, slug, slug)}", flush=True)
    (work / "uploaded").mkdir(exist_ok=True)
    keep = work / "uploaded" / f"{batch.name}.index.json"
    if (batch / "index.json").exists():
        shutil.copy(batch / "index.json", keep)
    shutil.rmtree(batch)
    state["batch"] += 1
    save(work, state)


def save(work: Path, state: dict[str, Any]) -> None:
    (work / "state.json").write_text(json.dumps(state, indent=1))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("workdir")
    ap.add_argument("--watch", type=int, default=0, help="poll every N seconds")
    ap.add_argument("--batch", type=int, default=10)
    ap.add_argument("--pieces", type=int, default=5)
    ap.add_argument("--seconds", type=float, default=180)
    ap.add_argument("--min-free-gb", type=float, default=4.0)
    ap.add_argument("--flush-idle", type=int, default=3, help="upload a partial batch after N idle polls")
    a = ap.parse_args()
    work = Path(a.workdir)
    work.mkdir(parents=True, exist_ok=True)
    sp = work / "state.json"
    state: dict[str, Any] = json.loads(sp.read_text()) if sp.exists() else {"batch": 1, "games": {}}
    idle = 0
    while True:
        n = run_once(a, state)
        idle = 0 if n else idle + 1
        if not a.watch:
            flush(work, state)
            break
        if idle >= a.flush_idle:
            flush(work, state)
            idle = 0
        time.sleep(a.watch)


if __name__ == "__main__":
    main()
