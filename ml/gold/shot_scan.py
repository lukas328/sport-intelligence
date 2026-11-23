"""Shot end test: find shots in never-trained halls by looking, not by any detector (research, ml/).

The frozen shot end test (docs/plans/tracking-strategie.md section 9, priority 1) needs at least 100
shots from at least 15 halls that were never in any ball training: the 42 halls of ball test set 2
(ml/ball/test_games.json). Only 2 of these games have an official log, so shots are found by eye:

    python ml/gold/shot_scan.py pick LIBRARY_JSON            # one segment per game -> shot_endtest_segments.json
    python ml/gold/shot_scan.py sheets SEGMENT_MP4 OUT_DIR   # 1 frame per second, 4 x 4 tiles per sheet
    python ml/gold/shot_scan.py zoom SEGMENT_MP4 T_S OUT_DIR # 5 frames per second from T_S - 3 to T_S + 3 s
    python ml/gold/shot_scan.py clips ANSWERS_JSON           # confirmed shots -> shot_endtest_clips.json
    python ml/gold/shot_scan.py cands OBS_DIR OUT_JSON [--rate 2]   # product shot candidates per segment
    python ml/gold/shot_scan.py view SEGMENT_MP4 T_S OUT_DIR  # 5 fps, 640 px tiles, T_S - 4 to T_S + 2 s
    python ml/gold/shot_scan.py crop SEGMENT_MP4 T0 T1 X Y W OUT_JPG [--fps 15]  # full-resolution crop

The pilot (3 segments by eye at 1 fps) found 1 shot: attacks fall between the tiles, and 426 px
tiles at 5 fps rarely show the ball. So the candidates come from the product's shot candidates
(handball_vision.goalcandidates: camera pan and people motion, no ball detector; 83 % of the
logged shots at 2 per minute, ml/goals/README.md), computed from the product observation pass
(ml/goals/product_path.py observe --cheap); the eye then confirms each candidate with view and crop.

pick: per game one segment drawn with a fixed seed among those without the gold v1 clip, so no scene
is in both. sheets: tiles 320 x 180 with the second in the corner; a looker lists the seconds where
a shot on goal may happen (attack at the 6 m line, then the keeper with the ball, the ball in the
net, a restart from the goal or the keeper's throw). zoom: the candidate at 5 fps (426 x 240 tiles)
to confirm it and give the release time. clips: each confirmed shot becomes a clip from 4 s before
to 2 s after the release, split "test" (frozen; whole set).
"""

import argparse
import json
import random
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
PRE, POST = 4000, 2000


def pick(a: argparse.Namespace) -> None:
    lib = json.loads(a.library.read_text())["games"]
    test = json.loads((HERE.parent / "ball" / "test_games.json").read_text())
    names = [t if isinstance(t, str) else t["name"] for t in (test if isinstance(test, list) else test["games"])]
    gold = {c["game"]: c["file"] for c in json.loads((HERE / "gold_clips.json").read_text())["clips"]}
    rnd = random.Random(a.seed)
    out = []
    for n in sorted(names):
        g = lib[n]
        segs = sorted(s["file"] for s in g["segments"] if s["file"] != gold.get(n))
        out.append({"game": n, "dataset": g["kaggle_dataset"], "file": rnd.choice(segs), "fps": g.get("fps")})
    (HERE / "shot_endtest_segments.json").write_text(json.dumps(out, indent=1) + "\n")
    print(len(out), "segments")


def _grid(tiles: list, cols: int) -> np.ndarray:
    h, w = tiles[0].shape[:2]
    while len(tiles) % cols:
        tiles.append(np.zeros((h, w, 3), np.uint8))
    return np.vstack([np.hstack(tiles[i:i + cols]) for i in range(0, len(tiles), cols)])


def _label(im: np.ndarray, text: str) -> None:
    for col, th in (((0, 0, 0), 3), ((255, 255, 255), 1)):
        cv2.putText(im, text, (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, col, th)


def sheets(a: argparse.Namespace) -> None:
    cap = cv2.VideoCapture(str(a.segment))
    fps = cap.get(cv2.CAP_PROP_FPS)
    a.out.mkdir(parents=True, exist_ok=True)
    stem = a.segment.stem
    tiles, k, sec, n = [], 0, 0, 0
    while True:
        ok, im = cap.read()
        if not ok:
            break
        if k >= sec * fps:
            t = cv2.resize(im, (320, 180), interpolation=cv2.INTER_AREA)
            _label(t, f"{sec} s")
            tiles.append(t)
            sec += 1
            if len(tiles) == 16:
                cv2.imwrite(str(a.out / f"{stem}_{n:02d}.jpg"), _grid(tiles, 4), [cv2.IMWRITE_JPEG_QUALITY, 85])
                tiles, n = [], n + 1
        k += 1
    if tiles:
        cv2.imwrite(str(a.out / f"{stem}_{n:02d}.jpg"), _grid(tiles, 4), [cv2.IMWRITE_JPEG_QUALITY, 85])
        n += 1
    print(stem, sec, "s,", n, "sheets")


def zoom(a: argparse.Namespace) -> None:
    cap = cv2.VideoCapture(str(a.segment))
    fps = cap.get(cv2.CAP_PROP_FPS)
    a.out.mkdir(parents=True, exist_ok=True)
    t0 = max(0.0, a.t - 3)
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(round(t0 * fps)))
    tiles, k, step = [], 0, fps / 5
    nxt = 0.0
    while len(tiles) < 30:
        ok, im = cap.read()
        if not ok:
            break
        if k >= nxt:
            t = cv2.resize(im, (426, 240), interpolation=cv2.INTER_AREA)
            _label(t, f"{t0 + k / fps:.1f} s")
            tiles.append(t)
            nxt += step
        k += 1
    stem = f"{a.segment.stem}_{a.t:.0f}"
    for i in range(0, len(tiles), 12):
        cv2.imwrite(str(a.out / f"{stem}_z{i // 12}.jpg"), _grid(tiles[i:i + 12], 3), [cv2.IMWRITE_JPEG_QUALITY, 88])
    print(stem, len(tiles), "frames")


def clips(a: argparse.Namespace) -> None:
    segs = {s["file"]: s for s in json.loads((HERE / "shot_endtest_segments.json").read_text())}
    shots = json.loads(a.answers.read_text())  # [{file, release_s, kind}]
    out = []
    for s in sorted(shots, key=lambda x: (x["file"], x["release_s"])):
        g = segs[s["file"]]
        out.append({"id": f"e{len(out):03d}", "game": g["game"], "dataset": g["dataset"], "file": s["file"],
                    "start_ms": round(s["release_s"] * 1000) - PRE, "dur_ms": PRE + POST, "fps": g["fps"],
                    "width": 1280, "height": 720,
                    "shot": {"kind": s.get("kind", "shot"), "release_ms": PRE}, "split": "test"})
    note = ("Shot end test: shots found by eye in the 42 never-trained halls of test set 2 "
            "(ml/gold/shot_scan.py). Frozen: no development or tuning on it; measured once at the end.")
    (HERE / "shot_endtest_clips.json").write_text(json.dumps({"note": note, "clips": out}, indent=1) + "\n")
    print(len(out), "clips from", len({c["game"] for c in out}), "halls")


def cands(a: argparse.Namespace) -> None:
    from handball_vision import goalcandidates as gc
    from handball_vision import observe as ob
    from handball_vision.motion import CameraMotion

    out = {}
    for f in sorted(a.obs.glob("*.obs.npz")):
        stem = f.name[: -len(".obs.npz")]
        obs = ob.load_observations(f, CameraMotion.load(a.obs / f"{stem}.motion.npz"))
        res = gc.from_observations(obs)
        shots = (res or {}).get("shots") or {}
        out[stem] = [{"t_s": c["goal_ms"] / 1000, "score": c["score"], "rank": c["rank"]}
                     for c in shots.get("candidates", []) if c["rate"] <= a.rate]
    a.out.write_text(json.dumps(out, indent=1))
    print(len(out), "segments,", sum(len(v) for v in out.values()), "candidates at", a.rate, "per minute")


def _frames(path: Path, t0: float, t1: float, fps_out: float):
    cap = cv2.VideoCapture(str(path))
    fps = cap.get(cv2.CAP_PROP_FPS)
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(round(max(0.0, t0) * fps)))
    k, nxt, t = int(round(max(0.0, t0) * fps)), max(0.0, t0), 0.0
    while True:
        ok, im = cap.read()
        if not ok:
            break
        t = k / fps
        if t > t1:
            break
        if t >= nxt - 0.5 / fps:
            yield t, im
            nxt += 1 / fps_out
        k += 1


def view(a: argparse.Namespace) -> None:
    a.out.mkdir(parents=True, exist_ok=True)
    tiles = []
    for t, im in _frames(a.segment, a.t - 4, a.t + 2, 5):
        tile = cv2.resize(im, (640, 360), interpolation=cv2.INTER_AREA)
        _label(tile, f"{t:.1f} s")
        tiles.append(tile)
    stem = f"{a.segment.stem}_{a.t:.1f}"
    for i in range(0, len(tiles), 6):
        cv2.imwrite(str(a.out / f"{stem}_v{i // 6}.jpg"), _grid(tiles[i:i + 6], 2), [cv2.IMWRITE_JPEG_QUALITY, 88])
    print(stem, len(tiles), "frames in", (len(tiles) + 5) // 6, "sheets")


def crop(a: argparse.Namespace) -> None:
    tiles = []
    for t, im in _frames(a.segment, a.t0, a.t1, a.fps):
        h, w = im.shape[:2]
        x0 = int(min(max(0, a.x - a.w // 2), w - a.w)); y0 = int(min(max(0, a.y - a.w * 9 // 32), h - a.w * 9 // 16))
        c = im[y0:y0 + a.w * 9 // 16, x0:x0 + a.w]
        c = cv2.resize(c, (480, 270), interpolation=cv2.INTER_CUBIC)
        _label(c, f"{t:.2f} s")
        tiles.append(c)
    tiles = tiles[:24]
    cv2.imwrite(str(a.out), _grid(tiles, 4), [cv2.IMWRITE_JPEG_QUALITY, 90])
    print(a.out, len(tiles), "frames (at most 24)")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pick")
    p.add_argument("library", type=Path)
    p.add_argument("--seed", type=int, default=2026)
    p = sub.add_parser("sheets")
    p.add_argument("segment", type=Path)
    p.add_argument("out", type=Path)
    p = sub.add_parser("zoom")
    p.add_argument("segment", type=Path)
    p.add_argument("t", type=float)
    p.add_argument("out", type=Path)
    p = sub.add_parser("clips")
    p.add_argument("answers", type=Path)
    p = sub.add_parser("cands")
    p.add_argument("obs", type=Path)
    p.add_argument("out", type=Path)
    p.add_argument("--rate", type=int, default=2)
    p = sub.add_parser("view")
    p.add_argument("segment", type=Path)
    p.add_argument("t", type=float)
    p.add_argument("out", type=Path)
    p = sub.add_parser("crop")
    p.add_argument("segment", type=Path)
    p.add_argument("t0", type=float)
    p.add_argument("t1", type=float)
    p.add_argument("x", type=int)
    p.add_argument("y", type=int)
    p.add_argument("w", type=int, help="crop width in frame px (height = w * 9 / 16)")
    p.add_argument("out", type=Path)
    p.add_argument("--fps", type=float, default=15)
    a = ap.parse_args()
    {"pick": pick, "sheets": sheets, "zoom": zoom, "clips": clips, "cands": cands, "view": view, "crop": crop}[a.cmd](a)


if __name__ == "__main__":
    main()
