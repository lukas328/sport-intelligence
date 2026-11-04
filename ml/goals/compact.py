"""Shrink cached npz files for the streaming check: drop the thumbnails (most of the size) and keep
the goal-area share per thumbnail, which is all `cues.profile_channels` needs from them.

usage: uv run --project packages/vision python ml/goals/compact.py CACHE_DIR
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cues  # noqa: E402

for f in sorted(Path(sys.argv[1]).glob("*.npz")):
    z = np.load(f)
    if "thumbs" not in z:
        continue
    d = {k: z[k] for k in z.files if k != "thumbs"}
    d["zshare"] = cues.zone_masks(z).mean(axis=(1, 2)).astype(np.float32)
    tmp = f.with_suffix(".tmp.npz")
    np.savez_compressed(tmp, **d)
    tmp.replace(f)
    print(f.name, f.stat().st_size // 1024, "KiB")
