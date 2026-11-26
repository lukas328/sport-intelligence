# ruff: noqa: N806, N812
"""Whistle detector, round 2. Procedure fixed before running: the parameters are chosen on clip
mue ONLY (grid below, best F1 at MATCH_S 0.5 against the frozen whistle truth), then the chosen
setting is scored ONCE on clip lei (holdout). No change after the lei score.
Per frame (64 ms Hann, hop 10 ms): the whistle band WB = (lo, hi); contrast = the strongest bin
in WB over the median bin of 1 to 6 kHz (or 1 to 3.95 kHz at 8 kHz), in dB, minus that value's
median over the clip (the hall's own tonality). A whistle = a run with contrast >= C_DB at least
MIN_S long (gaps up to 2 frames bridged); runs closer than MERGE_S are one."""

import itertools
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import whistle as W
from wh_eval import AUDIO, pair

MERGE_S = 0.3
GRID = {
    "wb": [(3300.0, 4300.0), (3500.0, 4200.0), (2500.0, 4500.0)],
    "c_db": [6.0, 9.0, 12.0, 15.0],
    "min_s": [0.08, 0.12, 0.2],
}


def contrast(x, sr, wb):
    N, H = int(0.064 * sr), int(0.010 * sr)
    fr = np.lib.stride_tricks.sliding_window_view(x, N)[::H] * np.hanning(N)
    mag = np.abs(np.fft.rfft(fr, axis=1))
    fq = np.fft.rfftfreq(N, 1 / sr)
    hi = min(wb[1], sr / 2 - 50)
    band = (fq >= wb[0]) & (fq <= hi)
    ref = (fq >= 1000) & (fq <= min(6000, sr / 2 - 50))
    c = 20 * np.log10((mag[:, band].max(1) + 1e-9) / (np.median(mag[:, ref], 1) + 1e-9))
    return c - np.median(c), N, H


def detect(x, sr, wb, c_db, min_s):
    c, N, H = contrast(x, sr, wb)
    on = c >= c_db
    for k in (1, 2):
        on = on | (np.roll(on, k) & np.roll(on, -k))
    dt = H / sr
    out = []
    i = 0
    while i < len(on):
        if not on[i]:
            i += 1
            continue
        j = i
        while j < len(on) and on[j]:
            j += 1
        if (j - i) * dt >= min_s:
            t0, t1 = i * dt + N / sr / 2, j * dt + N / sr / 2
            if out and t0 - out[-1][1] < MERGE_S:
                out[-1] = (out[-1][0], t1)
            else:
                out.append((t0, t1))
        i = j
    return out


def f1(det, truth):
    tp = len(pair(det, truth))
    p = tp / max(1, len(det))
    r = tp / max(1, len(truth))
    return (2 * p * r / max(1e-9, p + r)), p, r, len(det)


def main():
    D = Path(__file__).parent
    truth = json.loads((D / "wh_truth.json").read_text())
    res = {}
    for sr in (8000, 16000):
        x, r = W.load_wav(D / AUDIO[("mue", sr)])
        t = [e["start"] for e in truth["mue"]]
        best = None
        for wb, c, m in itertools.product(GRID["wb"], GRID["c_db"], GRID["min_s"]):
            s = f1([e[0] for e in detect(x, r, wb, c, m)], t)
            if best is None or s[0] > best[0][0]:
                best = (s, (wb, c, m))
        (fm, pm, rm, nm), (wb, c, m) = best
        xl, rl = W.load_wav(D / AUDIO[("lei", sr)])
        fl, pl, rcl, nl = f1(
            [e[0] for e in detect(xl, rl, wb, c, m)], [e["start"] for e in truth["lei"]]
        )
        res[str(sr)] = {
            "chosen_on_mue": {"band_hz": wb, "c_db": c, "min_s": m},
            "mue_dev": {
                "f1": round(fm, 3),
                "precision": round(pm, 3),
                "recall": round(rm, 3),
                "detected": nm,
                "truth": len(t),
            },
            "lei_holdout": {
                "f1": round(fl, 3),
                "precision": round(pl, 3),
                "recall": round(rcl, 3),
                "detected": nl,
                "truth": len(truth["lei"]),
            },
        }
    print(json.dumps(res, indent=1))
    (D / "wh2_eval.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
