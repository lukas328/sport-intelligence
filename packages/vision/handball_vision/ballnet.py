"""3-frame ball net (ONNX) for the product: ball candidates per frame (docs/plans/
produkt-analyse-integration.md step 2).

The nets hr1 (BallHR) and hrp1 (BallHRP, timm HRNet-W18) look at three frames t-G, t, t+G (G = 2
at 25/30 fps, 3 at 50/60 fps) and return a ball heatmap at stride 4; the candidates are its
strongest peaks, as in the research prelabel kernels (`ml/gold/kaggle/prelabel_gpu.py` `peaks()`).
Export: `ml/ball/export_onnx.py` (sigmoid inside the graph, dynamic batch and size). With two
model files the candidates of both are merged (`balltrack2.merge_candidates`), the research
ensemble.

`BallCandidates` keeps a ring buffer of decoded frames so `observe()` can feed every frame once;
the net runs on every `every`-th frame, in batches.

LICENCE NOTE (test phase only): hr1 and hrp1 were trained with DeepSport data (non-commercial,
`ml/ball/LINEAGE.md` section 2, D5). Before a real go-live they must be replaced by nets trained
without DeepSport (`docs/plans/tracking-strategie.md` section 9, step 6).
"""

from __future__ import annotations

from collections import deque
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from numpy.typing import NDArray

from handball_vision.balltrack2 import merge_candidates

U8 = NDArray[Any]
Peak = tuple[float, float, float]


def frame_gap(fps: float) -> int:
    """Frames between the centre frame and its neighbours, as in training."""
    return 3 if fps > 40 else 2


def peaks(hm: NDArray[np.float32], k: int = 5, stride: int = 4) -> list[Peak]:
    """The `k` strongest heatmap peaks (frame px of the net input), each blanking a 12 x 12 cell
    neighbourhood (48 px at stride 4) before the next."""
    hm = hm.copy()
    out: list[Peak] = []
    for _ in range(k):
        y, x = np.unravel_index(int(hm.argmax()), hm.shape)
        out.append(
            (
                float(x * stride + stride // 2),
                float(y * stride + stride // 2),
                round(float(hm[y, x]), 3),
            )
        )
        hm[max(0, y - 6) : y + 6, max(0, x - 6) : x + 6] = 0
    return out


class BallNet:
    """One or more exported ball nets; `run(triplets)` -> candidates per triplet."""

    def __init__(
        self, model_paths: Sequence[Path], threads: int | None = None, width: int = 1280
    ) -> None:
        import onnxruntime as ort

        options = ort.SessionOptions()
        if threads:
            options.intra_op_num_threads = threads
        providers = [
            p
            for p in ("CUDAExecutionProvider", "CPUExecutionProvider")
            if p in ort.get_available_providers()
        ]
        self.sessions = [
            ort.InferenceSession(str(p), options, providers=providers) for p in model_paths
        ]
        self.model = "+".join(Path(p).stem for p in model_paths)
        self.width = width

    def prepare(self, frames: Sequence[U8]) -> tuple[NDArray[np.float32], float]:
        """Three BGR frames -> 9 x H x W float32 RGB 0..255 at `width` px, height cropped to a
        multiple of 32 (bottom rows dropped, as in the prelabel kernels); returns the scale
        frame px per input px."""
        h, w = frames[0].shape[:2]
        r = self.width / w
        chans = []
        for f in frames:
            if f.shape[1] != self.width:
                f = cv2.resize(f, (self.width, round(h * r)), interpolation=cv2.INTER_AREA)
            h2 = f.shape[0] // 32 * 32
            chans.append(cv2.cvtColor(f[:h2], cv2.COLOR_BGR2RGB))
        x = np.concatenate(chans, 2).transpose(2, 0, 1).astype(np.float32)
        return x, 1 / r

    def run(self, triplets: Sequence[Sequence[U8]], k: int = 5) -> list[list[Peak]]:
        if not triplets:
            return []
        prepared = [self.prepare(t) for t in triplets]
        x = np.stack([p[0] for p in prepared])
        scale = prepared[0][1]
        per_net = []
        for sess in self.sessions:
            hm = sess.run(None, {sess.get_inputs()[0].name: x})[0][:, 0]
            per_net.append([[(px * scale, py * scale, s) for px, py, s in peaks(h, k)] for h in hm])
        if len(per_net) == 1:
            return [[rounded(c) for c in row] for row in per_net[0]]
        return [
            [
                rounded(c)
                for c in merge_candidates([net[i] for net in per_net], radius=8 * scale, top=k)
            ]
            for i in range(len(x))
        ]


def rounded(c: Peak) -> Peak:
    """Candidates are kept at 0.01 px and 1e-4 score: they survive storage as float32 exactly, so a
    re-run from `observations.npz` gives the same ball path as the first run."""
    return (round(c[0], 2), round(c[1], 2), round(c[2], 4))


class BallCandidates:
    """Feeds decoded frames in order; runs the net for centre frames t with t % every == 0 once
    frame t + G has arrived, in batches of `batch`. `result` maps frame index -> candidates."""

    def __init__(self, net: BallNet, fps: float, every: int = 1, batch: int = 8) -> None:
        self.net = net
        self.gap = frame_gap(fps)
        self.every = max(1, every)
        self.batch = max(1, batch)
        self.buf: deque[tuple[int, U8]] = deque(maxlen=2 * self.gap + 1)
        self.pending: list[tuple[int, list[U8]]] = []
        self.result: dict[int, list[Peak]] = {}

    def add(self, index: int, frame: U8) -> None:
        self.buf.append((index, frame))
        if len(self.buf) < self.buf.maxlen:  # type: ignore[operator]
            return
        t, centre = self.buf[self.gap]
        if t % self.every:
            return
        self.pending.append((t, [self.buf[0][1], centre, self.buf[-1][1]]))
        if len(self.pending) >= self.batch:
            self.flush()

    def flush(self) -> None:
        if not self.pending:
            return
        out = self.net.run([trip for _, trip in self.pending])
        for (t, _), cands in zip(self.pending, out, strict=True):
            self.result[t] = cands
        self.pending = []
