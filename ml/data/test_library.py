"""Names, dataset slugs, merging and resumability of ml/data/library.py (no network, no clock
reader: the reader is replaced by a stub)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))

import library
from library import (
    CLOCK_READER,
    MAX_ATTEMPTS,
    LocalSource,
    add_index,
    base_name,
    canonical_name,
    dataset_of,
    dataset_slug,
    known_names,
    merge_games,
    needs_visit,
    new_library,
    run_once,
    set_clock,
    todo_segments,
)
from segment_clock import all_games, labels

GAME = "CH_NLB_SGWaedenswilHorgen_Emmen_2023-09-03"


def clock(reader: int = CLOCK_READER, source: str | None = "overlay") -> dict[str, Any]:
    return {"source": source, "samples": [[0, 600.0], [2000, 602.0]] if source else [],
            "reader": reader}


def index_entry(name: str, n: int = 2, batch: str = "batch_l01") -> dict[str, Any]:
    return {"duration_s": 3600.0, "width": 1280, "height": 720, "fps": 30.0, "codec": "h264",
            "batch": batch, "source": "local",
            "segments": [{"file": f"{name}_s{k}.mp4", "start_s": 540.0 * (k + 1)}
                         for k in range(n)]}


# --- names and slugs ----------------------------------------------------------------------------


def test_names_map_to_the_video_list(tmp_path: Path) -> None:
    csv = tmp_path / "videos.csv"
    csv.write_text(f"url;start;end;name\nhttps://x;;;{GAME}\nhttps://y;;;CH_SPL1_Zürich_Brühl_2024-01-01\n",
                   encoding="utf-8")
    known = known_names([csv, tmp_path / "missing.csv"])
    assert canonical_name(GAME, known) == GAME
    assert canonical_name(f"{GAME}.f298", known) == GAME
    assert canonical_name("ch_nlb_sgwaedenswilhorgen_emmen_2023_09_03", known) == GAME
    assert canonical_name("CH_SPL1_Zurich_Bruhl_2024-01-01", known) == "CH_SPL1_Zürich_Brühl_2024-01-01"
    assert canonical_name("Unknown game.f137", known) == "Unknown game"
    assert base_name(" a_b.f12 ") == "a_b" and base_name("a.f12x") == "a.f12x"


def test_dataset_slugs() -> None:
    assert dataset_slug("batch_03") == "handball-segs-b03"
    assert dataset_slug("batch_l07") == "handball-segs-l07"
    assert dataset_slug("batch_l112") == "handball-segs-l112"
    assert dataset_slug("tmp") is None and dataset_slug("") is None
    assert dataset_of({"batch": "batch_01"}) == "handball-segs-b01"
    assert dataset_of({"batch": "batch_l01", "kaggle_dataset": "handball-segs-l09"}) == "handball-segs-l09"
    assert dataset_of(None) is None


# --- merging ------------------------------------------------------------------------------------


def test_merge_prefers_ingest_and_newer_clock() -> None:
    ingest = {
        "both": {"batch": "batch_01", "segments": [
            {"file": "a.mp4", "clock": clock(reader=2)},
            {"file": "b.mp4", "clock": clock()},
        ]},
        "only_ingest": {"batch": "batch_02", "segments": [{"file": "c.mp4"}]},
        "failed": {"error": "probe failed"},
    }
    lib = {
        "both": {"kaggle_dataset": "handball-segs-b01", "segments": [
            {"file": "a.mp4", "clock": clock(source=None)},
            {"file": "b.mp4", "clock": clock(reader=1)},
        ]},
        "failed": {"kaggle_dataset": "handball-segs-l01", "segments": [{"file": "f.mp4"}]},
        "only_lib": {"kaggle_dataset": "handball-segs-l01", "segments": [{"file": "d.mp4"}]},
    }
    before = json.dumps([ingest, lib], sort_keys=True)
    out = merge_games(ingest, lib)
    assert json.dumps([ingest, lib], sort_keys=True) == before  # inputs unchanged
    assert set(out) == {"both", "only_ingest", "failed", "only_lib"}
    a, b = out["both"]["segments"]
    assert a["clock"]["reader"] == CLOCK_READER and a["clock"]["source"] is None  # newer reader
    assert b["clock"] == clock()  # the ingest's current data stays
    assert out["both"]["has_clock"] is True and out["both"]["batch"] == "batch_01"
    assert out["failed"] is lib["failed"]  # an ingest error is replaced by segments
    assert dataset_of(out["only_lib"]) == "handball-segs-l01"


def test_all_games_reads_the_library_beside_the_ingest(tmp_path: Path) -> None:
    work, libdir = tmp_path / "ingest", tmp_path / "library"
    work.mkdir()
    libdir.mkdir()
    (work / "state.json").write_text(json.dumps({"games": {"b": index_entry("b", 1, "batch_01")}}))
    (libdir / "library.json").write_text(json.dumps({"games": {"l": index_entry("l", 1)}}))
    assert set(all_games(work)) == {"b", "l"}
    assert set(all_games(work, tmp_path / "nowhere")) == {"b"}


# --- index, todo, clock -------------------------------------------------------------------------


def test_add_index_is_idempotent_and_keeps_clocks() -> None:
    lib = new_library()
    known = {library.name_key(GAME): GAME}
    idx = {f"{GAME}.f298": index_entry(GAME), "broken": {"error": "x"}}
    assert add_index(lib, "handball-segs-l01", idx, known) == [GAME]
    g = lib["games"][GAME]
    assert g["kaggle_dataset"] == "handball-segs-l01" and g["file_name"] == f"{GAME}.f298"
    set_clock(g, g["segments"][0], clock())
    snapshot = json.dumps(lib, sort_keys=True)
    add_index(lib, "handball-segs-l01", idx, known)
    assert json.dumps(lib, sort_keys=True) == snapshot
    # the same game again in another dataset: stays where it was, listed as duplicate
    assert add_index(lib, "handball-segs-l02", {GAME: index_entry(GAME, batch="batch_l02")}, known) == []
    assert lib["datasets"]["handball-segs-l02"]["duplicates"] == [GAME]
    assert lib["games"][GAME]["kaggle_dataset"] == "handball-segs-l01"


def test_todo_skips_read_covered_and_given_up_segments() -> None:
    lib = new_library()
    add_index(lib, "handball-segs-l01", {"g": index_entry("g", 4)}, {})
    s0, s1, s2, s3 = lib["games"]["g"]["segments"]
    set_clock(lib["games"]["g"], s0, clock())
    ingest = {"g": {"segments": [{"file": s1["file"], "clock": clock()},
                                 {"file": s2["file"], "clock": clock(reader=1)}]}}
    for _ in range(MAX_ATTEMPTS):
        set_clock(lib["games"]["g"], s3, {"source": None, "samples": [], "error": "timeout"})
    todo, covered = todo_segments(lib, ["g"], ingest)
    assert [s["file"] for _, s in todo] == [s2["file"]] and covered == 1
    assert s3["clock_attempts"] == MAX_ATTEMPTS and s3["clock"]["error"] == "timeout"


def test_failed_reading_keeps_older_data() -> None:
    g = {"segments": [{"file": "a.mp4", "clock": clock(reader=1)}]}
    s = g["segments"][0]
    set_clock(g, s, {"source": None, "samples": [], "error": "crash"})
    assert s["clock"]["reader"] == 1 and s["clock_attempts"] == 1
    set_clock(g, s, clock())
    assert s["clock"] == clock() and "clock_attempts" not in s and g["has_clock"] is True


def test_a_renamed_game_is_the_ingest_game() -> None:
    """The ingest keeps "....f298"; the library maps it to the list's name: still one game."""
    lib = new_library()
    known = {library.name_key(GAME): GAME}
    add_index(lib, "handball-segs-b03", {f"{GAME}.f298": index_entry(f"{GAME}.f298", 2)}, known)
    ingest = {f"{GAME}.f298": index_entry(f"{GAME}.f298", 2, "batch_03")}
    for s in ingest[f"{GAME}.f298"]["segments"]:
        s["clock"] = clock()
    todo, covered = todo_segments(lib, [GAME], ingest)
    assert todo == [] and covered == 2
    merged = merge_games(ingest, lib["games"])
    assert list(merged) == [f"{GAME}.f298"] and merged[f"{GAME}.f298"]["batch"] == "batch_03"


def test_needs_visit() -> None:
    assert needs_visit(None, "t1")
    assert needs_visit({"status": "pending", "last_updated": "t1"}, "t1")
    assert not needs_visit({"status": "done", "last_updated": "t1"}, "t1")
    assert needs_visit({"status": "done", "last_updated": "t1"}, "t2")  # new version on Kaggle


# --- the whole run offline (stub clock reader) --------------------------------------------------


def make_dataset(root: Path, slug: str, names: list[str], n: int = 2) -> None:
    d = root / slug
    d.mkdir(parents=True)
    idx = {nm: index_entry(nm, n, f"batch_{slug.rsplit('-', 1)[1]}") for nm in names}
    (d / "index.json").write_text(json.dumps(idx))
    for nm in names:
        (d / f"{nm}.info.json").write_text(json.dumps({"title": nm}))
        for s in idx[nm]["segments"]:
            (d / s["file"]).write_bytes(b"\0" * 10)


def test_run_is_resumable_and_idempotent(tmp_path: Path, monkeypatch: Any) -> None:
    src_dir, libdir, ingest = tmp_path / "kaggle", tmp_path / "lib", tmp_path / "ingest"
    ingest.mkdir()
    make_dataset(src_dir, "handball-segs-l01", ["g1", "g2"])
    calls: list[str] = []
    crash_after = [3]

    def fake_read(path: Path) -> dict[str, Any]:
        assert path.exists() and path.parent == libdir / "tmp"
        if len(calls) == crash_after[0]:
            raise KeyboardInterrupt  # the process dies in the middle of the batch
        calls.append(path.name)
        return clock()

    monkeypatch.setattr(library, "read_clock", fake_read)
    a = argparse.Namespace(libdir=libdir, ingest=ingest, only="", min_free_gb=0.0)
    src = LocalSource(src_dir)
    try:
        run_once(src, a, {})
    except KeyboardInterrupt:
        pass
    assert len(calls) == 3
    lib = json.loads((libdir / "library.json").read_text())
    assert lib["datasets"]["handball-segs-l01"]["status"] != "done"
    assert lib["summary"]["segments_with_clock_data"] == 3
    crash_after[0] = 99
    run_once(src, a, {})  # resumes: only the fourth segment is read
    assert len(calls) == 4 and len(set(calls)) == 4
    lib = json.loads((libdir / "library.json").read_text())
    assert lib["datasets"]["handball-segs-l01"]["status"] == "done"
    assert lib["games"]["g1"]["has_clock"] is True
    assert (libdir / "info" / "g1.info.json").exists()
    assert not list((libdir / "tmp").glob("*.mp4")) if (libdir / "tmp").exists() else True
    assert len(list((src_dir / "handball-segs-l01").glob("*.mp4"))) == 4  # source untouched
    assert run_once(src, a, {}) == 0 and len(calls) == 4  # nothing new: no visit, no reading
    # a new dataset appears: only it is read
    make_dataset(src_dir, "handball-segs-l02", ["g3"], 1)
    run_once(src, a, {})
    assert calls[-1] == "g3_s0.mp4" and len(calls) == 5


def test_labels_for_a_library_game(tmp_path: Path) -> None:
    work, libdir, off, out = (tmp_path / x for x in ("ingest", "library", "off", "out"))
    for d in (work, libdir, off):
        d.mkdir()
    g = index_entry("l", 1)
    g["segments"][0].update(start_s=0.0, clock={
        "source": "overlay", "reader": CLOCK_READER,
        "samples": [[k * 5000, 600.0 + 5 * k] for k in range(37)]})
    (libdir / "library.json").write_text(json.dumps({"games": {"l": g}}))
    entry = {"actionGroup": 1, "actionText": "Tor", "homeTeamPlayerStaffName": "A B",
             "homeTeamPlayerStaffNrDesc": "7", "awayTeamPlayerStaffName": "",
             "awayTeamPlayerStaffNrDesc": "", "result": "1:0", "timeInt": 700, "timeString": "11:40"}
    (off / "l.json").write_text(json.dumps({"log": [entry]}))
    written = labels(work, out, off)
    assert [p.name for p in written] == ["l.json"]
    rows = json.loads(written[0].read_text())["entries"]
    assert len(rows) == 1 and rows[0]["segment_ms"] == 100_000
