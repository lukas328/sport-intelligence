"""Player re-identification (BRIEF 7.2 stage 6): read a shirt number once, recognise the player.

A shirt number is readable on few frames (back to the camera, sharp, unoccluded); the player is
recognisable on many more. So:

1. A person re-identification network (ONNX, `Embedder`) turns a player crop into an appearance
   vector, about once per second per player (`observe`).
2. Fragments (track pieces) whose number was read (`numbers.vote`) are the labelled examples of
   this match. Per team, a projection is learned from them (PCA, then LDA: directions that separate
   today's players; all shirts of a team are equal, hair, build and shoes are not).
   Only consistent fragments teach (`consistency`): a track jumping between people would teach a
   mixture. With the frames of the vectors and the track's readings, a fragment teaches only with
   the vectors next to readings of its number (`anchor_vectors`): the reading says who is in the
   box at that moment, also on tracks that carry a second person (bench, referee, a crowd).
3. Every fragment without a number goes to the nearest player when that is clearly nearer than the
   second nearest (ratio test), the player is not on court elsewhere at the same time, the
   distances to the player's fragments before and after can be run, and the fragment's own
   readings (if any) do not say another number (`contradicts`). Unsure stays unknown.
4. Only field players take part (`plays`): fragments labelled referee or goalkeeper, and those
   the role classifier (roles.py, averaged next to the readings for a numbered fragment) does not
   call a player, neither teach nor get a number. Referees, staff and the bench in a team-like
   colour otherwise become anchors that pull other fragments to their number.

Measured on a 5-minute NLB clip (12 numbered players, numbers hidden on 15-second pieces of their
tracks): 65 % of the pieces found, 70 to 75 % of the found ones right (some "errors" are misread
numbers in the labels). Colour statistics alone found 19 %. On a 3-minute SG Wädenswil/Horgen
stream segment (10 players with numbers on the match sheet, 56 pieces of 10 s hidden): 31 right
and 14 wrong with whole tracks teaching, 34 right and 12 wrong with the read stretches; in the
full pipeline the appearance numbers no longer went to bench and referee anchors. The network
itself separates teammates well when the examples are clean: 25 of 29 five-second pieces with
agreeing readings go to the right player (LDA, nearest centre).
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
    frames: NDArray[np.int64] | None = None  # video frame of each vector (same order)
    readings: tuple[tuple[int, int], ...] = ()  # (frame, number): confident shirt-number readings
    # mean role probabilities (player, goalkeeper, referee; roles.py), see `fragment_roles`
    role_p: tuple[float, float, float] | None = None


ANCHOR_WINDOW_S = 2.0  # vectors this close to a reading of the number show its owner
MIN_READ_VECTORS = 2


def anchor_vectors(f: Fragment, fps: float, window_s: float = ANCHOR_WINDOW_S) -> F64:
    """The vectors of a numbered fragment that show the number's owner: those within `window_s`
    of a reading of that number. A track often carries two people (crowds, the bench, a player
    passing the referee), and the reading says who is in the box at that moment; the other
    vectors would teach a mixture. Without frames or readings: all vectors."""
    if f.number is None or f.frames is None or not f.readings:
        return f.vectors
    at = np.array([fr for fr, n in f.readings if n == f.number], np.float64)
    if not len(at):
        return f.vectors[:0]
    gap = np.abs(np.asarray(f.frames, np.float64)[:, None] - at[None, :]).min(axis=1)
    return np.asarray(f.vectors[gap <= window_s * fps], np.float64)


# mean player probability a fragment needs to teach or to get a number. 0.75 was set on four
# games of one hall; on twelve games of other halls 0.45 finds 330 instead of 290 hidden numbers
# with 57 instead of 53 wrong, and still keeps out what the classifier calls a referee or a
# goalkeeper (ADR 027, broad measurement)
MIN_PLAYER_P = 0.45


def fragment_roles(
    looks: list[tuple[int, F64]],
    readings: tuple[tuple[int, int], ...],
    number: int | None,
    fps: float,
    window_s: float = ANCHOR_WINDOW_S,
    min_looks: int = 2,
) -> tuple[float, float, float] | None:
    """What a fragment is to the role classifier (player, goalkeeper, referee): the mean of its
    (frame, probabilities) looks; for a numbered fragment the looks next to readings of its
    number when there are enough (the reading says who is in the box, like `anchor_vectors`).
    None with fewer than `min_looks` looks."""
    if not looks:
        return None
    frames = np.array([f for f, _ in looks], np.float64)
    probs = np.stack([np.asarray(p, np.float64) for _, p in looks])
    at = np.array([fr for fr, n in readings if n == number], np.float64)
    if number is not None and len(at):
        near = np.abs(frames[:, None] - at[None, :]).min(axis=1) <= window_s * fps
        if near.sum() >= min_looks:
            probs = probs[near]
    if len(probs) < min_looks:
        return None
    m = probs.mean(axis=0)
    return (float(m[0]), float(m[1]), float(m[2]))


def plays(f: Fragment, min_player_p: float = MIN_PLAYER_P) -> bool:
    """Whether a fragment may teach or be given a number: a field player by its label and, when
    known, by the role classifier. Referees, goalkeepers, staff and bench people in a team's
    colour otherwise become anchors that attract other fragments, or get a player's number."""
    if f.team == "referee" or f.team.endswith("_gk"):
        return False
    return f.role_p is None or f.role_p[0] >= min_player_p


def contradicts(f: Fragment, number: int) -> bool:
    """Whether the fragment's own readings speak against `number`: at least two confident
    readings and none of them is the number or a known misreading of it (numbers.CONFUSIONS)."""
    from handball_vision.numbers import _misread_of

    read = [n for _, n in f.readings]
    if len(read) < 2:
        return False
    return not any(n == number or _misread_of(str(n), str(number)) for n in read)


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


def consistency(vectors: F64) -> float:
    """Median similarity of a fragment's vectors to their mean: low for a track that jumps between
    people (crowds, referee and spectators), about 0.75 for one player on the checked clip."""
    c = _unit(np.asarray(vectors, np.float64).mean(axis=0))
    return float(np.median(np.asarray(vectors, np.float64) @ c))


MIN_ANCHOR_CONSISTENCY = 0.68
MIN_ANCHOR_VECTORS = 5
MIN_CANDIDATE_CONSISTENCY = 0.62


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
        mine = [
            f
            for f in fragments
            if f.team.removesuffix("_gk") == team
            and plays(f)
            and len(f.vectors)
            and (
                consistency(f.vectors) >= MIN_CANDIDATE_CONSISTENCY
                # a numbered track that switched people still teaches with its read stretches
                or (f.number is not None and f.frames is not None and bool(f.readings))
            )
        ]
        timeline: dict[int, list[Fragment]] = defaultdict(list)
        teach: dict[int, F64] = {}  # id(fragment) -> the vectors it teaches with
        for f in mine:
            if f.number is None:
                continue
            if f.frames is not None and f.readings:
                vecs = anchor_vectors(f, fps)
                good = len(vecs) >= MIN_READ_VECTORS
            else:
                vecs = f.vectors
                good = (
                    len(vecs) >= MIN_ANCHOR_VECTORS and consistency(vecs) >= MIN_ANCHOR_CONSISTENCY
                )
            if good:
                timeline[f.number].append(f)
                teach[id(f)] = vecs
        project = fit_projection(
            {n: np.concatenate([teach[id(g)] for g in fs]) for n, fs in timeline.items()}
        )
        if project is None:
            continue
        desc = {id(f): _unit(project(teach.get(id(f), f.vectors)).mean(axis=0)) for f in mine}
        open_ = [f for f in mine if id(f) not in teach]
        while open_:
            centres = {
                n: _unit(np.mean([desc[id(g)] for g in fs], axis=0)) for n, fs in timeline.items()
            }
            best: tuple[float, Fragment, int] | None = None
            for f in open_:
                ranked = sorted(
                    (1.0 - float(desc[id(f)] @ c), n)
                    for n, c in centres.items()
                    if fits(f, timeline[n], fps) and not contradicts(f, n)
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
