"""Audio synchronisation of several cameras (BRIEF 7.2 stage 0, goal cams in M5).

Cameras in the same hall hear the same whistles, horn, ball impacts and crowd. We compare onset envelopes
(energy increases per 10 ms) with an FFT cross-correlation, which is robust against different microphones,
gains and background noise. The result is the offset to add to the main video time to get the time in the
other video, plus a confidence from the peak sharpness. Below `MIN_CONFIDENCE` the UI asks for a manual
offset instead of silently using a wrong one.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

SR = 8000
HOP = 80  # 10 ms at 8 kHz
MIN_CONFIDENCE = 0.35


@dataclass(frozen=True)
class SyncResult:
    offset_ms: int  # time in other video = time in main video + offset_ms
    confidence: float


def load_mono(path: Path, seconds: float = 600.0, sr: int = SR) -> NDArray[np.float32]:
    """Decode the first `seconds` of audio as mono float32 at `sr` (PyAV, no ffmpeg CLI)."""
    import av

    out: list[NDArray[np.float32]] = []
    with av.open(str(path)) as c:
        if not c.streams.audio:
            return np.zeros(0, np.float32)
        resampler = av.AudioResampler(format="flt", layout="mono", rate=sr)
        total = 0
        for frame in c.decode(audio=0):
            for f in resampler.resample(frame):
                a = f.to_ndarray().reshape(-1).astype(np.float32)
                out.append(a)
                total += len(a)
            if total >= seconds * sr:
                break
    return np.concatenate(out)[: int(seconds * sr)] if out else np.zeros(0, np.float32)


def onset_envelope(x: NDArray[np.float32], hop: int = HOP) -> NDArray[np.float64]:
    n = len(x) // hop
    if n < 2:
        return np.zeros(0)
    frames = x[: n * hop].astype(np.float64).reshape(n, hop)
    energy = np.log1p(1000 * np.sqrt((frames**2).mean(axis=1)))
    onset = np.maximum(np.diff(energy, prepend=energy[0]), 0)
    onset -= onset.mean()
    std = onset.std()
    return onset / std if std > 0 else onset


def estimate_offset(
    main: NDArray[np.float32], other: NDArray[np.float32], sr: int = SR, max_lag_s: float = 300.0
) -> SyncResult:
    a, b = onset_envelope(main), onset_envelope(other)
    if len(a) < 100 or len(b) < 100:
        return SyncResult(0, 0.0)
    n = 1 << int(np.ceil(np.log2(len(a) + len(b))))
    corr = np.fft.irfft(np.fft.rfft(b, n) * np.conj(np.fft.rfft(a, n)), n)
    # lag k > 0: an event at main frame i appears at other frame i + k
    lags = np.concatenate([np.arange(0, len(b)), np.arange(-len(a) + 1, 0)])
    vals = np.concatenate([corr[: len(b)], corr[n - len(a) + 1 :]])
    hop_ms = 1000 * HOP / sr
    keep = np.abs(lags * hop_ms) <= max_lag_s * 1000
    lags, vals = lags[keep], vals[keep]
    # overlap of the two envelopes at each lag; tiny overlaps give noisy, meaningless peaks
    overlap = np.minimum(len(b), len(a) + lags) - np.maximum(0, lags)
    enough = overlap >= 0.25 * min(len(a), len(b))
    lags, vals, overlap = lags[enough], vals[enough], overlap[enough]
    if len(vals) == 0:
        return SyncResult(0, 0.0)
    vals = vals / overlap
    i = int(vals.argmax())
    peak = float(vals[i])
    # second best peak at least 1 s away
    far = np.abs(lags - lags[i]) * hop_ms > 1000
    second = float(vals[far].max()) if far.any() else 0.0
    confidence = 0.0 if peak <= 0 else max(0.0, min(1.0, (peak - max(second, 0.0)) / peak))
    return SyncResult(int(np.round(lags[i] * hop_ms)), round(confidence, 3))
