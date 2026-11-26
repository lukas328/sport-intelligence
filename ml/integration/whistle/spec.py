"""Spectrogram strip for whistle labelling.
usage: python spec.py WAV T0 DUR OUT
0 to 8 kHz (16 kHz audio), time grid every second (labelled every 5 s, white), frequency lines
every 1 kHz (green). Whistles show as thin bright horizontal lines (often with harmonics), mostly
between 2 and 5 kHz, a fraction of a second to ~2 s long."""

import sys
import wave

import cv2
import numpy as np

wav, t0, dur, out = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), sys.argv[4]
with wave.open(wav) as w:
    sr = w.getframerate()
    w.setpos(int(t0 * sr))
    x = np.frombuffer(w.readframes(int(dur * sr)), np.int16).astype(np.float32) / 32768
n, hop = 1024, sr // 100
fr = np.lib.stride_tricks.sliding_window_view(x, n)[::hop] * np.hanning(n)
S = 20 * np.log10(np.abs(np.fft.rfft(fr, axis=1)).T + 1e-6)
S = np.clip((S - np.percentile(S, 99.7) + 60) / 60, 0, 1)
W, H = 1800, 500
img = cv2.applyColorMap(cv2.resize((255 * S[::-1]).astype(np.uint8), (W, H)), cv2.COLORMAP_MAGMA)
fmax = sr / 2
for k in range(int(dur) + 1):
    X = int(k / dur * W)
    thick = k % 5 == 0
    cv2.line(img, (X, 0), (X, H), (255, 255, 255) if thick else (120, 120, 120), 1)
    if thick:
        cv2.putText(img, f"{t0 + k:.0f}", (X + 2, 14), 0, 0.45, (255, 255, 255), 1)
for f in range(1000, int(fmax), 1000):
    Y = int(H * (1 - f / fmax))
    cv2.line(img, (0, Y), (W, Y), (0, 200, 0), 1)
    cv2.putText(img, f"{f // 1000}k", (2, Y - 3), 0, 0.45, (0, 255, 0), 1)
cv2.imwrite(out, img, [cv2.IMWRITE_JPEG_QUALITY, 88])
