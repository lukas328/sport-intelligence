"""Shirt numbers (BRIEF 7.2 stage 6): read on player crops, voted per track.

Text models: PP-OCRv4 detection and recognition (PaddleOCR, Apache-2.0) as ONNX, run with ONNX
Runtime. The two files come from the `rapidocr_onnxruntime` wheel on PyPI (Apache-2.0), pinned with
checksums in the worker image (`ml/models/ppocr-v4.md`). Only the models are used, not the package.

Per crop:
1. The upper body (10 to 60 % of the box height) is enlarged three times; numbers on amateur
   footage are 15 to 25 px tall.
2. Text detection (DB): probability map, threshold, boxes slightly widened ("unclip").
3. Recognition (CTC) of every box on the green channel; only one or two digits count.

On 720p club footage about one crop in ten shows a readable number (backs, sharp, unoccluded), and
about 40 % of those are read; all readings with a confidence of 0.8 or more were correct on the
checked sample. That is why a number is decided per track from many readings (`vote`), never from
one crop.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from numpy.typing import NDArray

U8 = NDArray[Any]
F32 = NDArray[np.float32]

MIN_BOX_HEIGHT = 80  # px; smaller players have unreadable numbers
MIN_CONFIDENCE = 0.8


@dataclass(frozen=True)
class Reading:
    number: int
    confidence: float
    frame: int = -1  # video frame of the crop (for splitting tracks at identity switches)


class NumberReader:
    def __init__(
        self,
        det_model: Path,
        rec_model: Path,
        det_side: int = 320,
        threads: int | None = None,
    ) -> None:
        import onnxruntime as ort

        opts = ort.SessionOptions()
        if threads:
            opts.intra_op_num_threads = threads
        providers = [
            p
            for p in ("CUDAExecutionProvider", "CPUExecutionProvider")
            if p in ort.get_available_providers()
        ]
        self.det = ort.InferenceSession(str(det_model), opts, providers=providers)
        self.rec = ort.InferenceSession(str(rec_model), opts, providers=providers)
        chars = self.rec.get_modelmeta().custom_metadata_map.get("character", "")
        # CTC classes: 0 = blank, then the dictionary, then a space
        self.charset = ["", *chars.split("\n"), " "]
        self.det_side = det_side
        self.calls = 0

    # --- detection (DB) ----------------------------------------------------------------------

    def _normalise(self, img: U8) -> F32:
        x = img.astype(np.float32) / 255.0
        x = (x - 0.5) / 0.5
        return np.ascontiguousarray(x.transpose(2, 0, 1)[None], dtype=np.float32)

    def detect(self, img: U8) -> list[NDArray[np.float32]]:
        """Text boxes (4 corner points each, image coordinates)."""
        h, w = img.shape[:2]
        scale = max(1.0, self.det_side / min(h, w))
        nh = max(32, round(h * scale / 32) * 32)
        nw = max(32, round(w * scale / 32) * 32)
        pred = self.det.run(None, {"x": self._normalise(cv2.resize(img, (nw, nh)))})[0][0, 0]
        bitmap = cv2.dilate((pred > 0.3).astype(np.uint8), np.ones((2, 2), np.uint8))
        contours, _ = cv2.findContours(bitmap, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        boxes = []
        for c in contours[:200]:
            rect = cv2.minAreaRect(c)
            if min(rect[1]) < 3:
                continue
            x, y, bw, bh = cv2.boundingRect(c)
            mask = np.zeros((bh, bw), np.uint8)
            cv2.fillPoly(mask, [c - [x, y]], 1)
            score = float(cv2.mean(pred[y : y + bh, x : x + bw], mask)[0])
            if score < 0.5:
                continue
            (cx, cy), (rw, rh), angle = rect
            area, perimeter = rw * rh, 2 * (rw + rh)
            d = area * 1.6 / max(perimeter, 1e-6)  # unclip
            grown = ((cx, cy), (rw + 2 * d, rh + 2 * d), angle)
            if min(grown[1]) < 5:
                continue
            pts = cv2.boxPoints(grown)
            pts[:, 0] *= w / nw
            pts[:, 1] *= h / nh
            boxes.append(pts.astype(np.float32))
        return boxes

    # --- recognition (CTC) ------------------------------------------------------------------

    @staticmethod
    def _crop(img: U8, pts: NDArray[np.float32]) -> U8:
        pts = _order(pts)
        w = int(max(np.linalg.norm(pts[0] - pts[1]), np.linalg.norm(pts[2] - pts[3])))
        h = int(max(np.linalg.norm(pts[0] - pts[3]), np.linalg.norm(pts[1] - pts[2])))
        w, h = max(w, 1), max(h, 1)
        dst = np.array([[0, 0], [w, 0], [w, h], [0, h]], np.float32)
        out = cv2.warpPerspective(
            img, cv2.getPerspectiveTransform(pts, dst), (w, h), borderMode=cv2.BORDER_REPLICATE
        )
        if h / w >= 1.5:
            out = np.rot90(out)
        return np.asarray(out)

    def recognise(self, crops: list[U8]) -> list[tuple[str, float]]:
        if not crops:
            return []
        widths = [min(320, max(16, math.ceil(48 * c.shape[1] / max(1, c.shape[0])))) for c in crops]
        width = max(widths)
        batch = np.zeros((len(crops), 3, 48, width), np.float32)
        for k, (c, cw) in enumerate(zip(crops, widths, strict=True)):
            batch[k, :, :, :cw] = self._normalise(cv2.resize(c, (cw, 48)))[0]
        probs = self.rec.run(None, {"x": batch})[0]
        out = []
        for p in probs:
            idx = p.argmax(axis=1)
            best = p.max(axis=1)
            text, confs, prev = [], [], 0
            for i, c in zip(idx, best, strict=True):
                if i != 0 and i != prev and i < len(self.charset):
                    text.append(self.charset[i])
                    confs.append(float(c))
                prev = i
            out.append(("".join(text), float(np.mean(confs)) if confs else 0.0))
        return out

    # --- numbers ------------------------------------------------------------------------------

    def read_player(self, frame: U8, box: tuple[float, float, float, float]) -> Reading | None:
        """The shirt number of one player box, or None."""
        x1, y1, x2, y2 = (round(v) for v in box)
        h = y2 - y1
        if h < MIN_BOX_HEIGHT:
            return None
        top = max(0, y1 + int(0.1 * h))
        torso = frame[top : max(top + 1, y1 + int(0.6 * h)), max(0, x1) : max(x1 + 1, x2)]
        if torso.size == 0:
            return None
        # the green channel separates white digits from red shirts and dark digits from yellow or
        # white ones better than colour or plain grey (more correct readings on the checked clips)
        green = torso[..., 1] if torso.ndim == 3 else torso
        big = cv2.resize(
            cv2.merge([green, green, green]), None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC
        )
        self.calls += 1
        boxes = self.detect(big)
        best: Reading | None = None
        for text, conf in self.recognise([self._crop(big, b) for b in boxes]):
            text = text.strip()
            digits = text.isascii() and text.isdigit()
            if 1 <= len(text) <= 2 and digits and (best is None or conf > best.confidence):
                best = Reading(int(text), conf)
        return best


def _order(pts: NDArray[np.float32]) -> NDArray[np.float32]:
    """Corners as top-left, top-right, bottom-right, bottom-left."""
    s = pts.sum(axis=1)
    d = np.diff(pts, axis=1).ravel()
    return np.array(
        [pts[np.argmin(s)], pts[np.argmin(d)], pts[np.argmax(s)], pts[np.argmax(d)]], np.float32
    )


def sharp_enough(frame: U8, box: tuple[float, float, float, float], min_var: float = 60.0) -> bool:
    """Motion blur hides numbers: skip crops whose upper body has little fine detail."""
    x1, y1, x2, y2 = (round(v) for v in box)
    h = y2 - y1
    torso = frame[max(0, y1 + int(0.1 * h)) : max(1, y1 + int(0.6 * h)), max(0, x1) : max(1, x2)]
    if torso.size == 0:
        return False
    grey = cv2.cvtColor(torso, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(grey, cv2.CV_64F).var()) >= min_var


@dataclass(frozen=True)
class Vote:
    number: int
    confidence: float  # share of the confident readings that agree, damped for few readings
    readings: int


def vote(
    readings: list[Reading], min_confidence: float = MIN_CONFIDENCE, min_readings: int = 3
) -> Vote | None:
    """One number per track from confident readings: the most frequent number needs at least 70 %
    of them and `min_readings` readings; two readings suffice when both are very sure (0.95) and
    nothing else was read. On the checked clips, numbers with two ordinary readings were often
    wrong, numbers with three or more were right."""
    good = [r for r in readings if r.confidence >= min_confidence]
    if not good:
        return None
    weight: dict[int, float] = defaultdict(float)
    count: dict[int, int] = defaultdict(int)
    for r in good:
        weight[r.number] += r.confidence
        count[r.number] += 1
    number = max(weight, key=lambda k: weight[k])
    share = weight[number] / sum(weight.values())
    n = count[number]
    sure_pair = n == 2 and len(count) == 1 and all(r.confidence >= 0.95 for r in good)
    if share < 0.7 or (n < min_readings and not sure_pair):
        return None
    damp = 1 - 0.5 ** (n + 1)  # 2 readings: 0.88, 3: 0.94, 5: 0.98
    return Vote(number, round(share * damp, 3), n)


def split_points(readings: list[Reading], min_side: int = 2, gain: int = 2) -> list[int]:
    """Frames at which a track changes identity: confident readings that say one number for a
    while and then another (the tracker swapped two players in a crowd). Returns split frames,
    each halfway between the last reading of one number and the first of the next."""
    good = sorted((r for r in readings if r.confidence >= MIN_CONFIDENCE), key=lambda r: r.frame)
    if len(good) < 2 * min_side:
        return []

    def majority(rs: list[Reading]) -> tuple[int, int]:
        c: dict[int, int] = defaultdict(int)
        for r in rs:
            c[r.number] += 1
        k = max(c, key=lambda x: c[x])
        return k, c[k]

    _, whole = majority(good)
    best: tuple[int, int] | None = None  # (score, index)
    for i in range(min_side, len(good) - min_side + 1):
        (a, ca), (b, cb) = majority(good[:i]), majority(good[i:])
        strong = a != b and ca >= min_side and cb >= min_side and ca + cb >= whole + gain
        if strong and (best is None or ca + cb > best[0]):
            best = (ca + cb, i)
    if best is None:
        return []
    i = best[1]
    here = (good[i - 1].frame + good[i].frame) // 2
    return [
        *split_points(good[:i], min_side, gain),
        here,
        *split_points(good[i:], min_side, gain),
    ]
