"""Person detection (BRIEF 7.2 stage 3) behind the `Detector` interface.

- `BackgroundDetector` (source "heuristic"): fixed cameras. A running median background, colour
  distance in Lab, morphology and connected components restricted to the court (+2 m). Blobs that
  are wider than a single player at that image position are split. No training data needed.
- `OnnxDetector` (source "model"): runs any exported detector with the common
  [x1, y1, x2, y2, score, class] output, batched, on ONNX Runtime (CUDA EP when available).
  Weights come from the model registry, never from the repository (ADR 003).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import cv2
import numpy as np
from numpy.typing import NDArray

from handball_vision import geometry
from handball_vision.calibration import Calibration

U8 = NDArray[Any]  # images (OpenCV returns loosely typed arrays)


@dataclass(frozen=True)
class Detection:
    x1: float
    y1: float
    x2: float
    y2: float
    score: float
    cls: str = "person"

    @property
    def foot(self) -> tuple[float, float]:
        return ((self.x1 + self.x2) / 2, self.y2)

    @property
    def height(self) -> float:
        return self.y2 - self.y1


class Detector(Protocol):
    source: str

    def detect(self, frames: list[U8]) -> list[list[Detection]]: ...


def court_mask(calib: Calibration, margin_m: float = 2.0) -> U8:
    w, h = calib.image_size
    poly = calib.to_image(
        np.array(
            [
                [-margin_m, -margin_m],
                [40 + margin_m, -margin_m],
                [40 + margin_m, 20 + margin_m],
                [-margin_m, 20 + margin_m],
            ]
        )
    )
    mask = np.zeros((h, w), np.uint8)
    cv2.fillPoly(mask, [poly.astype(np.int32)], 255)
    return mask


def expected_height_px(
    calib: Calibration, foot: tuple[float, float], player_m: float = 1.85
) -> float:
    """Approximate player height in pixels at an image position from the ground homography.

    Without the full camera matrix we use the local scale of the court plane: the image length
    of 1 m in depth direction times a factor that relates standing height to ground depth for
    elevated cameras (calibrated on the synthetic camera family, roughly 1.0 to 1.4).
    """
    cx, cy = calib.to_court(np.array([foot]))[0]
    pts = calib.to_image(np.array([[cx - 0.5, cy], [cx + 0.5, cy]]))
    lateral = float(np.linalg.norm(pts[1] - pts[0]))  # pixels per metre across the image
    return lateral * player_m


class BackgroundDetector:
    source = "heuristic"

    def __init__(self, calib: Calibration, threshold: float = 26.0, scale: float = 0.5) -> None:
        self.calib = calib
        self.scale = scale
        w, h = calib.image_size
        self.size = (round(w * scale), round(h * scale))
        self.mask = cv2.resize(court_mask(calib), self.size, interpolation=cv2.INTER_NEAREST)
        self._bg_f: NDArray[np.float32] = np.zeros(0, np.float32)
        self.threshold = threshold
        self.background: U8 | None = None
        # expected player height (px, at detection scale) for every image row band, via the homography
        self._exp = self._expected_height_table()

    def _expected_height_table(self) -> NDArray[np.float64]:
        w, h = self.size
        table = np.zeros((h, w // 16 + 1))
        for yi in range(h):
            for xi in range(0, w, 16):
                try:
                    table[yi, xi // 16] = (
                        expected_height_px(self.calib, (xi / self.scale, yi / self.scale))
                        * self.scale
                    )
                except (ValueError, np.linalg.LinAlgError):
                    table[yi, xi // 16] = 0
        return table

    def exp_h(self, x: float, y: float) -> float:
        h, _ = self._exp.shape
        return float(
            self._exp[int(np.clip(y, 0, h - 1)), int(np.clip(x, 0, self.size[0] - 1)) // 16]
        )

    def _small(self, frame: U8) -> U8:
        return (
            frame if self.scale == 1 else cv2.resize(frame, self.size, interpolation=cv2.INTER_AREA)
        )

    def warm_up(self, frames: list[U8]) -> None:
        """Background from frames sampled across the video (players move, the hall does not)."""
        labs = [cv2.cvtColor(self._small(f), cv2.COLOR_BGR2LAB) for f in frames]
        self.background = np.median(np.stack(labs), axis=0).astype(np.uint8)
        self._bg_f = self.background.astype(np.float32)

    def _update(self, lab: U8, foreground: U8 | None) -> None:
        """Selective, slow update: only where no player is, so standing players never fade in."""
        if self.background is None:
            self.background = lab.copy()
            self._bg_f = lab.astype(np.float32)
            return
        still = foreground == 0 if foreground is not None else np.ones(lab.shape[:2], bool)
        cv2.accumulateWeighted(
            lab.astype(np.float32), self._bg_f, 0.01, mask=still.astype(np.uint8)
        )
        self.background = self._bg_f.astype(np.uint8)

    def _split(self, blob: U8, ox: int, oy: int) -> list[tuple[float, float, float, float, float]]:
        """Greedy decomposition of a foreground blob into player-sized boxes, feet first."""
        boxes = []
        remaining = blob.copy()
        total = int(remaining.sum() // 255)
        for _ in range(6):
            ys, xs = np.nonzero(remaining)
            if len(ys) < max(15, total * 0.12):
                break
            foot_y = int(ys.max())
            cols = xs[ys >= foot_y - 2]
            fx = float(np.median(cols))
            eh = self.exp_h(ox + fx, oy + foot_y)
            if eh <= 0:
                break
            ew = eh * 0.36
            x1, x2 = fx - ew / 2, fx + ew / 2
            y1 = foot_y - eh
            region = remaining[max(0, int(y1)) : foot_y + 1, max(0, int(x1)) : int(x2) + 1]
            fill = float(region.sum() / 255 / max(1.0, ew * eh))
            if fill < 0.18:
                remaining[max(0, foot_y - 2) :, :] = 0  # stray pixels at the bottom
                continue
            boxes.append(
                (ox + x1, oy + max(0.0, y1), ox + x2, float(oy + foot_y + 1), min(1.0, fill * 1.6))
            )
            remaining[max(0, int(y1) - 1) : foot_y + 1, max(0, int(x1)) : int(x2) + 1] = 0
        return boxes

    def _foot_from_head(self, cx: float, top: float, bottom: float) -> float:
        """Legs often blend into the floor; if the box is clearly too short for a player standing
        at its bottom, place the feet one expected body height below the head instead."""
        foot = bottom
        for _ in range(3):
            eh = self.exp_h(cx, foot)
            if eh <= 0 or bottom - top >= eh * 0.88:
                return foot
            foot = max(bottom, top + eh)
        return foot

    def detect(self, frames: list[U8]) -> list[list[Detection]]:
        out = []
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        tall = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 5))
        inv = 1 / self.scale
        for frame in frames:
            lab = cv2.cvtColor(self._small(frame), cv2.COLOR_BGR2LAB)
            if self.background is None:
                self._update(lab, None)
            assert self.background is not None
            diff = cv2.absdiff(lab, self.background).astype(np.float32)
            dist = cv2.sqrt(diff[:, :, 0] ** 2 * 0.5 + diff[:, :, 1] ** 2 + diff[:, :, 2] ** 2)
            fg: U8 = ((dist > self.threshold) & (self.mask > 0)).astype(np.uint8) * 255
            fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, kernel)
            fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, tall)
            self._update(lab, cv2.dilate(fg, kernel, iterations=3))
            n, labels, stats, _ = cv2.connectedComponentsWithStats(fg, connectivity=8)
            dets: list[Detection] = []
            for i in range(1, n):
                x, y, w, h, area = (int(v) for v in stats[i])
                if area < 12 or h < 5:
                    continue
                eh = self.exp_h(x + w / 2, y + h)
                if eh <= 0 or h < eh * 0.4:
                    continue
                blob = (labels[y : y + h, x : x + w] == i).astype(np.uint8) * 255
                for x1, y1, x2, y2, score in self._split(blob, x, y):
                    y2 = self._foot_from_head((x1 + x2) / 2, y1, y2)
                    dets.append(Detection(x1 * inv, y1 * inv, x2 * inv, y2 * inv, score))
            out.append(dets)
        return out


class OnnxDetector:
    """Generic batched ONNX detector. Expects outputs [batch, n, 6] = x1, y1, x2, y2, score, class
    in pixels of the network input (letterboxed square). Classes map via `labels`."""

    source = "model"

    def __init__(
        self,
        model_path: Path,
        input_size: int = 640,
        labels: dict[int, str] | None = None,
        score_threshold: float = 0.35,
        batch: int = 8,
    ) -> None:
        import onnxruntime as ort

        providers = [
            p
            for p in ("CUDAExecutionProvider", "CPUExecutionProvider")
            if p in ort.get_available_providers()
        ]
        self.session = ort.InferenceSession(str(model_path), providers=providers)
        self.input_name = self.session.get_inputs()[0].name
        self.size = input_size
        self.labels = labels or {0: "person", 1: "goalkeeper", 2: "referee", 3: "ball"}
        self.threshold = score_threshold
        self.batch = batch

    def _letterbox(self, frame: U8) -> tuple[NDArray[np.float32], float, tuple[int, int]]:
        h, w = frame.shape[:2]
        scale = self.size / max(h, w)
        nw, nh = round(w * scale), round(h * scale)
        canvas = np.full((self.size, self.size, 3), 114, np.uint8)
        top, left = (self.size - nh) // 2, (self.size - nw) // 2
        canvas[top : top + nh, left : left + nw] = cv2.resize(frame, (nw, nh))
        x = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB).astype(np.float32).transpose(2, 0, 1) / 255.0
        return x, scale, (left, top)

    def detect(self, frames: list[U8]) -> list[list[Detection]]:
        out: list[list[Detection]] = []
        for start in range(0, len(frames), self.batch):
            chunk = frames[start : start + self.batch]
            prepared = [self._letterbox(f) for f in chunk]
            batch = np.stack([p[0] for p in prepared])
            (raw,) = self.session.run(None, {self.input_name: batch})[:1]
            for (_, scale, (left, top)), rows in zip(prepared, raw, strict=True):
                dets = []
                for x1, y1, x2, y2, score, cls in rows:
                    if score < self.threshold:
                        continue
                    dets.append(
                        Detection(
                            (x1 - left) / scale,
                            (y1 - top) / scale,
                            (x2 - left) / scale,
                            (y2 - top) / scale,
                            float(score),
                            self.labels.get(int(cls), "person"),
                        )
                    )
                out.append(dets)
        return out


def foot_positions(calib: Calibration, dets: list[Detection]) -> NDArray[np.float64]:
    if not dets:
        return np.zeros((0, 2))
    return geometry.apply(calib.inverse, np.array([d.foot for d in dets]))
