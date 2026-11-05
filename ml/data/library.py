"""Library of every game segment on Kaggle: the match clock per segment for the batches the cloud
ingest did not make itself (`handball-segs-lNN` from `local_ingest.py` on the owner's computer).

The cloud ingest (`ingest_drive.py`) reads the clock while it cuts and keeps it in its own
state.json; a local batch arrives on Kaggle without it. This script lists the account's private
datasets `handball-segs-*`, and for each one not yet done: downloads its index.json (and the
<name>.info.json files), then one segment at a time, reads the match clock of the segment
(`ingest_drive.read_clock`: `segment_clock.py` in a subprocess with the vision environment, clock
data stamped with the reader version) and deletes the segment. Segments the ingest state (with
WORKDIR/clocks.json) already has clock data of the current reader for are not downloaded again, so
the bNN batches cost one index download each.

LIBDIR/library.json has the per-game shape of the ingest state (games -> segments -> clock) plus
the dataset each game is in ("kaggle_dataset") and one entry per dataset (last update on Kaggle,
games, status). It is written after every segment: an interrupted run goes on where it stopped,
a rerun does nothing new (a dataset is read again only when Kaggle shows a newer version, and
only its segments without current clock data). Consumers read both sources through
`segment_clock.all_games` and `match_official.load_names` (`merge_games`: the ingest state first,
newer clock data per segment wins).

A game's name is its file name (`local_ingest.game_name`); a name that differs from a name in
videos*.csv only in case, punctuation or a ".fNNN" format suffix is mapped to that name, so the
official data of match_official.py finds it.

    python ml/data/library.py [--libdir DIR] [--ingest WORKDIR] [--watch 900] [--only l]
        [--local-dir DIR]   # offline: DIR/handball-segs-*/ (index.json + segments) instead of Kaggle

Run it with the ingest's Python (Kaggle CLI on PATH, KAGGLE_USERNAME set); the clock reader uses
HANDBALL_CLOCK_PYTHON or the repo's .venv, as in ingest_drive.py.
"""

from __future__ import annotations

import argparse
import csv
import fcntl
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time
import unicodedata
import zipfile
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ingest_drive import free_gb, read_clock  # noqa: E402
from segment_clock import (  # noqa: E402
    CLOCK_READER,
    SCRATCH,
    SIDECAR,
    clock_reader,
    load_json,
    merge_clocks,
    write_json,
)

ROOT = Path(__file__).resolve().parent
LIBRARY = SCRATCH / "library"
PREFIX = "handball-segs-"
NAME_LISTS = ("videos.csv", "videos_next.csv", "videos_priority.csv")
MAX_ATTEMPTS = 3  # clock reads that failed (crash, timeout) before a segment is given up


# --- names and datasets (pure) ---------------------------------------------------------------


def base_name(name: str) -> str:
    """Name without a yt-dlp format suffix ("..._2023-09-23.f298")."""
    return re.sub(r"\.f\d+$", "", name.strip())


def name_key(name: str) -> str:
    """Comparison key of a game name: no accents, case, punctuation or format suffix."""
    s = unicodedata.normalize("NFKD", base_name(name)).encode("ascii", "ignore").decode()
    return re.sub(r"[^0-9a-z]", "", s.casefold())


def known_names(lists: Iterable[Path]) -> dict[str, str]:
    """name_key -> name of every row of the video lists (the names the official data uses)."""
    out: dict[str, str] = {}
    for p in lists:
        if not p.exists():
            continue
        with p.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f, delimiter=";"):
                n = (row.get("name") or "").strip()
                if n:
                    out.setdefault(name_key(n), n)
    return out


def canonical_name(name: str, known: dict[str, str]) -> str:
    """The video list's spelling of a file name when only case, punctuation, accents or a format
    suffix differ; else the name without format suffix."""
    return known.get(name_key(name), base_name(name))


def dataset_slug(batch: str) -> str | None:
    """Kaggle dataset of an ingest batch folder: batch_03 -> handball-segs-b03 (cloud ingest),
    batch_l03 -> handball-segs-l03 (local_ingest.py)."""
    m = re.fullmatch(r"batch_(l?)(\d+)", batch or "")
    if not m:
        return None
    return f"{PREFIX}{m.group(1) or 'b'}{int(m.group(2)):02d}"


def dataset_of(game: dict[str, Any] | None) -> str | None:
    """Kaggle dataset (slug) holding a game's segments."""
    if not game:
        return None
    return game.get("kaggle_dataset") or dataset_slug(game.get("batch", ""))


def has_current_clock(seg: dict[str, Any] | None) -> bool:
    return bool(seg) and clock_reader((seg or {}).get("clock")) >= CLOCK_READER


def _has_clock(game: dict[str, Any]) -> bool | None:
    segs = game.get("segments") or []
    if not any("clock" in s for s in segs):
        return None
    return any((s.get("clock") or {}).get("source") for s in segs)


def ingest_entry(
    name: str, game: dict[str, Any], ingest: dict[str, dict[str, Any]]
) -> tuple[str, dict[str, Any]] | None:
    """(key, entry) of a library game in the ingest state: under its name or under the file name
    it was mapped from ("..._2023-09-23.f298" in the ingest, the plain name in the library)."""
    for key in (name, game.get("file_name")):
        if key and ingest.get(key):
            return key, ingest[key]
    return None


def merge_games(
    primary: dict[str, dict[str, Any]], secondary: dict[str, dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    """Games of two sources (the ingest state first, then the library) as one dict in the ingest
    shape. A game in both (by name, or by the library's "file_name" it was mapped from) keeps the
    primary entry and key (unless it has no segments); per segment file the clock data of the
    newer reader wins. The inputs are not changed."""
    out = {n: g for n, g in primary.items()}
    for lib_name, g in secondary.items():
        found = ingest_entry(lib_name, g, out)
        name, p = found if found else (lib_name, None)
        if not p or not p.get("segments"):
            out[name] = g
            continue
        if not g.get("segments"):
            continue
        by_file = {s.get("file"): s for s in g["segments"]}
        segs = []
        for s in p["segments"]:
            o = by_file.get(s.get("file"))
            if o and o.get("clock") is not None and (
                clock_reader(o.get("clock")) > clock_reader(s.get("clock"))
            ):
                s = {**s, "clock": o["clock"]}
            segs.append(s)
        merged = {**p, "segments": segs}
        if (hc := _has_clock(merged)) is not None:
            merged["has_clock"] = hc
        out[name] = merged
    return out


def new_library() -> dict[str, Any]:
    return {"datasets": {}, "games": {}}


def add_index(
    lib: dict[str, Any], slug: str, index: dict[str, Any], known: dict[str, str]
) -> list[str]:
    """Games of a dataset's index.json into the library (idempotent). Clock data of segments
    already in the library is kept when the segment's file and start are unchanged. A game that is
    already in another dataset stays there (listed in the dataset's "duplicates"). Returns the
    library names of the dataset's games."""
    ds = lib["datasets"].setdefault(slug, {})
    names, dups = [], []
    for raw, g in sorted(index.items()):
        if not isinstance(g, dict) or not g.get("segments"):
            continue
        name = canonical_name(raw, known)
        old = lib["games"].get(name)
        if old and old.get("kaggle_dataset") not in (None, slug):
            dups.append(name)
            continue
        old_segs = {(s.get("file"), s.get("start_s")): s for s in (old or {}).get("segments", [])}
        segs = []
        for s in g["segments"]:
            prev = old_segs.get((s.get("file"), s.get("start_s")), {})
            keep = {k: prev[k] for k in ("clock", "clock_attempts") if k in prev}
            segs.append({**s, **keep})
        entry = {**g, "segments": segs, "kaggle_dataset": slug}
        entry.setdefault("source", "local" if slug.startswith(PREFIX + "l") else "ingest")
        if name != raw:
            entry["file_name"] = raw
        if (hc := _has_clock(entry)) is not None:
            entry["has_clock"] = hc
        lib["games"][name] = entry
        names.append(name)
    ds["games"] = names
    if dups:
        ds["duplicates"] = sorted(dups)
    else:
        ds.pop("duplicates", None)
    return names


def todo_segments(
    lib: dict[str, Any], names: Iterable[str], ingest: dict[str, dict[str, Any]]
) -> tuple[list[tuple[str, dict[str, Any]]], int]:
    """(segments of these library games that need a clock reading, number of segments skipped
    because the ingest state already has current clock data for them). Segments whose reading
    failed MAX_ATTEMPTS times are not retried."""
    todo, covered = [], 0
    for name in names:
        g = lib["games"].get(name) or {}
        found = ingest_entry(name, g, ingest)
        ing = {s.get("file"): s for s in (found[1] if found else {}).get("segments") or []}
        for s in g.get("segments") or []:
            if has_current_clock(s) or s.get("clock_attempts", 0) >= MAX_ATTEMPTS:
                continue
            if has_current_clock(ing.get(s.get("file"))):
                covered += 1
                continue
            todo.append((name, s))
    return todo, covered


def set_clock(game: dict[str, Any], seg: dict[str, Any], clock: dict[str, Any]) -> None:
    """Clock data of one segment into a library game (`ingest_drive.read_clock`'s result); a
    failed reading (no "reader") counts as an attempt and keeps older data."""
    if clock.get("reader"):
        seg["clock"] = clock
        seg.pop("clock_attempts", None)
    else:
        seg["clock_attempts"] = seg.get("clock_attempts", 0) + 1
        if seg["clock_attempts"] >= MAX_ATTEMPTS or "clock" not in seg:
            seg["clock"] = clock
    if (hc := _has_clock(game)) is not None:
        game["has_clock"] = hc


def needs_visit(entry: dict[str, Any] | None, last_updated: str) -> bool:
    """Whether a dataset has to be looked at: new, not finished, or a newer version on Kaggle."""
    return not entry or entry.get("status") != "done" or entry.get("last_updated") != last_updated


def summary(lib: dict[str, Any]) -> dict[str, Any]:
    games = lib.get("games", {})
    segs = [s for g in games.values() for s in g.get("segments") or []]
    return {
        "datasets": len(lib.get("datasets", {})),
        "datasets_done": sum(1 for d in lib.get("datasets", {}).values()
                             if d.get("status") == "done"),
        "games": len(games),
        "local_games": sum(1 for g in games.values() if g.get("source") == "local"),
        "segments": len(segs),
        "segments_with_clock_data": sum(1 for s in segs if has_current_clock(s)),
        "segments_with_clock": sum(1 for s in segs
                                   if has_current_clock(s) and s["clock"].get("source")),
        "games_with_clock": sum(1 for g in games.values() if g.get("has_clock")),
    }


# --- consumers --------------------------------------------------------------------------------


def library_games(libdir: Path | None) -> dict[str, dict[str, Any]]:
    """Games of LIBDIR/library.json ({} without one)."""
    if libdir is None:
        return {}
    return dict(load_json(libdir / "library.json", {}).get("games", {}))


def ingest_games(workdir: Path) -> dict[str, dict[str, Any]]:
    """Games of the ingest state, clock data of clocks.json merged in (read only)."""
    state = load_json(workdir / "state.json", {"games": {}})
    merge_clocks(state, load_json(workdir / SIDECAR, {}))
    return dict(state.get("games", {}))


# --- sources: Kaggle, or a local folder for offline runs ----------------------------------------


class Source(Protocol):
    def datasets(self) -> dict[str, str]: ...  # slug -> last update
    def files(self, slug: str) -> set[str]: ...
    def fetch(self, slug: str, name: str, dest: Path) -> Path: ...


class KaggleSource:
    def __init__(self, owner: str, cli: str = "kaggle") -> None:
        self.owner, self.cli = owner, cli

    def _run(self, *args: str) -> str:
        res = subprocess.run(  # noqa: S603
            [self.cli, *args], capture_output=True, text=True, timeout=1800,
        )
        if res.returncode:
            err = (res.stderr.strip() or res.stdout.strip()).splitlines()
            raise RuntimeError(f"kaggle {args[0]} {args[1]}: {err[-1] if err else res.returncode}")
        return res.stdout

    @staticmethod
    def _csv(out: str) -> tuple[list[dict[str, str]], str | None]:
        token = re.search(r"Next Page Token = (\S+)", out)
        lines = [ln for ln in out.splitlines() if "," in ln and "Next Page Token" not in ln]
        return list(csv.DictReader(io.StringIO("\n".join(lines)))), token.group(1) if token else None

    def datasets(self) -> dict[str, str]:
        out: dict[str, str] = {}
        for page in range(1, 20):
            rows, _ = self._csv(self._run(
                "datasets", "list", "--mine", "-s", PREFIX.rstrip("-"), "--csv", "-p", str(page)))
            for r in rows:
                ref = r.get("ref", "")
                owner, _, slug = ref.partition("/")
                if owner == self.owner and slug.startswith(PREFIX):
                    out[slug] = r.get("lastUpdated", "")
            if len(rows) < 20:
                break
        return out

    def files(self, slug: str) -> set[str]:
        names: set[str] = set()
        token: str | None = None
        for _ in range(50):
            args = ["datasets", "files", f"{self.owner}/{slug}", "--csv", "--page-size", "200"]
            rows, token = self._csv(self._run(*args, *(["--page-token", token] if token else [])))
            names |= {r["name"] for r in rows if r.get("name")}
            if not token:
                break
        return names

    def fetch(self, slug: str, name: str, dest: Path) -> Path:
        dest.mkdir(parents=True, exist_ok=True)
        self._run("datasets", "download", f"{self.owner}/{slug}", "-f", name, "-p", str(dest),
                  "-o", "-q")
        out, packed = dest / name, dest / f"{name}.zip"
        if packed.exists():  # the API may hand a single file over zipped
            with zipfile.ZipFile(packed) as z:
                member = next(m for m in z.namelist() if Path(m).name == name)
                with z.open(member) as src, out.open("wb") as dst:
                    shutil.copyfileobj(src, dst)
            packed.unlink()
        if not out.exists():
            raise RuntimeError(f"{slug}/{name}: download left no file")
        return out


class LocalSource:
    """DIR/<slug>/ folders laid out like a Kaggle dataset (offline test of the whole path);
    fetch copies, so the folder stays as it is."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def datasets(self) -> dict[str, str]:
        out = {}
        for d in sorted(self.root.glob(f"{PREFIX}*")):
            if d.is_dir():
                stamp = max((f.stat().st_mtime for f in d.iterdir()), default=0.0)
                out[d.name] = datetime.fromtimestamp(stamp).isoformat(timespec="seconds")
        return out

    def files(self, slug: str) -> set[str]:
        return {f.name for f in (self.root / slug).iterdir() if f.is_file()}

    def fetch(self, slug: str, name: str, dest: Path) -> Path:
        dest.mkdir(parents=True, exist_ok=True)
        return Path(shutil.copy(self.root / slug / name, dest / name))


# --- run ----------------------------------------------------------------------------------------


def save(libdir: Path, lib: dict[str, Any]) -> None:
    lib["summary"] = summary(lib)
    lib["updated"] = datetime.now().isoformat(timespec="seconds")
    write_json(libdir / "library.json", lib)


def process_dataset(
    src: Source, slug: str, stamp: str, lib: dict[str, Any], a: argparse.Namespace,
    known: dict[str, str],
) -> None:
    libdir: Path = a.libdir
    ds = lib["datasets"].setdefault(slug, {})
    files = src.files(slug)
    ds["files"] = len(files)
    if "index.json" not in files:
        ds["status"] = "no index.json"
        print(f"{slug}: no index.json (yet)", flush=True)
        save(libdir, lib)
        return
    idx_dir = libdir / "index"
    tmp = libdir / "tmp"
    idx = src.fetch(slug, "index.json", tmp)
    idx_dir.mkdir(exist_ok=True)
    idx = Path(shutil.move(str(idx), idx_dir / f"{slug}.index.json"))
    names = add_index(lib, slug, load_json(idx, {}), known)
    info_dir = libdir / "info"
    for name in names:
        raw = lib["games"][name].get("file_name", name)
        info = f"{raw}.info.json"
        if info in files and not (info_dir / f"{name}.info.json").exists():
            try:
                info_dir.mkdir(exist_ok=True)
                src.fetch(slug, info, tmp).replace(info_dir / f"{name}.info.json")
            except Exception as exc:  # noqa: BLE001 - descriptions are optional
                print(f"  {info}: {str(exc)[:160]}", flush=True)
        lib["games"][name]["info_json"] = (info_dir / f"{name}.info.json").exists()
    todo, covered = todo_segments(lib, names, ingest_games(a.ingest))
    missing = [(n, s) for n, s in todo if s["file"] not in files]
    todo = [(n, s) for n, s in todo if s["file"] in files]
    ds.update({"status": "pending", "last_updated": stamp, "games": names,
               "covered_by_ingest": covered, "missing_files": [s["file"] for _, s in missing]})
    print(f"{slug}: {len(names)} games, {len(todo)} segments to read, {covered} already read by "
          f"the ingest, {len(missing)} missing", flush=True)
    save(libdir, lib)
    failed = 0
    for k, (name, seg) in enumerate(todo):
        if free_gb(libdir) < a.min_free_gb:
            print(f"only {free_gb(libdir):.1f} GB free, stopping this pass", flush=True)
            failed += 1
            break
        try:
            path = src.fetch(slug, seg["file"], tmp)
        except Exception as exc:  # noqa: BLE001 - network or quota: next pass
            print(f"  {seg['file']}: download failed: {str(exc)[:160]}", flush=True)
            failed += 1
            continue
        try:
            print(f"[{k + 1}/{len(todo)}]", end="", flush=True)
            set_clock(lib["games"][name], seg, read_clock(path))
        finally:
            path.unlink(missing_ok=True)
        save(libdir, lib)
    shutil.rmtree(tmp, ignore_errors=True)
    left, _ = todo_segments(lib, names, ingest_games(a.ingest))
    left = [x for x in left if x[1]["file"] in files]
    ds["status"] = "done" if not left and not failed else "pending"
    ds["checked"] = datetime.now().isoformat(timespec="seconds")
    save(libdir, lib)
    merged = merge_games(ingest_games(a.ingest), {n: lib["games"][n] for n in names})
    segs = [x for g in merged.values() if dataset_of(g) == slug for x in g.get("segments") or []]
    clocked = sum(1 for x in segs if has_current_clock(x) and x["clock"].get("source"))
    print(f"{slug}: {ds['status']}, {len(todo)} segments read here, {covered} by the ingest; "
          f"{clocked} of {len(segs)} segments with a clock", flush=True)


def run_once(src: Source, a: argparse.Namespace, known: dict[str, str]) -> int:
    shutil.rmtree(a.libdir / "tmp", ignore_errors=True)  # left by an interrupted run
    lib = load_json(a.libdir / "library.json", new_library())
    lib.setdefault("datasets", {})
    lib.setdefault("games", {})
    seen = src.datasets()
    visits = 0
    for slug, stamp in sorted(seen.items()):
        if a.only and not slug.startswith(PREFIX + a.only):
            continue
        if not needs_visit(lib["datasets"].get(slug), stamp):
            continue
        visits += 1
        try:
            process_dataset(src, slug, stamp, lib, a, known)
        except Exception as exc:  # noqa: BLE001 - one dataset must not stop the others
            print(f"{slug}: failed: {str(exc)[:200]}", flush=True)
            lib = load_json(a.libdir / "library.json", lib)
    print(f"{datetime.now():%Y-%m-%d %H:%M} {len(seen)} datasets on the source, {visits} visited; "
          f"{json.dumps(summary(lib))}", flush=True)
    return visits


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--libdir", type=Path, default=LIBRARY, help="holds library.json")
    ap.add_argument("--ingest", type=Path, default=SCRATCH / "ingest",
                    help="cloud ingest workdir (read only: state.json, clocks.json)")
    ap.add_argument("--watch", type=int, default=0, help="poll for new datasets every N seconds")
    ap.add_argument("--only", default="", help="only datasets handball-segs-<ONLY>* (l, b, l03)")
    ap.add_argument("--local-dir", type=Path, help="offline: datasets as folders in this folder")
    ap.add_argument("--owner", default=os.environ.get("KAGGLE_USERNAME", "lukasde1000"))
    ap.add_argument("--kaggle", default="kaggle", help="Kaggle CLI")
    ap.add_argument("--min-free-gb", type=float, default=1.0)
    a = ap.parse_args()
    a.libdir.mkdir(parents=True, exist_ok=True)
    lock = (a.libdir / ".lock").open("w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        sys.exit(f"another library.py runs on {a.libdir}")
    src: Source = LocalSource(a.local_dir) if a.local_dir else KaggleSource(a.owner, a.kaggle)
    known = known_names(ROOT / n for n in NAME_LISTS)
    while True:
        try:
            run_once(src, a, known)
        except Exception as exc:  # noqa: BLE001 - listing failed (network): try again later
            print(f"{datetime.now():%Y-%m-%d %H:%M} pass failed: {str(exc)[:200]}", flush=True)
            if not a.watch:
                raise
        if not a.watch:
            break
        time.sleep(a.watch)


if __name__ == "__main__":
    main()
