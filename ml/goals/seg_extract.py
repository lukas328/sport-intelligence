"""Heavy pass over whole 3-minute ingest segments, run once: per-frame cheap signals for goal moments.

`extract.py` does the same for 9-second broadcast clips; this one is built for the ingest's 3-minute
segments (1280 wide, 50/60 fps, panning or fixed camera, with or without a score overlay) and keeps
only what the cheap cues need, so a segment costs a few minutes of CPU and well under 1 MB on disk.
Frames are decoded without the non-reference frames (about 30 Hz at 60 fps).

Per segment (one compressed npz):
- overlay: `scoreboard.find_overlay` boxes (empty for a fixed camera); they are masked out of the
  motion signals. When the boxes hold a score field ("12 : 9"), PP-OCR (the `hallboard` models)
  reads it every 0.5 s; without one, the hall scoreboard every 2 s (`hallboard.parse_board`).
  Reference only, for labels: the cues never look at it;
- every decoded frame: camera pan (phase correlation on a 320x180 grey image with the overlay masked,
  in 1280-px units), correlation response, pan-compensated motion energy;
- 10 Hz: dense optical flow (Farneback, 320x180) between frames 0.1 s apart, minus the camera's
  median flow. Moving pixels (|residual| > 0.8 px) give a 16-bin histogram over the image x of their
  count and of their summed residual x-flow ("flow towards a half"), plus their share;
- 2 Hz: YOLOX-m people (boxes, score) on the full frame;
- 1 Hz: a 256x144 JPEG thumbnail (looking at failures).

usage: nice -n 10 uv run --project packages/vision python ml/goals/seg_extract.py OUT_DIR SEG.mp4 [...]
       [--threads 2] [--det-every 0.5] [--no-det]
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

import av
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "packages/vision"))
from handball_vision import scoreboard  # noqa: E402
from handball_vision.detection import YoloxDetector  # noqa: E402
from handball_vision.hallboard import CLOCK, Token, parse_board  # noqa: E402
from handball_vision.numbers import NumberReader  # noqa: E402

W, H = 320, 180  # analysis size (1280x720 / 4)
FLOW_DT = 0.1
NBINS = 16
MOVE_PX = 0.8


def decode(path: Path, skip: str = "NONREF"):
    """(seconds from the first frame, BGR frame scaled to 1280 wide)."""
    c = av.open(str(path))
    s = c.streams.video[0]
    s.thread_type = "AUTO"
    s.codec_context.thread_count = 2
    s.codec_context.skip_frame = skip
    t0 = None
    try:
        for fr in c.decode(s):
            if fr.time is None:
                continue
            t0 = float(fr.time) if t0 is None else t0
            img = fr.to_ndarray(format="bgr24")
            if img.shape[1] != 1280:
                img = cv2.resize(img, (1280, round(img.shape[0] * 1280 / img.shape[1])),
                                 interpolation=cv2.INTER_AREA)
            yield float(fr.time) - t0, img
    finally:
        c.close()


SCORE_RE = re.compile(r"^(\d{1,2})\s*[:\-.]\s*(\d{1,2})$")


def _tokens(ocr, img: np.ndarray, x0: int = 0, y0: int = 0) -> list[Token]:
    crops, kept = [], []
    for b in ocr.detect(img):
        bx1, by1 = np.asarray(b).min(axis=0)
        bx2, by2 = np.asarray(b).max(axis=0)
        if by2 - by1 < 8:
            continue
        crops.append(img[max(0, int(by1) - 2):int(by2) + 2, max(0, int(bx1) - 2):int(bx2) + 2])
        kept.append((float(bx1) + x0, float(by1) + y0, float(bx2) + x0, float(by2) + y0))
    return [Token(t, *bx, sc) for (t, sc), bx in zip(ocr.recognise(crops), kept, strict=True) if sc >= 0.6]


def overlay_setup(path: Path, ocr) -> tuple[list[tuple[int, int, int, int]], tuple[int, int, int, int] | None]:
    """Overlay boxes from key frames (`scoreboard.find_overlay`, empty for a fixed camera) and the
    box of the score field ("12 : 9") inside them: the score-like token whose value stays the same
    on most key frames (the clock changes on every one)."""
    keys = [(t, f) for t, f in decode(path, "NONKEY")]
    if len(keys) > 24:
        keys = [keys[round(k * (len(keys) - 1) / 23)] for k in range(24)]
    boxes = scoreboard.find_overlay([f for _, f in keys])
    if not boxes:
        return [], None
    h, w = keys[0][1].shape[:2]
    groups: list[list] = []  # [box, values]
    for band in ([b for b in boxes if b[1] + b[3] / 2 < h / 2], [b for b in boxes if b[1] + b[3] / 2 >= h / 2]):
        if not band:
            continue
        x, y, bw, bh = scoreboard._union(band, 10, (w, h))
        for _, f in keys[::2]:
            for tk in _tokens(ocr, f[y:y + bh, x:x + bw], x, y):
                if not SCORE_RE.match(tk.text.strip()):
                    continue
                bx = (tk.x1, tk.y1, tk.x2, tk.y2)
                for g in groups:
                    if abs(g[0][0] - bx[0]) < 12 and abs(g[0][1] - bx[1]) < 8:
                        g[1].append(tk.text.replace(" ", ""))
                        break
                else:
                    groups.append([bx, [tk.text.replace(" ", "")]])
    # a clock shows leading zeros ("01:05", "39:07") and changes; a score does neither
    cands = [g for g in groups if len(g[1]) >= 3 and len(set(g[1])) <= max(3, 0.6 * len(g[1]))
             and not any(re.match(r"^0\d|.*[:\-.]0\d$", v) for v in g[1])]
    if not cands:
        return boxes, None
    x1, y1, x2, y2 = min(cands, key=lambda g: (len(set(g[1])), -len(g[1])))[0]
    px, py = 0.3 * (x2 - x1) + 4, 0.25 * (y2 - y1) + 3
    return boxes, (int(max(0, x1 - px)), int(max(0, y1 - py)), int(min(w, x2 + px)), int(min(h, y2 + py)))


def read_score(ocr, img: np.ndarray, box: tuple[int, int, int, int]) -> tuple[int, int] | None:
    x1, y1, x2, y2 = box
    text, sc = ocr.recognise([img[y1:y2, x1:x2]])[0]
    m = SCORE_RE.match(text.strip())
    return (int(m.group(1)), int(m.group(2))) if m and sc >= 0.7 else None


class BoardScore:
    """Hall scoreboard score (no overlay): PP-OCR + `hallboard.parse_board` every 2 s, on a window
    around the board's last position, on the full frame at most every 10 s while it is lost."""

    def __init__(self, ocr) -> None:
        self.ocr = ocr
        self.win: tuple[int, int, int, int] | None = None
        self.last_full = -1e9
        self.reads: list[tuple[int, int | None, int | None]] = []

    def add(self, t: float, img: np.ndarray) -> None:
        h, w = img.shape[:2]
        r = None
        if self.win is not None:
            x0, y0, x1, y1 = self.win
            r = parse_board(_tokens(self.ocr, img[y0:y1, x0:x1], x0, y0))
        if r is None and t - self.last_full >= 10:
            self.last_full = t
            toks = _tokens(self.ocr, img)
            r = parse_board(toks)
            self.win = None
            if r is not None:
                ck = max((tk for tk in toks if CLOCK.match(tk.text.strip())), key=lambda tk: tk.score * tk.h)
                cw, ch = ck.x2 - ck.x1, ck.y2 - ck.y1
                self.win = (int(max(0, ck.x1 - 5 * cw)), int(max(0, ck.y1 - 3 * ch)),
                            int(min(w, ck.x2 + 5 * cw)), int(min(h, ck.y2 + 3 * ch)))
        if r is not None and (r.home is not None or r.away is not None):
            self.reads.append((round(t * 1000), r.home, r.away))


def run(path: Path, out: Path, det: YoloxDetector | None, ocr, det_every: float, board: bool) -> None:
    t_start = time.time()
    boxes, score_box = overlay_setup(path, ocr)
    scores: list[tuple[int, int, int]] = []
    hall = BoardScore(ocr) if score_box is None and board else None
    mask = np.ones((H, W), np.float32)
    for x, y, bw, bh in boxes:
        mask[max(0, y // 4 - 2):(y + bh) // 4 + 2, max(0, x // 4 - 2):(x + bw) // 4 + 2] = 0
    win = cv2.createHanningWindow((W, H), cv2.CV_32F) * mask
    valid = mask > 0
    xs = np.arange(W)
    bins = np.minimum(xs * NBINS // W, NBINS - 1)
    ts, pan, resp, energy = [], [], [], []
    ft, fcnt, fsum, fshare, fcam = [], [], [], [], []
    people: list[tuple[float, float, float, float, float, float]] = []
    thumbs: list[bytes] = []
    thumb_t: list[float] = []
    prev = None
    flow_ref: tuple[float, np.ndarray] | None = None
    next_det = next_thumb = next_ocr = 0.0
    for t, img in decode(path):
        g = cv2.cvtColor(cv2.resize(img, (W, H), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)
        gf = g.astype(np.float32)
        if prev is None:
            d, r, e = (0.0, 0.0), 1.0, 0.0
        else:
            # phaseCorrelate applies the window to its inputs in place: hand it copies
            d, r = cv2.phaseCorrelate(prev.copy(), gf.copy(), win)
            m = np.float32([[1, 0, d[0]], [0, 1, d[1]]])
            warped = cv2.warpAffine(prev, m, (W, H), borderMode=cv2.BORDER_REPLICATE)
            diff = np.abs(gf - warped)
            pad = 8 + int(abs(d[0])) + 1
            sub = (diff * mask)[8:-8, pad:-pad] if pad < W // 2 - 8 else diff * mask
            e = float(sub.mean())
        prev = gf
        ts.append(t)
        pan.append((d[0] * 4, d[1] * 4))
        resp.append(r)
        energy.append(e)
        if flow_ref is None or t - flow_ref[0] >= FLOW_DT - 0.005:
            if flow_ref is not None:
                fl = cv2.calcOpticalFlowFarneback(flow_ref[1], g, None, 0.5, 3, 11, 2, 5, 1.1, 0)
                cam = np.median(fl[valid], axis=0)
                res = fl - cam
                mv = (np.hypot(res[..., 0], res[..., 1]) > MOVE_PX) & valid
                cnt = np.bincount(bins[np.nonzero(mv)[1]], minlength=NBINS)
                sx = np.bincount(bins[np.nonzero(mv)[1]], weights=res[..., 0][mv], minlength=NBINS)
                ft.append(t)
                fcnt.append(cnt)
                fsum.append(sx)
                fshare.append(mv.sum() / valid.sum())
                fcam.append(cam)
            flow_ref = (t, g)
        if det is not None and t >= next_det - 1e-3:
            next_det += det_every
            for dd in det.detect([img])[0]:
                if dd.cls == "person":
                    people.append((t, dd.x1, dd.y1, dd.x2, dd.y2, dd.score))
        if t >= next_thumb - 1e-3:
            next_thumb += 1.0
            ok, buf = cv2.imencode(".jpg", cv2.resize(img, (256, 144), interpolation=cv2.INTER_AREA),
                                   [cv2.IMWRITE_JPEG_QUALITY, 70])
            thumbs.append(buf.tobytes())
            thumb_t.append(t)
        if score_box is not None and t >= next_ocr - 1e-3:
            next_ocr += 0.5
            got = read_score(ocr, img, score_box)
            if got:
                scores.append((round(t * 1000), *got))
        elif hall is not None and t >= next_ocr - 1e-3:
            next_ocr += 2.0
            hall.add(t, img)
    lens = np.array([len(b) for b in thumbs])
    np.savez_compressed(
        out,
        t=np.array(ts, np.float32), pan=np.array(pan, np.float32), resp=np.array(resp, np.float32),
        energy=np.array(energy, np.float32),
        flow_t=np.array(ft, np.float32), flow_cnt=np.array(fcnt, np.float32).reshape(-1, NBINS),
        flow_sum=np.array(fsum, np.float32).reshape(-1, NBINS), flow_share=np.array(fshare, np.float32),
        flow_cam=np.array(fcam, np.float32).reshape(-1, 2),
        people=np.array(people, np.float32).reshape(-1, 6),
        overlay_boxes=np.array(boxes, np.int32).reshape(-1, 4),
        score_box=np.array(score_box or (), np.int32),
        score_reads=np.array(scores, np.int32).reshape(-1, 3),
        board_reads=np.array([(tm, -1 if a is None else a, -1 if b is None else b)
                              for tm, a, b in (hall.reads if hall else [])], np.int32).reshape(-1, 3),
        thumb_t=np.array(thumb_t, np.float32), thumb_len=lens,
        thumb_jpg=np.frombuffer(b"".join(thumbs), np.uint8),
    )
    print(f"{path.name}: {len(ts)} frames ({ts[-1]:.0f} s), {len(people)} people, overlay boxes {len(boxes)}, "
          f"score box {score_box}, {len(scores)} overlay / {len(hall.reads) if hall else 0} board reads, "
          f"{time.time() - t_start:.0f} s", flush=True)


def thumb(z, k: int) -> np.ndarray:
    """Decode thumbnail k of a cached segment."""
    off = np.r_[0, np.cumsum(z["thumb_len"])]
    return cv2.imdecode(z["thumb_jpg"][off[k]:off[k + 1]], cv2.IMREAD_COLOR)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("out", type=Path)
    ap.add_argument("segs", type=Path, nargs="+")
    ap.add_argument("--threads", type=int, default=2)
    ap.add_argument("--det-every", type=float, default=0.5)
    ap.add_argument("--no-det", action="store_true")
    ap.add_argument("--no-board", action="store_true", help="no hall-board score reading")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    cv2.setNumThreads(a.threads)
    det = None if a.no_det else YoloxDetector(ROOT / "data/models/yolox_m.onnx", threads=a.threads)
    models = ROOT / "data/models"
    ocr = NumberReader(models / "ch_PP-OCRv4_det_infer.onnx", models / "ch_PP-OCRv4_rec_infer.onnx",
                       threads=a.threads)
    for seg in a.segs:
        out = a.out / (seg.stem + ".npz")
        if out.exists():
            continue
        try:
            run(seg, out, det, ocr, a.det_every, not a.no_board)
        except Exception as exc:  # keep going over the batch
            print(f"{seg.name}: FAILED {exc!r}", flush=True)


if __name__ == "__main__":
    main()
