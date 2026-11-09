"""Library of every game segment on Kaggle: the match clock per segment for the batches the cloud
ingest did not make itself (`handball-segs-lNN` from `local_ingest.py` on the owner's computer).

The cloud ingest (`ingest_drive.py`) reads the clock while it cuts and keeps it in its own
state.json; a local batch arrives on Kaggle without it. This script lists the account's private
datasets `handball-segs-*`, and for each one not yet done: downloads its index.json, then the whole
dataset as one zip archive (one request instead of one per segment, which Kaggle rate-limits), and
takes the <name>.info.json files and the segments out of it one at a time. A pool of clock readers
(`--workers 3`, `ingest_drive.read_clock`: `segment_clock.py` in a niced subprocess with the vision
environment, one thread each, clock data stamped with the reader version) reads the segments in
parallel; each extracted segment is deleted once read. The zip goes to LIBDIR/tmp when it fits
with `--min-free-gb` to spare and is cut back behind every segment taken out (members are taken
from the end of the file); otherwise the same archive is read in place on Kaggle's storage with
HTTP range requests, so it needs no disk at all. Kaggle answers "rate limited" are retried with
exponential backoff. Segments the ingest state (with WORKDIR/clocks.json) already has clock data of
the current reader for are not read again, so the bNN batches cost one index download each.

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
        [--workers 3] [--min-free-gb 1.5]
        [--local-dir DIR]   # offline: DIR/handball-segs-*/ (index.json + segments) instead of Kaggle

Run it with the ingest's Python (Kaggle CLI and package on PATH, KAGGLE_USERNAME set); the clock
reader uses HANDBALL_CLOCK_PYTHON or the repo's .venv, as in ingest_drive.py.
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
from collections.abc import Callable, Iterable
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
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
WORKERS = 3  # clock readers at once (4 cores; each reader is one thread)
EXTRACT_ROOM_GB = 0.3  # beside a local zip: room for the segments taken out of it
RATE_LIMITED = re.compile(r"rate.?limit|too many requests|\b429\b", re.IGNORECASE)


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
    already in another dataset stays there (listed in the dataset's "duplicates"). Games of this
    dataset that its new index no longer lists are removed (listed in "removed"). Returns the
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
    # a new version of the dataset without some games (e.g. videos below 720p taken out): drop them
    gone = [n for n, g in lib["games"].items() if g.get("kaggle_dataset") == slug and n not in names]
    for n in gone:
        del lib["games"][n]
    if gone:
        ds["removed"] = sorted(set(ds.get("removed", [])) | set(gone))
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


class LowDiskError(RuntimeError):
    """Less free disk than --min-free-gb."""


def with_backoff[T](
    call: Callable[[], T], what: str, *, tries: int = 8, base_s: float = 60.0,
    cap_s: float = 1800.0, sleep: Callable[[float], None] = time.sleep,
) -> T:
    """call(); an answer "rate limited" (or HTTP 429) is tried again after base_s, 2 * base_s, ...
    (at most cap_s each), `tries` calls in all. Other errors are raised at once."""
    for k in range(tries):
        try:
            return call()
        except Exception as exc:
            if not RATE_LIMITED.search(str(exc)) or k + 1 >= tries:
                raise
            wait_s = min(cap_s, base_s * 2**k)
            print(f"  {what}: rate limited, next try in {wait_s:.0f} s", flush=True)
            sleep(wait_s)
    raise AssertionError("unreachable")


class RangeFile(io.RawIOBase):
    """A remote file read with HTTP range requests (wrap it in io.BufferedReader):
    get(start, end) returns the bytes start..end (both included)."""

    def __init__(self, size: int, get: Callable[[int, int], bytes]) -> None:
        super().__init__()
        self.size, self.get, self.pos = size, get, 0

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        return self.pos

    def seek(self, offset: int, whence: int = io.SEEK_SET) -> int:
        base = {io.SEEK_SET: 0, io.SEEK_CUR: self.pos, io.SEEK_END: self.size}[whence]
        self.pos = max(0, base + offset)
        return self.pos

    def readinto(self, b: Any) -> int:
        n = min(len(b), self.size - self.pos)
        if n <= 0:
            return 0
        data = self.get(self.pos, self.pos + n - 1)
        if not data:
            raise OSError(f"no data at {self.pos}")
        b[: len(data)] = data
        self.pos += len(data)
        return len(data)


class Archive:
    """A dataset's zip archive, members by file name. `source` is a local zip file (deleted on
    close; `extract(cut=True)` cuts the file back to the start of the member taken out, so members
    are then taken from the end of the file, see `offset`) or a seekable remote file."""

    def __init__(self, source: Path | io.BufferedIOBase) -> None:
        self.path = source if isinstance(source, Path) else None
        self.zip = zipfile.ZipFile(source)
        self.members = {Path(i.filename).name: i for i in self.zip.infolist() if not i.is_dir()}
        self.end = self.path.stat().st_size if self.path else None

    def offset(self, name: str) -> int:
        info = self.members.get(name)
        return info.header_offset if info else -1

    def extract(self, name: str, dest: Path, cut: bool = False) -> Path:
        info = self.members.get(name)
        if info is None:
            raise KeyError(f"{name} is not in the archive")
        if self.end is not None and info.header_offset >= self.end:
            raise RuntimeError(f"{name}: already cut off the zip")
        dest.mkdir(parents=True, exist_ok=True)
        out, part = dest / name, dest / f"{name}.part"
        with self.zip.open(info) as src, part.open("wb") as dst:
            shutil.copyfileobj(src, dst, 1 << 20)
        part.replace(out)
        if cut and self.path is not None:
            os.truncate(self.path, info.header_offset)
            self.end = info.header_offset
        return out

    def close(self) -> None:
        self.zip.close()
        if self.path is not None:
            self.path.unlink(missing_ok=True)
            Path(f"{self.path}.kaggle-partial").unlink(missing_ok=True)

    def __enter__(self) -> Archive:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


def fits_on_disk(free: float, size_bytes: int | None, min_free_gb: float) -> bool:
    """Whether a zip of size_bytes can be downloaded with `free` GB free and min_free_gb (plus room
    for the segments taken out of it) to spare."""
    return bool(size_bytes) and free - size_bytes / 1e9 >= min_free_gb + EXTRACT_ROOM_GB


class Source(Protocol):
    def datasets(self) -> dict[str, str]: ...  # slug -> last update
    def files(self, slug: str) -> set[str]: ...
    def fetch(self, slug: str, name: str, dest: Path) -> Path: ...
    def open_archive(self, slug: str, dest: Path, min_free_gb: float) -> Archive: ...


class KaggleSource:
    DOWNLOAD_TIMEOUT_S = 3 * 3600

    def __init__(
        self, owner: str, cli: str = "kaggle", sleep: Callable[[float], None] = time.sleep
    ) -> None:
        self.owner, self.cli, self.sleep = owner, cli, sleep
        self.sizes: dict[str, int] = {}  # slug -> bytes of the archive (from the listing)
        self._api: Any = None

    def _run(self, *args: str) -> str:
        res = subprocess.run(  # noqa: S603
            [self.cli, *args], capture_output=True, text=True, timeout=1800,
        )
        if res.returncode:
            err = (res.stderr.strip() or res.stdout.strip()).splitlines()
            raise RuntimeError(f"kaggle {args[0]} {args[1]}: {err[-1] if err else res.returncode}")
        return res.stdout

    def _call(self, *args: str) -> str:
        return with_backoff(lambda: self._run(*args), f"kaggle {args[0]} {args[1]}",
                            sleep=self.sleep)

    @staticmethod
    def _csv(out: str) -> tuple[list[dict[str, str]], str | None]:
        token = re.search(r"Next Page Token = (\S+)", out)
        lines = [ln for ln in out.splitlines() if "," in ln and "Next Page Token" not in ln]
        return list(csv.DictReader(io.StringIO("\n".join(lines)))), token.group(1) if token else None

    def datasets(self) -> dict[str, str]:
        out: dict[str, str] = {}
        for page in range(1, 20):
            rows, _ = self._csv(self._call(
                "datasets", "list", "--mine", "-s", PREFIX.rstrip("-"), "--csv", "-p", str(page)))
            for r in rows:
                ref = r.get("ref", "")
                owner, _, slug = ref.partition("/")
                if owner == self.owner and slug.startswith(PREFIX):
                    out[slug] = r.get("lastUpdated", "")
                    if (r.get("size") or "").isdigit():
                        self.sizes[slug] = int(r["size"])
            if len(rows) < 20:
                break
        return out

    def files(self, slug: str) -> set[str]:
        names: set[str] = set()
        token: str | None = None
        for _ in range(50):
            args = ["datasets", "files", f"{self.owner}/{slug}", "--csv", "--page-size", "200"]
            rows, token = self._csv(self._call(*args, *(["--page-token", token] if token else [])))
            names |= {r["name"] for r in rows if r.get("name")}
            if not token:
                break
        return names

    def fetch(self, slug: str, name: str, dest: Path) -> Path:
        dest.mkdir(parents=True, exist_ok=True)
        self._call("datasets", "download", f"{self.owner}/{slug}", "-f", name, "-p", str(dest),
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

    # the whole dataset as one zip: downloaded when it fits on the disk, else read in place

    def open_archive(self, slug: str, dest: Path, min_free_gb: float) -> Archive:
        dest.mkdir(parents=True, exist_ok=True)
        size, free = self.sizes.get(slug), free_gb(dest)
        if fits_on_disk(free, size, min_free_gb):
            try:
                return Archive(self._download(slug, dest, min_free_gb))
            except (LowDiskError, zipfile.BadZipFile) as exc:
                (dest / f"{slug}.zip").unlink(missing_ok=True)
                print(f"  {slug}: zip download: {exc}; reading the archive in place", flush=True)
        else:
            print(f"  {slug}: the {(size or 0) / 1e9:.1f} GB zip does not fit ({free:.1f} GB free, "
                  f"{min_free_gb} GB to keep): reading it in place on Kaggle's storage", flush=True)
        return self._remote(slug)

    def _download(self, slug: str, dest: Path, min_free_gb: float) -> Path:
        zpath, log = dest / f"{slug}.zip", dest / f"{slug}.download.log"

        def once() -> None:
            t0 = time.time()
            with log.open("w") as out:
                proc = subprocess.Popen(  # noqa: S603
                    [self.cli, "datasets", "download", f"{self.owner}/{slug}", "-p", str(dest),
                     "-q"], stdout=out, stderr=subprocess.STDOUT,
                )
                while proc.poll() is None:
                    short = free_gb(dest) < min_free_gb
                    if short or time.time() - t0 > self.DOWNLOAD_TIMEOUT_S:
                        proc.kill()
                        proc.wait()
                        zpath.unlink(missing_ok=True)
                        Path(f"{zpath}.kaggle-partial").unlink(missing_ok=True)
                        if short:
                            raise LowDiskError(f"under {min_free_gb} GB free while downloading")
                        raise RuntimeError("download timed out")
                    time.sleep(2)
            lines = log.read_text(errors="replace").strip().splitlines()
            if proc.returncode:
                raise RuntimeError(f"kaggle datasets download: {lines[-1] if lines else ''}")
            if not zpath.exists():
                raise RuntimeError(f"{slug}: download left no zip")
            print(f"  {slug}: zip downloaded, {zpath.stat().st_size / 1e9:.2f} GB in "
                  f"{time.time() - t0:.0f} s", flush=True)

        try:
            with_backoff(once, f"kaggle datasets download {slug}", sleep=self.sleep)
        finally:
            log.unlink(missing_ok=True)
        return zpath

    def _archive_url(self, slug: str) -> tuple[str, int]:
        """Signed storage URL and size of the dataset's zip (the redirect target of the
        download API)."""

        def once() -> tuple[str, int]:
            from kaggle.api.kaggle_api_extended import KaggleApi
            from kagglesdk.datasets.types.dataset_api_service import ApiDownloadDatasetRequest

            if self._api is None:
                api = KaggleApi()
                api.authenticate()
                self._api = api
            req = ApiDownloadDatasetRequest()
            req.owner_slug, req.dataset_slug = self.owner, slug
            with self._api.build_kaggle_client() as kaggle:
                resp = kaggle.datasets.dataset_api_client.download_dataset(req)
            try:
                resp.raise_for_status()
                return resp.url, int(resp.headers["Content-Length"])
            finally:
                resp.close()

        return with_backoff(once, f"archive URL of {slug}", sleep=self.sleep)

    def _remote(self, slug: str) -> Archive:
        import requests

        url, size = self._archive_url(slug)
        state = {"url": url}
        session = requests.Session()

        def get(start: int, end: int) -> bytes:
            err: object = None
            for k in range(6):
                try:
                    r = session.get(state["url"], headers={"Range": f"bytes={start}-{end}"},
                                    stream=True, timeout=300)
                    with r:
                        if r.status_code == 206:
                            data = r.content
                            if len(data) == end - start + 1:
                                return data
                            err = f"{len(data)} of {end - start + 1} bytes"
                        else:
                            err = f"HTTP {r.status_code}"
                            if r.status_code in (400, 401, 403):  # the signed URL expired
                                state["url"] = self._archive_url(slug)[0]
                                continue
                except requests.RequestException as exc:
                    err = exc
                time.sleep(min(60.0, 5.0 * 2**k))
            raise RuntimeError(f"{slug}: bytes {start}-{end}: {err}")

        print(f"  {slug}: reading the {size / 1e9:.2f} GB zip in place", flush=True)
        return Archive(io.BufferedReader(RangeFile(size, get), buffer_size=8 << 20))


class LocalSource:
    """DIR/<slug>/ folders laid out like a Kaggle dataset (offline test of the whole path);
    fetch copies and open_archive zips, so the folder stays as it is."""

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

    def open_archive(self, slug: str, dest: Path, min_free_gb: float) -> Archive:
        dest.mkdir(parents=True, exist_ok=True)
        zpath = dest / f"{slug}.zip"
        with zipfile.ZipFile(zpath, "w") as z:
            for f in sorted((self.root / slug).iterdir()):
                if f.is_file():
                    z.write(f, f.name)
        return Archive(zpath)


# --- run ----------------------------------------------------------------------------------------


def save(libdir: Path, lib: dict[str, Any]) -> None:
    lib["summary"] = summary(lib)
    lib["updated"] = datetime.now().isoformat(timespec="seconds")
    write_json(libdir / "library.json", lib)


Job = tuple[str, dict[str, Any]]  # (library game name, segment)


def read_parallel(
    jobs: list[Job], take: Callable[[str, dict[str, Any]], Path],
    apply: Callable[[str, dict[str, Any], dict[str, Any]], None], workers: int,
) -> int:
    """Clock readings of `jobs` in order, `workers` at once: take(game, seg) gives the segment as
    a local file (main thread, one at a time), `read_clock` reads it in a pool thread, apply(game,
    seg, clock) stores the result (main thread, as readings finish); the file is deleted once
    read. A take that fails skips the segment; LowDiskError stops taking more. An exception of a
    reading (KeyboardInterrupt) stops taking more and is raised once the running readings are
    applied. Returns the number of segments not read."""
    queue, failed, done, n = list(reversed(jobs)), 0, 0, len(jobs)
    pending: dict[Future[dict[str, Any]], tuple[str, dict[str, Any], Path]] = {}
    error: BaseException | None = None
    t0 = time.time()
    pool = ThreadPoolExecutor(max(1, workers), thread_name_prefix="clock")
    try:
        while True:
            while queue and error is None and len(pending) < max(1, workers):
                name, seg = queue.pop()
                try:
                    path = take(name, seg)
                except LowDiskError as exc:
                    print(f"{exc}, stopping this pass", flush=True)
                    failed += 1 + len(queue)
                    queue.clear()
                    break
                except Exception as exc:  # noqa: BLE001 - one segment must not stop the batch
                    print(f"  {seg['file']}: not taken: {str(exc)[:160]}", flush=True)
                    failed += 1
                    continue
                pending[pool.submit(read_clock, path)] = (name, seg, path)
            if not pending:
                break
            finished, _ = wait(pending, return_when=FIRST_COMPLETED)
            for fut in finished:
                name, seg, path = pending.pop(fut)
                path.unlink(missing_ok=True)
                try:
                    clock = fut.result()
                except BaseException as exc:  # noqa: BLE001 - raised below, after the others
                    error = error or exc
                    continue
                apply(name, seg, clock)
                done += 1
                minutes = (time.time() - t0) / 60
                print(f"[{done}/{n}] {minutes:.1f} min, {done / max(minutes, 1e-9):.2f} "
                      f"segments/min", flush=True)
    finally:
        pool.shutdown(wait=True, cancel_futures=True)
    if error is not None:
        raise error
    return failed + len(queue)


def take_infos(
    src: Source, slug: str, lib: dict[str, Any], names: list[str], files: set[str],
    libdir: Path, archive: Archive | None,
) -> None:
    """The <name>.info.json files of a dataset's games into LIBDIR/info (from the archive when
    one is open, else one download each)."""
    info_dir, tmp = libdir / "info", libdir / "tmp"
    for name in names:
        raw = lib["games"][name].get("file_name", name)
        info, out = f"{raw}.info.json", info_dir / f"{name}.info.json"
        if info in files and not out.exists():
            try:
                info_dir.mkdir(exist_ok=True)
                got = (archive.extract(info, tmp) if archive and info in archive.members
                       else src.fetch(slug, info, tmp))
                got.replace(out)
            except Exception as exc:  # noqa: BLE001 - descriptions are optional
                print(f"  {info}: {str(exc)[:160]}", flush=True)
        lib["games"][name]["info_json"] = out.exists()


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
    todo, covered = todo_segments(lib, names, ingest_games(a.ingest))
    missing = [(n, s) for n, s in todo if s["file"] not in files]
    todo = [(n, s) for n, s in todo if s["file"] in files]
    ds.update({"status": "pending", "last_updated": stamp, "games": names,
               "covered_by_ingest": covered, "missing_files": [s["file"] for _, s in missing]})
    print(f"{slug}: {len(names)} games, {len(todo)} segments to read, {covered} already read by "
          f"the ingest, {len(missing)} missing", flush=True)
    save(libdir, lib)
    failed = 0
    if not todo:
        take_infos(src, slug, lib, names, files, libdir, None)
    elif free_gb(libdir) < a.min_free_gb:
        print(f"only {free_gb(libdir):.1f} GB free, stopping this pass", flush=True)
        failed = len(todo)
    else:
        with src.open_archive(slug, tmp, a.min_free_gb) as arch:
            take_infos(src, slug, lib, names, files, libdir, arch)
            save(libdir, lib)
            # from the end of the zip, so that a local zip can be cut back behind each segment
            jobs = sorted(todo, key=lambda j: arch.offset(j[1]["file"]), reverse=True)

            def take(name: str, seg: dict[str, Any]) -> Path:
                if free_gb(libdir) < a.min_free_gb:
                    raise LowDiskError(f"only {free_gb(libdir):.1f} GB free")
                return arch.extract(seg["file"], tmp, cut=True)

            def apply(name: str, seg: dict[str, Any], clock: dict[str, Any]) -> None:
                set_clock(lib["games"][name], seg, clock)
                save(libdir, lib)

            failed = read_parallel(jobs, take, apply, a.workers)
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
    ap.add_argument("--min-free-gb", type=float, default=1.5,
                    help="disk to keep free (a batch zip is downloaded only with this to spare)")
    ap.add_argument("--workers", type=int, default=WORKERS, help="clock readers at once")
    a = ap.parse_args()
    os.environ.setdefault("HANDBALL_CLOCK_THREADS", "1")  # one thread per reader (OMP, decoder, OCR)
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
