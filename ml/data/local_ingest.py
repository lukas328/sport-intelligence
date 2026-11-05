"""Ingest game videos that are already on a local computer: the same cut as the cloud ingest
(`ingest_drive.py`: five 3-minute segments at 15/30/50/70/85 % of each game, 1280 wide, crf 25),
uploaded in batches as private Kaggle datasets `handball-segs-lNN` (l = local, so the numbers never
collide with the cloud ingest's bNN). The full videos stay on the computer; only the segments
(about 50 to 100 MB per game) go to Kaggle. The cloud side then reads the match clock per segment
and builds the labels from the official logs.

Resumable: a state file in WORKDIR records every game done and every batch uploaded; rerun the same
command after an interruption. A game's name is its file name without extension (a yt-dlp format
suffix like ".f298" is dropped); names from videos.csv match the official data automatically.

Needs Python 3.10+, ffmpeg/ffprobe on PATH and the Kaggle CLI (`pip install kaggle`, API token in
~/.kaggle/kaggle.json or %USERPROFILE%\\.kaggle\\kaggle.json).

usage: python ml/data/local_ingest.py VIDEO_DIR WORKDIR --user KAGGLE_USERNAME
       [--batch 20] [--pieces 5] [--seconds 180] [--max-games N] [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ingest_drive import FRACTIONS, cut, probe  # noqa: E402

VIDEO_EXT = (".mp4", ".mkv", ".webm", ".mov")


def game_name(path: Path) -> str:
    return re.sub(r"\.f\d+$", "", path.stem)


def find_videos(root: Path) -> dict[str, Path]:
    games: dict[str, Path] = {}
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.suffix.lower() in VIDEO_EXT and not p.name.startswith("."):
            name = game_name(p)
            # several files per game (e.g. downloaded pieces): keep the longest file name match only once
            games.setdefault(name, p)
    return games


def already_on_kaggle() -> dict[str, str]:
    """Games whose segments are already in a Kaggle dataset (cloud ingest bNN), from catalog.json,
    so a local run never uploads them a second time."""
    cat = Path(__file__).resolve().parent / "catalog.json"
    if not cat.exists():
        return {}
    games = json.loads(cat.read_text(encoding="utf-8")).get("games", [])
    return {re.sub(r"\.f\d+$", "", g["name"]): g["video"]["kaggle_dataset"]
            for g in games if (g.get("video") or {}).get("kaggle_dataset")}


def upload(batch_dir: Path, user: str, slug: str) -> bool:
    meta = {"title": slug, "id": f"{user}/{slug}", "licenses": [{"name": "other"}]}
    (batch_dir / "dataset-metadata.json").write_text(json.dumps(meta))
    res = subprocess.run(  # noqa: S603
        ["kaggle", "datasets", "create", "-p", str(batch_dir)],  # noqa: S607
        capture_output=True, text=True,
    )
    out = (res.stdout + res.stderr).strip()
    print(out.splitlines()[-1] if out else f"exit {res.returncode}", flush=True)
    return res.returncode == 0 and "error" not in out.lower()


def flush(work: Path, state: dict[str, Any], user: str, dry: bool) -> None:
    batch = work / f"batch_l{state['batch']:02d}"
    if not batch.exists() or not any(batch.glob("*.mp4")):
        return
    slug = f"handball-segs-l{state['batch']:02d}"
    print(f"uploading {batch.name} as {slug}", flush=True)
    if not dry and not upload(batch, user, slug):
        print("upload failed; fix the problem and rerun (the batch stays on disk)", flush=True)
        sys.exit(1)
    keep = work / "uploaded"
    keep.mkdir(exist_ok=True)
    if (batch / "index.json").exists():
        shutil.copy(batch / "index.json", keep / f"{batch.name}.index.json")
    if not dry:
        shutil.rmtree(batch)
    state["batch"] += 1
    save(work, state)


def save(work: Path, state: dict[str, Any]) -> None:
    (work / "state.json").write_text(json.dumps(state, indent=1))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("videos", type=Path)
    ap.add_argument("workdir", type=Path)
    ap.add_argument("--user", required=True, help="Kaggle user name (owner of the datasets)")
    ap.add_argument("--batch", type=int, default=20, help="games per Kaggle dataset")
    ap.add_argument("--pieces", type=int, default=5)
    ap.add_argument("--seconds", type=float, default=180)
    ap.add_argument("--max-games", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true", help="cut, but do not upload or delete")
    a = ap.parse_args()
    work = a.workdir
    work.mkdir(parents=True, exist_ok=True)
    sp = work / "state.json"
    state: dict[str, Any] = json.loads(sp.read_text()) if sp.exists() else {"batch": 1, "games": {}}
    videos = find_videos(a.videos)
    on_kaggle = already_on_kaggle()
    todo = [n for n in videos if n not in state["games"] and n not in on_kaggle]
    skipped = sorted(n for n in videos if n in on_kaggle)
    print(f"{len(videos)} videos, {len(skipped)} already on Kaggle (skipped), "
          f"{len(todo)} to do", flush=True)
    done = 0
    for name in todo:
        if a.max_games and done >= a.max_games:
            break
        src = videos[name]
        batch = work / f"batch_l{state['batch']:02d}"
        batch.mkdir(parents=True, exist_ok=True)
        info = src.with_name(src.stem + ".info.json")
        if info.exists():
            shutil.copy(info, batch / f"{name}.info.json")
        try:
            meta = probe(src)
            pieces = []
            if meta["duration_s"] < 15 * 60:  # a piece, not a whole game: keep it as one segment
                seg = batch / f"{name}_s0.mp4"
                cut(src, seg, 0.0, meta["duration_s"])
                pieces.append({"file": seg.name, "start_s": 0.0, "piece": True})
            for k, f in enumerate(FRACTIONS[: a.pieces] if not pieces else ()):
                start = max(0.0, meta["duration_s"] * f)
                seg = batch / f"{name}_s{k}.mp4"
                cut(src, seg, start, a.seconds)
                pieces.append({"file": seg.name, "start_s": round(start, 2)})
            state["games"][name] = {**meta, "batch": batch.name, "segments": pieces,
                                    "source": "local"}
            print(f"[{done + 1}/{len(todo)}] {name}: {meta['duration_s'] / 60:.0f} min, "
                  f"{meta['width']}x{meta['height']}", flush=True)
        except (subprocess.CalledProcessError, KeyError, ValueError, IndexError) as exc:
            state["games"][name] = {"error": str(exc)[:200]}
            print(f"{name}: failed {exc}", flush=True)
        (batch / "index.json").write_text(json.dumps(
            {n: g for n, g in state["games"].items() if g.get("batch") == batch.name}, indent=1))
        save(work, state)
        done += 1
        if sum(1 for g in state["games"].values() if g.get("batch") == batch.name) >= a.batch:
            flush(work, state, a.user, a.dry_run)
    flush(work, state, a.user, a.dry_run)
    ok = sum(1 for g in state["games"].values() if "segments" in g)
    bad = [n for n, g in state["games"].items() if "error" in g]
    print(f"done: {ok} games with segments, {len(bad)} failed {bad[:10]}", flush=True)


if __name__ == "__main__":
    main()
