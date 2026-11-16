"""Pre-labels for the gold standard clips (ml/gold/gold_clips.json, inserted as CLIPS by
prelabel_push.py), so the owner only confirms or corrects (docs/plans/tracking-strategie.md):

- clips/<id>.mp4: the clip as decoded frame by frame from the segment (so frame k of the mp4 is
  frame start + k of the segment), H.264 with a keyframe every 6 frames for exact seeking in the
  browser;
- pre.json: per clip and frame the ball net's top 5 peaks (3-frame net MODEL, every frame) and
  OWLv2's ball boxes (every OWL_EVERY-th frame), in 1280 px frame coordinates.
Pre-labels are suggestions only; the gold labels are what the owner confirms.
"""

import glob
import json
import os
import subprocess
import time

import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision
from transformers import Owlv2ForObjectDetection, Owlv2Processor

CLIPS = json.loads(r"""__CLIPS__""")
MODEL = "__MODEL__"
OWL_EVERY = 2
IN = "/kaggle/input"
OUT = "/kaggle/working"
os.makedirs(f"{OUT}/clips", exist_ok=True)
dev = "cuda"
T0 = time.time()


class BallNet3(nn.Module):  # as in ml/ball/kaggle/train_r6.py
    def __init__(s):
        super().__init__()
        r = torchvision.models.resnet18(weights=None)
        c1 = nn.Conv2d(9, 64, 7, 2, 3, bias=False)
        s.stem = nn.Sequential(c1, r.bn1, r.relu, r.maxpool)
        s.l1 = r.layer1
        s.l2 = r.layer2
        s.up = nn.Sequential(nn.Conv2d(128, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU())
        s.head = nn.Sequential(
            nn.Conv2d(128, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(), nn.Conv2d(64, 1, 1)
        )
        s.register_buffer("mean", torch.tensor([0.485, 0.456, 0.406] * 3).view(1, 9, 1, 1) * 255)
        s.register_buffer("std", torch.tensor([0.229, 0.224, 0.225] * 3).view(1, 9, 1, 1) * 255)

    def forward(s, x):
        x = (x - s.mean) / s.std
        a = s.l1(s.stem(x))
        b = s.l2(a)
        b = F.interpolate(s.up(b), size=a.shape[-2:], mode="bilinear", align_corners=False)
        return s.head(torch.cat([a, b], 1))


def peaks(hm, k=5):
    hm = hm.copy()
    out = []
    for _ in range(k):
        y, x = np.unravel_index(hm.argmax(), hm.shape)
        out.append([int(x * 4 + 2), int(y * 4 + 2), round(float(hm[y, x]), 3)])
        hm[max(0, y - 6) : y + 6, max(0, x - 6) : x + 6] = 0
    return out


net = BallNet3()
net.load_state_dict(
    torch.load(
        glob.glob(f"{IN}/**/{MODEL}", recursive=True)[0], map_location="cpu", weights_only=True
    )
)
net.to(dev).eval()

# OWLv2 (Apache-2.0) on 480 px tiles upscaled to 960, as in ml/ball/kaggle/owl_gpu.py
QUERIES = ["a photo of a handball", "a ball", "a small ball in the air"]
TILE = 480
XS = (0, 400, 800)
YS = (0, 240)
oname = "google/owlv2-base-patch16-ensemble"
proc = Owlv2Processor.from_pretrained(oname)
owl = Owlv2ForObjectDetection.from_pretrained(oname, torch_dtype=torch.float16).to(dev).eval()
tok = proc(text=[QUERIES], return_tensors="pt")
ids, mask = tok["input_ids"].to(dev), tok["attention_mask"].to(dev)
MEAN = torch.tensor([0.48145466, 0.4578275, 0.40821073], device=dev).view(1, 3, 1, 1)
STD = torch.tensor([0.26862954, 0.26130258, 0.27577711], device=dev).view(1, 3, 1, 1)


@torch.no_grad()
def owl_detect(fr, thr=0.05, max_side=60):
    tiles, offs = [], []
    for y0 in YS:
        for x0 in XS:
            t = fr[y0 : y0 + TILE, x0 : x0 + TILE]
            if t.shape[0] < TILE or t.shape[1] < TILE:
                t = cv2.copyMakeBorder(
                    t,
                    0,
                    TILE - t.shape[0],
                    0,
                    TILE - t.shape[1],
                    cv2.BORDER_CONSTANT,
                    value=(128, 128, 128),
                )
            tiles.append(cv2.cvtColor(t, cv2.COLOR_BGR2RGB))
            offs.append((x0, y0))
    x = torch.from_numpy(np.stack(tiles)).to(dev).permute(0, 3, 1, 2).float() / 255
    x = (
        (F.interpolate(x, size=(960, 960), mode="bilinear", align_corners=False) - MEAN) / STD
    ).half()
    o = owl(
        input_ids=ids.repeat(len(tiles), 1),
        attention_mask=mask.repeat(len(tiles), 1),
        pixel_values=x,
    )
    sc_all = o.logits.float().sigmoid().max(-1).values
    boxes = o.pred_boxes.float()
    res = []
    for i, (x0, y0) in enumerate(offs):
        for k in (sc_all[i] >= thr).nonzero().flatten().tolist():
            cx, cy, bw, bh = (boxes[i, k] * TILE).tolist()
            if bw <= max_side and bh <= max_side:
                res.append(
                    [
                        round(x0 + cx, 1),
                        round(y0 + cy, 1),
                        round(bw, 1),
                        round(bh, 1),
                        round(float(sc_all[i, k]), 3),
                    ]
                )
    res.sort(key=lambda r: -r[4])
    return res[:8]


FILES = {os.path.basename(a): a for a in glob.glob(f"{IN}/**/*.mp4", recursive=True)}
pre = {}
for c in CLIPS:
    path = FILES.get(c["file"])
    if not path:
        print("missing", c["file"], flush=True)
        continue
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or c["fps"]
    G = 3 if fps > 40 else 2
    f0 = int(round(c["start_ms"] / 1000 * fps))
    n = int(round(c["dur_ms"] / 1000 * fps))
    cap.set(cv2.CAP_PROP_POS_FRAMES, f0 - G)
    frames = []
    for _ in range(n + 2 * G):
        ok, im = cap.read()
        if not ok:
            break
        if im.shape[1] != 1280:
            im = cv2.resize(
                im, (1280, round(im.shape[0] * 1280 / im.shape[1])), interpolation=cv2.INTER_AREA
            )
        frames.append(im)
    cap.release()
    n = len(frames) - 2 * G
    if n <= 0:
        print("short", c["id"], flush=True)
        continue
    H, W = frames[0].shape[:2]
    ff = subprocess.Popen(
        [
            "ffmpeg",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "bgr24",
            "-s",
            f"{W}x{H}",
            "-r",
            str(fps),
            "-i",
            "-",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "20",
            "-g",
            "6",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            f"{OUT}/clips/{c['id']}.mp4",
        ],
        stdin=subprocess.PIPE,
    )
    for im in frames[G : G + n]:
        ff.stdin.write(im.tobytes())
    ff.stdin.close()
    ff.wait()
    h2 = H // 32 * 32
    recs = []
    for k in range(n):
        t = G + k
        rgb = [cv2.cvtColor(frames[j][:h2], cv2.COLOR_BGR2RGB) for j in (t - G, t, t + G)]
        x = torch.from_numpy(np.concatenate(rgb, 2).transpose(2, 0, 1)[None].astype(np.float32)).to(
            dev
        )
        with torch.no_grad():
            hm = torch.sigmoid(net(x))[0, 0].float().cpu().numpy()
        r = {"net": peaks(hm)}
        if k % OWL_EVERY == 0:
            r["owl"] = owl_detect(frames[t])
        recs.append(r)
    pre[c["id"]] = {
        **c,
        "seg_frame0": f0,
        "frames": n,
        "fps_read": fps,
        "gap": G,
        "w": W,
        "h": H,
        "pre": recs,
    }
    print(c["id"], n, "frames", f"{time.time() - T0:.0f}s", flush=True)
json.dump({"model": MODEL, "owl_every": OWL_EVERY, "clips": pre}, open(f"{OUT}/pre.json", "w"))
print("done", len(pre), "clips", f"{time.time() - T0:.0f}s")
