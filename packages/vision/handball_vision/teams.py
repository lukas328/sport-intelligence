"""Team assignment (BRIEF 7.2 stage 5): torso colour against the kit colours from the match setup.

Per detection the torso region (rows 18 to 50 % of the box, central 60 % of the width) is
reduced to a robust colour in Lab after removing floor-coloured pixels. Each track collects its
samples; the track is assigned to the nearest kit (home, home_gk, away, away_gk, referee) by the
median of its samples. The kit colours act as priors, so no clustering seed problems arise.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np
from numpy.typing import NDArray

from handball_vision.detection import Detection

LABELS = ("home", "home_gk", "away", "away_gk", "referee")


def hex_to_bgr(value: str) -> tuple[int, int, int]:
    v = value.lstrip("#")
    r, g, b = int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16)
    return (b, g, r)


def bgr_to_lab(bgr: tuple[int, int, int]) -> NDArray[np.float64]:
    return cv2.cvtColor(np.array([[bgr]], np.uint8), cv2.COLOR_BGR2LAB)[0, 0].astype(np.float64)


def colour_distance(colour: NDArray[np.float64], kit: NDArray[np.float64]) -> float:
    """Distance between a torso colour seen in the video and a kit colour (both Lab, OpenCV
    scale). Hall video washes colours out (a yellow shirt looks beige, red looks pink), so a
    coloured kit is compared by hue (direction of a, b around neutral), not by plain distance;
    white, black and grey kits are compared by lightness and lack of colour."""
    ca = np.array([colour[1] - 128.0, colour[2] - 128.0])
    ka = np.array([kit[1] - 128.0, kit[2] - 128.0])
    mc, mk = float(np.hypot(*ca)), float(np.hypot(*ka))
    dl = abs(float(colour[0]) - float(kit[0]))
    if mk >= 15:
        if mc < 6:
            return 45.0 + 0.1 * dl
        cos = float(ca @ ka) / (mc * mk)
        hue = float(np.degrees(np.arccos(np.clip(cos, -1.0, 1.0))))
        return 0.8 * hue + 0.12 * dl + max(0.0, 8.0 - mc) * 2.0
    return 0.45 * dl + 1.6 * mc


@dataclass(frozen=True)
class TeamResult:
    label: str
    confidence: float
    samples: int


class TeamAssigner:
    def __init__(
        self, kits: dict[str, tuple[int, int, int]], floor_lab: NDArray[np.float64] | None = None
    ) -> None:
        self.kits = {k: bgr_to_lab(v) for k, v in kits.items()}
        self.floor = floor_lab
        self.samples: dict[int, list[NDArray[Any]]] = defaultdict(list)
        # video frame of each sample (parallel to `samples`, filled by `add_sample`)
        self.frames: dict[int, list[int]] = defaultdict(list)

    def add_sample(self, track_id: int, colour: NDArray[Any], frame: int) -> None:
        self.samples[track_id].append(colour)
        self.frames[track_id].append(frame)

    def torso_colour(self, frame: NDArray[np.uint8], d: Detection) -> NDArray[np.float64] | None:
        h, w = d.y2 - d.y1, d.x2 - d.x1
        y1, y2 = int(d.y1 + h * 0.18), int(d.y1 + h * 0.5)
        x1, x2 = int(d.x1 + w * 0.2), int(d.x2 - w * 0.2)
        if y2 - y1 < 2 or x2 - x1 < 2:
            return None
        crop = frame[max(0, y1) : y2, max(0, x1) : x2]
        if crop.size == 0:
            return None
        lab = cv2.cvtColor(crop, cv2.COLOR_BGR2LAB).reshape(-1, 3).astype(np.float64)
        if self.floor is not None:
            keep = np.linalg.norm(lab - self.floor, axis=1) > 18
            lab = lab[keep] if keep.sum() >= 3 else lab
        return np.median(lab, axis=0)

    def add(self, track_id: int, frame: NDArray[np.uint8], d: Detection) -> None:
        c = self.torso_colour(frame, d)
        if c is not None and len(self.samples[track_id]) < 200:
            self.samples[track_id].append(c)

    def classify(self, colour: NDArray[np.float64]) -> tuple[str, float]:
        dists = {k: colour_distance(colour, v) for k, v in self.kits.items()}
        ranked = sorted(dists.items(), key=lambda kv: kv[1])
        best, second = ranked[0], ranked[1]
        confidence = 1.0 - best[1] / max(second[1], 1e-6)
        return best[0], round(max(0.0, min(1.0, confidence)), 3)

    def result(self, track_id: int) -> TeamResult | None:
        s = self.samples.get(track_id)
        if not s:
            return None
        label, conf = self.classify(np.median(np.stack(s), axis=0))
        return TeamResult(label, conf, len(s))


def _kmeans(
    x: NDArray[np.float64], w: NDArray[np.float64], k: int, iters: int = 30, starts: int = 8
) -> tuple[NDArray[np.float64], NDArray[np.int_]]:
    """Weighted k-means, k-means++ starts with fixed seeds, the lowest inertia wins."""
    best: tuple[float, NDArray[np.float64], NDArray[np.int_]] | None = None
    for seed in range(starts):
        rng = np.random.default_rng(seed)
        centres = [x[int(rng.choice(len(x), p=w / w.sum()))]]
        for _ in range(1, k):
            d = np.min([np.sum((x - c) ** 2, axis=1) for c in centres], axis=0) * w
            centres.append(x[int(rng.choice(len(x), p=d / d.sum()))] if d.sum() > 0 else x[0])
        c = np.array(centres)
        labels = np.zeros(len(x), int)
        for _ in range(iters):
            labels = np.argmin(((x[:, None, :] - c[None]) ** 2).sum(axis=2), axis=1)
            new = np.array(
                [
                    np.average(x[labels == j], axis=0, weights=w[labels == j])
                    if (labels == j).any()
                    else c[j]
                    for j in range(k)
                ]
            )
            if np.allclose(new, c):
                break
            c = new
        inertia = float((w * ((x - c[labels]) ** 2).sum(axis=1)).sum())
        if best is None or inertia < best[0]:
            best = (inertia, c, labels)
    assert best is not None
    return best[1], best[2]


def relabel_by_clusters(
    colours: dict[int, tuple[NDArray[np.float64], int]],
    kits: dict[str, NDArray[np.float64]],
    min_samples: int = 20,
) -> dict[int, str]:
    """Team labels relative to this match's colours, not absolute kit colours.

    Hall lighting shifts colours a lot (white shirts look grey, black ones dark grey; colours wash
    out), so absolute matching fails while the order survives. The tracks' median torso colours are
    clustered (two big clusters: the teams; a small third: referees and others); the two team
    clusters are matched to the home and away kits by hue when the kits are coloured, else by
    lightness order. `colours`: track -> (median Lab, samples); `kits`: label -> Lab. Returns labels
    for the tracks with enough samples.
    """
    tids = [t for t, (_, n) in colours.items() if n >= min_samples]
    if len(tids) < 6 or "home" not in kits or "away" not in kits:
        return {}
    x = np.array([colours[t][0] for t in tids], dtype=np.float64)
    w = np.array([colours[t][1] for t in tids], dtype=np.float64)
    feat = np.column_stack([x[:, 0] * 0.6, x[:, 1], x[:, 2]])  # lightness counts less than colour
    total = float(w.sum())
    # the two teams: the pair of clusters with most players that is clearly apart (3 to 5 clusters,
    # because referees, goalkeepers and the bench form groups of their own)
    best: tuple[float, NDArray[np.float64], NDArray[np.int_], int, int] | None = None
    for k in (3, 4, 5):
        if len(tids) < 2 * k:
            break
        centres, labels = _kmeans(feat, w, k)
        weight = np.array([w[labels == j].sum() for j in range(k)])
        for i in range(k):
            for j in range(i + 1, k):
                if min(weight[i], weight[j]) < 0.12 * total:
                    continue
                sep = float(np.linalg.norm(centres[i] - centres[j]))
                # both teams field about as many players: a lopsided pair is a team plus referees
                balance = float(np.sqrt(min(weight[i], weight[j]) / max(weight[i], weight[j])))
                score = (weight[i] + weight[j]) / total * min(1.0, sep / 10.0) * balance
                if best is None or score > best[0] + 1e-9:
                    best = (score, centres, labels, i, j)
    if best is None:
        return {}
    _, centres, labels, ci, cj = best
    real = {
        j: np.average(x[labels == j], axis=0, weights=w[labels == j])
        for j in range(len(centres))
        if (labels == j).any()
    }
    home, away = kits["home"], kits["away"]
    a, b = real[ci], real[cj]

    def chroma(c: NDArray[np.float64]) -> float:
        return float(np.hypot(c[1] - 128, c[2] - 128))

    if max(chroma(home), chroma(away)) >= 15:
        straight = colour_distance(a, home) + colour_distance(b, away)
        swapped = colour_distance(a, away) + colour_distance(b, home)
        first_home = straight <= swapped
    else:  # white, black, grey kits: the lighter cluster wears the lighter kit
        first_home = (a[0] >= b[0]) == (home[0] >= away[0])
    names = {ci: "home" if first_home else "away", cj: "away" if first_home else "home"}
    # other clusters: referees (or keepers, fixed later by position) if they differ clearly from
    # both teams, else part of the nearest team
    for j in real:
        if j in names:
            continue
        dists = {t: float(np.linalg.norm(centres[j] - centres[t])) for t in (ci, cj)}
        nearest = min(dists, key=dists.__getitem__)
        names[j] = "referee" if dists[nearest] > 25 else names[nearest]
    return {t: names[int(lb)] for t, lb in zip(tids, labels, strict=True)}


# ---- the team of single looks (ADR 027 addendum: per-reading team colour) -------------------

MIN_TEAM_GAP = 20.0  # team centres closer than this (feature units) cannot tell single looks apart
SIDE_RATIO = 0.6  # a look belongs to a team when clearly nearer it than to the other


def _feature(lab: NDArray[np.float64] | list[float]) -> NDArray[np.float64]:
    """Lab with lightness weighted down (the same weighting as `relabel_by_clusters`)."""
    v = np.asarray(lab, dtype=np.float64)
    return np.array([0.6 * v[0], v[1], v[2]])


def team_centres(team_out: dict[int, dict[str, Any]]) -> dict[str, NDArray[np.float64]]:
    """This match's home and away torso colours: the median of the field tracks of each team,
    only when the two are far enough apart to tell single looks apart."""
    labs: dict[str, list[list[float]]] = defaultdict(list)
    for v in team_out.values():
        if v.get("label") in ("home", "away") and "lab" in v:
            labs[str(v["label"])].append(list(v["lab"]))
    if len(labs.get("home", [])) < 2 or len(labs.get("away", [])) < 2:
        return {}
    centres = {k: np.median(np.asarray(v), axis=0) for k, v in labs.items()}
    if np.linalg.norm(_feature(centres["home"]) - _feature(centres["away"])) < MIN_TEAM_GAP:
        return {}
    return centres


def side_of(
    colour: NDArray[np.float64] | None,
    centres: dict[str, NDArray[np.float64]],
    ratio: float = SIDE_RATIO,
) -> str | None:
    """"home" or "away" for one torso colour when it is clearly nearer that team's centre
    (`team_centres`), else None (referees, other kits, shadows, unsure)."""
    if colour is None or "home" not in centres or "away" not in centres:
        return None
    f = _feature(colour)
    dh = float(np.linalg.norm(f - _feature(centres["home"])))
    da = float(np.linalg.norm(f - _feature(centres["away"])))
    if dh < ratio * da:
        return "home"
    if da < ratio * dh:
        return "away"
    return None


def colour_runs(
    frames: list[int], sides: list[str | None], fps: float, min_run_s: float = 1.0
) -> list[tuple[int, int, str]]:
    """A track's stretches of one team colour: (first frame, last frame, side), in time order.
    Looks without a side are skipped; each look takes the majority of the looks within half a
    second (single looks flicker in crowds), and stretches shorter than `min_run_s` go to the
    longer neighbour."""
    known = sorted((f, s) for f, s in zip(frames, sides, strict=True) if s is not None)
    if not known:
        return []
    fr = np.array([f for f, _ in known], np.int64)
    home = np.array([s == "home" for _, s in known], np.int64)
    half = 0.5 * fps
    lo = np.searchsorted(fr, fr - half, side="left")
    hi = np.searchsorted(fr, fr + half, side="right")
    csum = np.concatenate([[0], np.cumsum(home)])
    share = (csum[hi] - csum[lo]) / (hi - lo)
    smooth = ["home" if s > 0.5 else "away" if s < 0.5 else known[k][1] for k, s in enumerate(share)]
    runs: list[list[Any]] = []  # [first, last, side]
    for f, s in zip(fr.tolist(), smooth, strict=True):
        if runs and runs[-1][2] == s:
            runs[-1][1] = f
        else:
            runs.append([f, f, s])
    min_len = min_run_s * fps
    while len(runs) > 1:
        k = min(range(len(runs)), key=lambda i: runs[i][1] - runs[i][0])
        if runs[k][1] - runs[k][0] >= min_len:
            break
        nb = [i for i in (k - 1, k + 1) if 0 <= i < len(runs)]
        to = max(nb, key=lambda i: runs[i][1] - runs[i][0])
        runs[to][0], runs[to][1] = min(runs[to][0], runs[k][0]), max(runs[to][1], runs[k][1])
        del runs[k]
        merged: list[list[Any]] = []
        for r in runs:
            if merged and merged[-1][2] == r[2]:
                merged[-1][1] = r[1]
            else:
                merged.append(r)
        runs = merged
    return [(int(a), int(b), str(s)) for a, b, s in runs]
