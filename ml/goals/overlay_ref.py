"""Reference only (the detector must work without overlays): when does the score bug change?

The score digits of the broadcast bug (bottom centre) are static except when a goal is given. For
each cached clip the change time is the first thumbnail whose digit regions are closer to the
clip's last state than to its first one; a clip whose digits never change gets `None`.
Writes overlay_ref.json {clip: {"change_s": seconds from clip start or None, "jump": size}}.

usage: python ml/goals/overlay_ref.py CACHE_DIR
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

# digit regions inside the bug crop (rows 0.86..0.93 h, cols 0.36..0.64 w of a 1280x720 frame)
REGIONS = [(slice(11, 41), slice(80, 136)), (slice(11, 41), slice(230, 285))]


def change_time(bugs: np.ndarray, idx: np.ndarray, fps: float) -> tuple[float | None, float]:
    """(change time in clip seconds or None, share of digit pixels that changed in %)."""
    b = bugs.astype(np.int32)
    # yellow digits on the dark bug (BGR): binarise, compression noise then hardly matters
    m = (b[..., 2] > 140) & (b[..., 1] > 110) & (b[..., 0] < 110)
    best: tuple[float | None, float] = (None, 0.0)
    for rs, cs in REGIONS:
        r = m[:, rs, cs].astype(np.float32)
        head, tail = r[:5].mean(axis=0) > 0.5, r[-5:].mean(axis=0) > 0.5
        jump = float((head != tail).mean() * 100)
        if jump < 2.5 or jump <= best[1]:
            continue
        d0 = (r != head).mean(axis=(1, 2))
        d1 = (r != tail).mean(axis=(1, 2))
        closer = d1 < d0
        # first index from which the tail state holds (allow a flicker or two)
        k = next((i for i in range(len(closer)) if closer[i:].mean() > 0.9), None)
        if k is not None:
            best = (float(idx[k] / fps), jump)
    return best


def main() -> None:
    cache = Path(sys.argv[1])
    out = {}
    for f in sorted(cache.glob("*.npz")):
        z = np.load(f)
        t, jump = change_time(z["bugs"], z["thumb_idx"], float(z["fps"]))
        out[f.stem] = {"change_s": t, "jump": round(jump, 1)}
        print(f.stem, out[f.stem])
    (cache / "overlay_ref.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
