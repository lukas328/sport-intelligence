# ruff: noqa: N806
"""Referee whistle from 8 kHz mono audio. Pre-registered before any label exists.
STFT 64 ms (Hann), hop 10 ms. Per frame, in the band BAND_HZ:
- tonal: the strongest bin is TONAL_DB above the band's median bin;
- loud: the band energy is LOUD_DB above its rolling median over NOISE_S (the hall noise).
A whistle = a run of frames that are both, at least MIN_S long (gaps of one frame bridged), with
a steady peak frequency (std below STEADY_HZ). Whistles closer than MERGE_S are one."""

import numpy as np

BAND_HZ = {8000: (2000.0, 3950.0), 16000: (2000.0, 4500.0)}  # below Nyquist at 8 kHz
TONAL_DB = 12.0
LOUD_DB = 6.0
NOISE_S = 10.0
MIN_S = 0.15
STEADY_HZ = 80.0
MERGE_S = 0.3
N_S, HOP_S = 0.064, 0.010  # STFT window and hop in seconds


def detect(x, sr=8000):
    N, HOP = int(N_S * sr), int(HOP_S * sr)
    frames = np.lib.stride_tricks.sliding_window_view(x, N)[::HOP] * np.hanning(N)
    mag = np.abs(np.fft.rfft(frames, axis=1))
    freqs = np.fft.rfftfreq(N, 1 / sr)
    lo, hi = BAND_HZ[sr]
    band = (freqs >= lo) & (freqs <= hi)
    b = mag[:, band]
    peak = b.max(axis=1)
    tonal = 20 * np.log10((peak + 1e-9) / (np.median(b, axis=1) + 1e-9)) >= TONAL_DB
    energy = 10 * np.log10((b**2).sum(axis=1) + 1e-12)
    w = int(NOISE_S * sr / HOP)
    pad = np.pad(energy, (w // 2, w - w // 2 - 1), mode="edge")
    noise = (
        np.array([np.median(pad[i : i + w]) for i in range(0, len(energy))])
        if len(energy) < 5000
        else _rolling_median(pad, w)[: len(energy)]
    )
    loud = energy - noise >= LOUD_DB
    on = tonal & loud
    on = on | (np.roll(on, 1) & np.roll(on, -1))  # bridge one-frame gaps
    pf = freqs[band][b.argmax(axis=1)]
    dt = HOP / sr
    out, i = [], 0
    while i < len(on):
        if not on[i]:
            i += 1
            continue
        j = i
        while j < len(on) and on[j]:
            j += 1
        if (j - i) * dt >= MIN_S and np.std(pf[i:j]) < STEADY_HZ:
            t0, t1 = i * dt + N / sr / 2, j * dt + N / sr / 2
            if out and t0 - out[-1][1] < MERGE_S:
                out[-1] = (out[-1][0], t1, max(out[-1][2], float(np.median(pf[i:j]))))
            else:
                out.append((t0, t1, float(np.median(pf[i:j]))))
        i = j
    return out


def _rolling_median(a, w):
    # median over a sliding window via a decimated estimate (every 10 frames), interpolated
    idx = np.arange(0, len(a) - w + 1, 10)
    med = np.array([np.median(a[k : k + w]) for k in idx])
    return np.interp(np.arange(len(a) - w + 1), idx, med)


def load_wav(path):
    import wave

    with wave.open(str(path)) as w:
        return np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(
            np.float32
        ) / 32768, w.getframerate()
