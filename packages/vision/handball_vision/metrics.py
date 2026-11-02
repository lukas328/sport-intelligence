"""Evaluation metrics for the golden set (BRIEF 10.3), computed on the court plane."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import linear_sum_assignment


@dataclass(frozen=True)
class DetectionScores:
    precision: float
    recall: float
    mean_error_m: float


@dataclass(frozen=True)
class TrackingScores:
    mota: float
    idf1: float
    id_switches: int
    recall: float
    precision: float


def _match(
    pred: NDArray[np.float64], truth: NDArray[np.float64], thr: float
) -> list[tuple[int, int, float]]:
    if len(pred) == 0 or len(truth) == 0:
        return []
    cost = np.linalg.norm(pred[:, None] - truth[None], axis=2)
    r, c = linear_sum_assignment(cost)
    return [
        (int(i), int(j), float(cost[i, j])) for i, j in zip(r, c, strict=True) if cost[i, j] < thr
    ]


def detection_scores(
    preds: list[NDArray[np.float64]], truths: list[NDArray[np.float64]], thr: float = 1.0
) -> DetectionScores:
    tp = fp = fn = 0
    errs: list[float] = []
    for p, t in zip(preds, truths, strict=True):
        m = _match(p, t, thr)
        tp += len(m)
        fp += len(p) - len(m)
        fn += len(t) - len(m)
        errs += [e for _, _, e in m]
    return DetectionScores(
        tp / max(1, tp + fp), tp / max(1, tp + fn), float(np.mean(errs)) if errs else float("nan")
    )


def tracking_scores(
    frames: list[tuple[list[int], NDArray[np.float64], list[int], NDArray[np.float64]]],
    thr: float = 1.0,
) -> TrackingScores:
    """CLEAR MOT (Bernardin & Stiefelhagen 2008) and IDF1 (Ristani et al. 2016) on the court plane.

    frames: (pred_ids, pred_xy, gt_ids, gt_xy) per frame. Correspondences from the previous frame
    are kept while they stay within the threshold; only the rest is re-matched (Hungarian).
    """
    tp = fp = fn = switches = 0
    last: dict[int, int] = {}  # gt id -> pred id of the last match
    current: dict[int, int] = {}
    pair_counts: Counter[tuple[int, int]] = Counter()
    gt_total: Counter[int] = Counter()
    pred_total: Counter[int] = Counter()
    for pids, pxy, gids, gxy in frames:
        for g in gids:
            gt_total[g] += 1
        for p in pids:
            pred_total[p] += 1
        pidx = {p: i for i, p in enumerate(pids)}
        gidx = {g: j for j, g in enumerate(gids)}
        matched: list[tuple[int, int]] = []
        for g, p in current.items():  # keep valid correspondences
            if g in gidx and p in pidx and np.linalg.norm(pxy[pidx[p]] - gxy[gidx[g]]) < thr:
                matched.append((pidx[p], gidx[g]))
        used_p = {i for i, _ in matched}
        used_g = {j for _, j in matched}
        rest_p = [i for i in range(len(pids)) if i not in used_p]
        rest_g = [j for j in range(len(gids)) if j not in used_g]
        for i, j, _ in _match(
            pxy[rest_p] if rest_p else np.zeros((0, 2)),
            gxy[rest_g] if rest_g else np.zeros((0, 2)),
            thr,
        ):
            matched.append((rest_p[i], rest_g[j]))
        current = {}
        tp += len(matched)
        fp += len(pids) - len(matched)
        fn += len(gids) - len(matched)
        for i, j in matched:
            g, p = gids[j], pids[i]
            pair_counts[(g, p)] += 1
            if g in last and last[g] != p:
                switches += 1
            last[g] = p
            current[g] = p
    total_gt = sum(gt_total.values())
    mota = 1 - (fn + fp + switches) / max(1, total_gt)
    gts, prs = sorted(gt_total), sorted(pred_total)
    if gts and prs:
        gi = {g: k for k, g in enumerate(gts)}
        pi = {p: k for k, p in enumerate(prs)}
        cost = np.zeros((len(gts), len(prs)))
        for (g, p), n in pair_counts.items():
            cost[gi[g], pi[p]] = -n
        r, c = linear_sum_assignment(cost)
        idtp = -cost[r, c].sum()
    else:
        idtp = 0
    idf1 = 2 * idtp / max(1, sum(gt_total.values()) + sum(pred_total.values()))
    return TrackingScores(
        round(mota, 4), round(float(idf1), 4), switches, tp / max(1, tp + fn), tp / max(1, tp + fp)
    )


def team_accuracy(
    assigned: dict[int, str], track_to_gt: dict[int, int], gt_labels: dict[int, str]
) -> float:
    ok = total = 0
    for tid, label in assigned.items():
        g = track_to_gt.get(tid)
        if g is None:
            continue
        total += 1
        ok += label == gt_labels[g]
    return ok / max(1, total)


def majority_gt(
    frames: list[tuple[list[int], NDArray[np.float64], list[int], NDArray[np.float64]]],
    thr: float = 1.0,
) -> dict[int, int]:
    votes: dict[int, Counter[int]] = defaultdict(Counter)
    for pids, pxy, gids, gxy in frames:
        for i, j, _ in _match(pxy, gxy, thr):
            votes[pids[i]][gids[j]] += 1
    return {p: c.most_common(1)[0][0] for p, c in votes.items()}
