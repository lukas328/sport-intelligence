"""Ball test set 2 (gold v2, 2026-11-25): single frames for a ring-free ball test.

Where from: the 42 games of test set 2 (`ml/ball/test_games.json`, 42 halls never in any ball
training; the same games as the shot end test). Per game the segments that hold neither the gold v1
clip (`ml/gold/gold_clips.json`) nor the shot end-test segment (`ml/gold/shot_endtest_segments.json`):
3 segments per game. 7 frames per game, segment and time drawn at random (seed 20261125), at
least 3 s from the segment's edges and 20 s apart within a segment, whatever is on screen (play,
stoppages, replays): frames without a ball count too, so false alarms become measurable.

The owner labels each frame without any detector ring (page `labelling/balltest2.html`,
https://claude.ai/artifact/XHMwGf3yff6zXy7xuMNt1C, db collection `labels`): click the
ball, or "partly hidden", "not visible (hidden)", "no ball in the picture", "unsure".

usage:
  python ml/gold/pick_ball_test2.py pick AVAIL.json VIDEOS_DIR OUT.json
  python ml/gold/pick_ball_test2.py frames OUT.json VIDEOS_DIR PAGE_DIR
AVAIL.json: {game: [[dataset, file, size], ...]} of the allowed segments.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import cv2
import numpy as np

SEED = 20261125
PER_GAME = 7
EDGE_S = 3.0
APART_S = 20.0


def pick(avail_path: Path, videos: Path, out: Path) -> None:
    avail = json.loads(avail_path.read_text())
    rng = random.Random(SEED)
    frames = []
    for game in sorted(avail):
        segs = []
        for dataset, file, _ in sorted(avail[game], key=lambda x: x[1]):
            cap = cv2.VideoCapture(str(videos / file))
            fps = cap.get(cv2.CAP_PROP_FPS)
            n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            cap.release()
            if fps > 0 and n / fps > 2 * EDGE_S + 1:
                segs.append((dataset, file, fps, n))
        taken: list[tuple[str, float]] = []
        tries = 0
        while len(taken) < PER_GAME and tries < 1000:
            tries += 1
            dataset, file, fps, n = rng.choice(segs)
            t = rng.uniform(EDGE_S, n / fps - EDGE_S)
            if any(f == file and abs(t - u) < APART_S for f, u in taken):
                continue
            taken.append((file, t))
            frames.append(
                {
                    "id": f"b{len(frames):03d}",
                    "game": game,
                    "dataset": dataset,
                    "file": file,
                    "fps": round(fps, 3),
                    "frame": round(t * fps),
                    "t_s": round(round(t * fps) / fps, 3),
                }
            )
    out.write_text(
        json.dumps(
            {
                "note": "Ball test set 2 (gold v2): frames of the 42 test set 2 games outside the gold v1 "
                "clip and shot end-test segments, ml/gold/pick_ball_test2.py, seed 20261125. "
                "Labels by the owner without detector rings. Frozen once labelling starts: no "
                "development, tuning or training on it.",
                "frames": frames,
            },
            indent=1,
        )
    )
    print(len(frames))


def extract(frames_path: Path, videos: Path, page: Path) -> None:
    """Per frame one image s/NNN.jpg: the frame at 1280 px on top, below it the frames 2 steps
    before and after (1 step below 40 fps) side by side at 640 px each, to see the ball move;
    items.json for the page."""
    frames = json.loads(frames_path.read_text())["frames"]
    (page / "s").mkdir(parents=True, exist_ok=True)
    items = []
    for fr in frames:
        cap = cv2.VideoCapture(str(videos / fr["file"]))
        step = 2 if fr["fps"] > 40 else 1
        got = {}
        for key, off in (("p", -step), ("f", 0), ("n", step)):
            cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, fr["frame"] + off))
            ok, img = cap.read()
            if ok:
                got[key] = cv2.resize(img, (1280, round(img.shape[0] * 1280 / img.shape[1])))
        cap.release()
        if "f" not in got:
            continue
        top = got["f"]
        half = [cv2.resize(got.get(k, np.zeros_like(top)), (640, top.shape[0] // 2)) for k in ("p", "n")]
        sheet = np.vstack([top, np.hstack(half)])
        cv2.imwrite(str(page / "s" / f"{fr['id'][1:]}.jpg"), sheet, [cv2.IMWRITE_JPEG_QUALITY, 86])
        items.append({"id": fr["id"], "game": fr["game"], "w": 1280, "h": top.shape[0]})
    (page / "items.json").write_text(json.dumps(items))
    print(len(items))


if __name__ == "__main__":
    if sys.argv[1] == "pick":
        pick(Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]))
    else:
        extract(Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]))
