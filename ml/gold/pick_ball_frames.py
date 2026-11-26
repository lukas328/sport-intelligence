"""Single frames for ring-free ball labels (plan docs/plans/ballnetz-ohne-deepsport.md step 0):
the same rules as `pick_ball_test2.py` (random segment and time, at least 3 s from the edges,
20 s apart, whatever is on screen), with the number per game, the seed, the id prefix and frames
to keep away from (another set's frames, 20 s) as arguments.

Two uses:
- the extension of ball test 2 (the 42 test games, outside gold v1, the shot end test and the
  existing ball test 2 frames): only labelled and frozen, measured once at the end;
- the validation set of training-side games (never in any ball training, not of a test hall):
  all analysis and decisions of the plan.

usage:
  python ml/gold/pick_ball_frames.py AVAIL.json VIDEOS_DIR OUT.json PER_GAME SEED PREFIX [AVOID.json]
then `python ml/gold/pick_ball_test2.py frames OUT.json VIDEOS_DIR PAGE_DIR` for the images.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import cv2

EDGE_S = 3.0
APART_S = 20.0


def main() -> None:
    avail = json.loads(Path(sys.argv[1]).read_text())
    videos, out = Path(sys.argv[2]), Path(sys.argv[3])
    per_game, seed, prefix = int(sys.argv[4]), int(sys.argv[5]), sys.argv[6]
    avoid = json.loads(Path(sys.argv[7]).read_text())["frames"] if len(sys.argv) > 7 else []
    rng = random.Random(seed)
    frames = []
    for game in sorted(avail):
        segs = []
        for dataset, file, *_ in sorted(avail[game], key=lambda x: x[1]):
            cap = cv2.VideoCapture(str(videos / file))
            fps, n = cap.get(cv2.CAP_PROP_FPS), int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            cap.release()
            if fps > 0 and n / fps > 2 * EDGE_S + 1:
                segs.append((dataset, file, fps, n))
        if not segs:
            continue
        taken = [(a["file"], a["t_s"]) for a in avoid if a["game"] == game]
        mine = 0
        for _ in range(5000):
            if mine >= per_game:
                break
            dataset, file, fps, n = rng.choice(segs)
            t = rng.uniform(EDGE_S, n / fps - EDGE_S)
            if any(f == file and abs(t - u) < APART_S for f, u in taken):
                continue
            taken.append((file, t))
            mine += 1
            frames.append(
                {
                    "id": f"{prefix}{len(frames):03d}",
                    "game": game,
                    "dataset": dataset,
                    "file": file,
                    "fps": round(fps, 3),
                    "frame": round(t * fps),
                    "t_s": round(round(t * fps) / fps, 3),
                }
            )
    note = f"ml/gold/pick_ball_frames.py, {per_game} per game, seed {seed}, prefix {prefix}"
    out.write_text(json.dumps({"note": note, "frames": frames}, indent=1))
    print(len(frames))


if __name__ == "__main__":
    main()
