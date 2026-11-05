"""Halves, labels and the clocks.json merge of ml/data/segment_clock.py (synthetic readings), and
the clock read of a real clip when it is available locally."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from segment_clock import (
    CLOCK_READER,
    MODELS,
    REPO,
    clock_reader,
    game_labels,
    labels,
    merge_clocks,
    read_segment_clock,
    segment_halves,
)


def running(c0_s: int, c1_s: int, every_s: int = 5, v0_ms: int = 0) -> list[list[float]]:
    return [[v0_ms + (c - c0_s) * 1000, float(c)] for c in range(c0_s, c1_s + 1, every_s)]


def seg(k: int, start_s: float, samples: list[list[float]], source: str = "overlay") -> dict[str, Any]:
    return {
        "file": f"g_s{k}.mp4",
        "start_s": start_s,
        "clock": {"source": source if samples else None, "samples": samples},
    }


def log_entry(t: int, action: str = "Tor", result: str = "1:0") -> dict[str, Any]:
    return {
        "actionGroup": 1, "actionText": action, "homeTeamPlayerStaffName": "A B",
        "homeTeamPlayerStaffNrDesc": "7", "awayTeamPlayerStaffName": "",
        "awayTeamPlayerStaffNrDesc": "", "result": result, "timeInt": t,
        "timeString": f"{t // 60:02d}:{t % 60:02d}",
    }


def test_restarting_second_half_is_found_from_the_drop_between_segments() -> None:
    segs = [
        seg(0, 900, running(600, 780)),  # first half 10:00-13:00
        seg(1, 4000, running(300, 480)),  # clock restarted: 05:00 is 35:00
        seg(2, 5000, []),
    ]
    assert segment_halves(segs) == [(1, True), (2, True), (1, False)]


def test_first_half_clock_without_a_second_half_in_view_is_uncertain() -> None:
    assert segment_halves([seg(0, 900, running(600, 780))]) == [(1, False)]
    # a continuing second half (30-60) is certain on its own
    assert segment_halves([seg(0, 4000, running(2100, 2280))]) == [(2, True)]


def test_labels_place_entries_with_segment_ms_and_video_offset() -> None:
    game = {
        "duration_s": 6000.0,
        "segments": [seg(0, 900, running(600, 780, v0_ms=2000)), seg(1, 4000, running(300, 480))],
    }
    official = {
        "log": [log_entry(650), log_entry(2000, "Wurf Parade", "1:0"), log_entry(2100, result="2:0"),
                log_entry(30 * 60 + 400, result="3:0")]
    }
    out = game_labels("g", game, official)
    placed = [(e["segment"], e["segment_ms"], e["video_ms"], e["kind"]) for e in out["entries"]]
    assert placed == [
        ("g_s0.mp4", 52_000, 952_000, "goal"),  # 50 s after 10:00, which shows at 2 s
        ("g_s1.mp4", 0, 4_000_000, "goal"),  # 35:00 shows as 05:00 (restarted clock)
        ("g_s1.mp4", 100_000, 4_100_000, "goal"),  # 36:40 = 06:40
    ]  # the save at 33:20 is 100 s before the first reading: not placed
    assert out["entries"][0]["anchor_gap_s"] == 0
    assert out["counts"] == {"goal": 3}
    assert [s["entries"] for s in out["segments"]] == [1, 2]


def test_merge_fills_only_segments_without_clock() -> None:
    state: dict[str, Any] = {"games": {"g": {"segments": [
        {"file": "a.mp4"}, {"file": "b.mp4", "clock": {"source": None, "samples": []}}
    ]}}}
    side = {"g": {"a.mp4": {"source": "overlay", "samples": [[0, 1.0], [5000, 6.0]]},
                  "b.mp4": {"source": "overlay", "samples": [[0, 1.0]]}}, "other": {}}
    assert merge_clocks(state, side) == 1
    g = state["games"]["g"]
    assert g["segments"][0]["clock"]["source"] == "overlay"
    assert g["segments"][1]["clock"]["source"] is None
    assert g["has_clock"] is True


def test_merge_replaces_clock_data_of_an_older_reader() -> None:
    old = {"source": "hall_board", "samples": [[0, 960.0], [2000, 960.0]]}  # reader 1
    new = {"source": "overlay", "samples": [[0, 11.0], [2000, 13.0]], "reader": CLOCK_READER}
    state: dict[str, Any] = {"games": {"g": {"segments": [
        {"file": "a.mp4", "clock": old},
        {"file": "b.mp4", "clock": new},
    ]}}}
    side = {"g": {"a.mp4": new, "b.mp4": old}}
    assert merge_clocks(state, side) == 1
    assert [s["clock"] for s in state["games"]["g"]["segments"]] == [new, new]
    assert clock_reader(None) == 0 and clock_reader(old) == 1


def test_labels_writes_games_with_log_and_clock(tmp_path: Path) -> None:
    work, off, out = tmp_path / "w", tmp_path / "off", tmp_path / "out"
    work.mkdir()
    off.mkdir()
    state = {"batch": 2, "games": {
        "with": {"duration_s": 3000.0, "segments": [seg(0, 900, running(600, 780))]},
        "nolog": {"duration_s": 3000.0, "segments": [seg(0, 900, running(600, 780))]},
        "noclock": {"duration_s": 3000.0, "segments": [{"file": "x.mp4", "start_s": 0}]},
    }}
    (work / "state.json").write_text(json.dumps(state))
    for n, log in (("with", [log_entry(700)]), ("nolog", []), ("noclock", [log_entry(700)])):
        (off / f"{n}.json").write_text(json.dumps({"log": log}))
    written = labels(work, out, off)
    assert [p.name for p in written] == ["with.json"]
    assert json.loads(written[0].read_text())["entries"][0]["segment_ms"] == 100_000


CLIP = REPO / "data" / "videos" / "ch-spl2-2024-leimental-arbon.mp4"


@pytest.mark.skipif(
    not CLIP.exists() or not (MODELS / "ch_PP-OCRv4_rec_infer.onnx").exists(),
    reason="test clip or PP-OCR models missing",
)
def test_overlay_clock_of_the_leimental_clip() -> None:
    r = read_segment_clock(CLIP)
    assert r["source"] == "overlay" and r["reader"] == CLOCK_READER
    s = r["samples"]
    assert len(s) >= 100  # 5 minutes, a reading every 2 s
    assert all(b[0] - a[0] >= 1900 for a, b in zip(s, s[1:], strict=False))  # at most every 2 s
    # the clip shows the match clock from about 02:00 to 07:00
    assert 100 <= s[0][1] <= 150 and 400 <= s[-1][1] <= 440


def test_plausible_needs_a_running_or_a_standing_clock() -> None:
    from segment_clock import plausible

    run = [(v, c) for v, c in running(600, 700)]
    assert plausible(run)
    assert plausible([(0, 190.0), (5000, 190.0), (10000, 190.0)])  # time-out: stands still
    slow = [(k * 5000, 190.0 + k // 6) for k in range(36)]  # one "second" per 30 s
    assert not plausible(slow)
    assert not plausible([(0, 100.0)])


def test_clean_drops_a_misread_twice_in_a_row_but_keeps_a_half_restart() -> None:
    from segment_clock import clean

    a = [(k * 2000, 2267.0 + k * 2) for k in range(10)]  # running 37:47 ...
    bad = [(20_000, 2390.0), (22_000, 2392.0)]  # "39:50", "39:52" read for 37:xx
    b = [(24_000 + k * 2000, 2291.0 + k * 2) for k in range(10)]
    assert clean([*a, *bad, *b]) == [*a, *b]
    restart = [(0, 1795.0), (2000, 1797.0), (60_000, 0.0), (62_000, 2.0)]  # 2nd half from 0
    assert clean(restart) == restart


def test_entry_at_a_clock_stopped_since_the_segment_start_is_left_out() -> None:
    stopped = [[k * 5000, 2267.0] for k in range(13)]  # 37:47 for a minute
    run = [[65_000 + k * 5000, 2267.0 + k * 5] for k in range(20)]
    game = {"duration_s": 7000.0, "segments": [seg(0, 4900, stopped + run)]}
    out = game_labels("g", game, {"log": [log_entry(2267), log_entry(2300, result="2:0")]})
    assert [(e["match_s"], e["segment_ms"]) for e in out["entries"]] == [(2300, 98_000)]
    assert out["segments"][0]["skipped_at_stopped_start"] == 1


class _FieldOcr:
    """Fake PP-OCR for synthetic frames: every text field is a flat box of a grey level of its own;
    detection returns one box per field in view, recognition that field's text at time `t`."""

    def __init__(self, fields: dict[int, Any]) -> None:
        self.fields = fields  # grey level -> text at a time (ms)
        self.t = 0

    def detect(self, img: Any) -> list[Any]:
        import numpy as np

        out = []
        for level in self.fields:
            ys, xs = np.nonzero(img[..., 0] == level)
            if len(xs) >= 50:
                x1, x2, y1, y2 = xs.min(), xs.max(), ys.min(), ys.max()
                out.append(np.array([[x1, y1], [x2, y1], [x2, y2], [x1, y2]], np.float32))
        return out

    def recognise(self, crops: list[Any]) -> list[tuple[str, float]]:
        import numpy as np

        res = []
        for c in crops:
            levels, counts = np.unique(c[..., 0], return_counts=True)
            known = [(n, int(v)) for v, n in zip(levels, counts, strict=True) if int(v) in self.fields]
            res.append((self.fields[max(known)[1]](self.t), 0.95) if known else ("", 0.0))
        return res


def _graphic_frames(ocr: _FieldOcr, boxes: dict[int, tuple[int, int, int, int]], n_s: int):
    """(ms, frame) every 250 ms of a fixed camera with a stream graphic: the fields as flat boxes
    on a textured background."""
    import numpy as np

    rng = np.random.default_rng(3)
    base = rng.integers(0, 60, (360, 640, 3), dtype=np.uint8)
    for level, (x1, y1, x2, y2) in boxes.items():
        base[y1:y2, x1:x2] = level
    for t in range(0, n_s * 1000, 250):
        ocr.t = t
        yield t, base.copy()


def _mmss(s: int) -> str:
    return f"{s // 60:02d}:{s % 60:02d}"


@pytest.mark.parametrize("score_text", ["{h}:{a}", "SGW {h} : {a} GOS"])
def test_stacked_stream_graphic_gives_the_running_clock_not_score_or_timer(
    monkeypatch: pytest.MonkeyPatch, score_text: str
) -> None:
    """SG Waedenswil/Horgen graphic: the score above the clock, a penalty timer counting down
    beside the clock. The old per-frame pick (most confident, tallest `mm:ss`) took timer or score."""
    import segment_clock as sc

    def score(t: int) -> str:
        h, a = (19, 16) if t < 40_000 else (20, 16)
        return score_text.format(h=h, a=a)

    wide = "SGW" in score_text
    ocr = _FieldOcr({
        120: score,
        160: lambda t: _mmss(2546 + t // 1000),  # 42:26 running
        200: lambda t: f"{max(0, 98 - t // 1000) // 60}:{max(0, 98 - t // 1000) % 60:02d}",
    })
    boxes = {
        120: (230, 40, 420, 70) if wide else (290, 40, 360, 70),  # score (with codes: wide)
        160: (290, 80, 360, 110),  # clock
        200: (365, 80, 415, 110),  # 2-minute timer beside it
    }
    monkeypatch.setattr(sc, "frames", lambda path, every_ms=0, skip="NONREF": _graphic_frames(
        ocr, boxes, 60))
    samples, reader = sc.read_clock(Path("x.mp4"), ocr, 2.0, budget_s=1e9, give_up=True)
    assert reader.stacked == "above"
    assert len(samples) >= 28
    assert all(c == 2546 + v // 1000 for v, c in samples)  # the clock field on every reading
    assert sc.plausible(sc.clean(samples))


def test_a_standing_field_without_score_is_no_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    """The half-time graphic "Pausenstand 11 : 17" reads as a lone, standing "11:17"."""
    import segment_clock as sc

    ocr = _FieldOcr({120: lambda t: "11:17"})
    monkeypatch.setattr(sc, "frames", lambda path, every_ms=0, skip="NONREF": _graphic_frames(
        ocr, {120: (250, 150, 390, 190)}, 30))
    samples, reader = sc.read_clock(Path("x.mp4"), ocr, 2.0, budget_s=1e9)
    assert len(samples) >= 10 and {c for _, c in samples} == {677.0}
    assert sc.plausible(samples) and not sc.with_score(reader)
    assert not sc.plausible(samples, standing_ok=sc.with_score(reader))
