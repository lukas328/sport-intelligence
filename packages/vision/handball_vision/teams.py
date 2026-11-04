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
