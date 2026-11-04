"""Player re-identification (BRIEF 7.2 stage 6): read a shirt number once, recognise the player.

A shirt number is readable on few frames (back to the camera, sharp, unoccluded); the player is
recognisable on many more. So:

1. A person re-identification network (ONNX, `Embedder`) turns a player crop into an appearance
   vector, about once per second per player (`observe`).
2. Fragments (track pieces) whose number was read (`numbers.vote`) are the labelled examples of
   this match. Per team, a projection is learned from them (PCA, then LDA: directions that separate
   today's players; all shirts of a team are equal, hair, build and shoes are not).
3. Every fragment without a number goes to the nearest player when that is clearly nearer than the
   second nearest (ratio test), the player is not on court elsewhere at the same time, and the
   distances to the player's fragments before and after can be run. Unsure stays unknown.

Measured on a 5-minute NLB clip (12 numbered players, numbers hidden on 15-second pieces of their
tracks): 65 % of the pieces found, 70 to 75 % of the found ones right (some "errors" are misread
numbers in the labels). Colour statistics alone found 19 %.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from numpy.typing import NDArray

F64 = NDArray[np.float64]
U8 = NDArray[Any]

MIN_BOX_HEIGHT = 50


class Embedder:
    """Appearance vectors for person crops: an ONNX model taking N x 3 x 256 x 128 RGB in 0..255
    (normalisation inside the model) and returning L2-normalised vectors."""

    def __init__(self, model: Path, threads: int | None = None) -> None:
        import onnxruntime as ort

        opts = ort.SessionOptions()
        if threads:
            opts.intra_op_num_threads = threads
        providers = [
            p
            for p in ("CUDAExecutionProvider", "CPUExecutionProvider")
            if p in ort.get_available_providers()
        ]
        self.session = ort.InferenceSession(str(model), opts, providers=providers)
        self.input = self.session.get_inputs()[0].name
        self.model = model.stem

    def embed(self, frame: U8, boxes: list[tuple[float, float, float, float]]) -> list[F64 | None]:
        crops, keep = [], []
        for k, (x1, y1, x2, y2) in enumerate(boxes):
            if y2 - y1 < MIN_BOX_HEIGHT:
                continue
            c = frame[max(0, round(y1)) : max(0, round(y2)), max(0, round(x1)) : max(0, round(x2))]
            if c.size == 0:
                continue
            crops.append(cv2.resize(cv2.cvtColor(c, cv2.COLOR_BGR2RGB), (128, 256)))
            keep.append(k)
        out: list[F64 | None] = [None] * len(boxes)
        if not crops:
            return out
        x = np.stack(crops).transpose(0, 3, 1, 2).astype(np.float32)
        vecs = self.session.run(None, {self.input: x})[0]
        for k, v in zip(keep, vecs, strict=True):
            out[k] = np.asarray(v, np.float64)
        return out


@dataclass
class Fragment:
    track_id: int
    team: str
    first: int  # frame
    last: int
    start_xy: tuple[float, float]
    end_xy: tuple[float, float]
    vectors: F64  # (n, d) appearance vectors of this fragment
    number: int | None = None


def fit_projection(
    by_number: dict[int, F64], dim: int = 32, reg: float = 0.3
) -> Callable[[F64], F64] | None:
    """PCA to `dim`, then LDA over the players (regularised within-class scatter)."""
    if len(by_number) < 2:
        return None
    xs = np.concatenate(list(by_number.values()))
    y = np.concatenate([[n] * len(v) for n, v in by_number.items()])
    dim = min(dim, xs.shape[0] - 1, xs.shape[1])
    mu = xs.mean(axis=0)
    _, _, vt = np.linalg.svd(xs - mu, full_matrices=False)
    p = vt[:dim].T
    z = (xs - mu) @ p
    m = z.mean(axis=0)
    sw = np.zeros((dim, dim))
    sb = np.zeros((dim, dim))
    for c in set(y.tolist()):
        zc = z[y == c]
        mc = zc.mean(axis=0)
        sw += (zc - mc).T @ (zc - mc)
        sb += len(zc) * np.outer(mc - m, mc - m)
    sw = sw / len(z)
    sw = (1 - reg) * sw + reg * np.eye(dim) * np.trace(sw) / dim
    w, v = np.linalg.eig(np.linalg.solve(sw, sb))
    order = np.argsort(-w.real)
    lda = v[:, order[: max(2, len(by_number) - 1)]].real

    def project(vectors: F64) -> F64:
        return np.asarray(((np.atleast_2d(vectors) - mu) @ p) @ lda, np.float64)

    return project


def _unit(v: F64) -> F64:
    return np.asarray(v / (np.linalg.norm(v) + 1e-9), np.float64)


def _reachable(a: Fragment, b: Fragment, fps: float, speed: float = 8.0) -> bool:
    """Can one player be at the end of `a` and at the start of `b` (a before b)?"""
    gap_s = max(0.0, (b.first - a.last) / fps)
    d = float(np.hypot(b.start_xy[0] - a.end_xy[0], b.start_xy[1] - a.end_xy[1]))
    return d <= 2.0 + speed * gap_s


def fits(f: Fragment, others: list[Fragment], fps: float, overlap_s: float = 1.0) -> bool:
    """Can `f` belong to the player whose fragments are `others`?"""
    for o in others:
        if min(f.last, o.last) - max(f.first, o.first) > overlap_s * fps:
            return False
        if o.last <= f.first and not _reachable(o, f, fps):
            return False
        if f.last <= o.first and not _reachable(f, o, fps):
            return False
    return True


def assign(
    fragments: list[Fragment],
    fps: float,
    max_distance: float = 0.5,
    ratio: float = 0.85,
) -> dict[int, int]:
    """Numbers for fragments without one: track id -> number. Per team, most certain first; each
    accepted fragment joins its player's timeline, so later ones must fit around it."""
    out: dict[int, int] = {}
    for team in {f.team.removesuffix("_gk") for f in fragments}:
        mine = [f for f in fragments if f.team.removesuffix("_gk") == team and len(f.vectors)]
        timeline: dict[int, list[Fragment]] = defaultdict(list)
        for f in mine:
            if f.number is not None:
                timeline[f.number].append(f)
        project = fit_projection(
            {n: np.concatenate([g.vectors for g in fs]) for n, fs in timeline.items()}
        )
        if project is None:
            continue
        desc = {id(f): _unit(project(f.vectors).mean(axis=0)) for f in mine}
        open_ = [f for f in mine if f.number is None]
        while open_:
            centres = {
                n: _unit(np.mean([desc[id(g)] for g in fs], axis=0)) for n, fs in timeline.items()
            }
            best: tuple[float, Fragment, int] | None = None
            for f in open_:
                ranked = sorted(
                    (1.0 - float(desc[id(f)] @ c), n)
                    for n, c in centres.items()
                    if fits(f, timeline[n], fps)
                )
                if not ranked:
                    continue
                d1, n1 = ranked[0]
                d2 = ranked[1][0] if len(ranked) > 1 else float("inf")
                if d1 > max_distance or d1 > ratio * d2:
                    continue
                score = d1 / max(d2, 1e-6)
                if best is None or score < best[0]:
                    best = (score, f, n1)
            if best is None:
                break
            _, f, n = best
            out[f.track_id] = n
            timeline[n].append(f)
            open_.remove(f)
    return out
