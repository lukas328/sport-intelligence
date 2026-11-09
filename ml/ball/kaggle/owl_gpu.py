"""Open-vocabulary ball pseudo-labels: OWLv2 (Apache-2.0) on 480 px tiles (upscaled to 960) of
1280-wide frames. Bench frames first (to measure it against the user's labels), then bursts of 5
consecutive frames every 6 s from the ingested game segments; a later step keeps only boxes the
temporal path confirms."""
import glob, json, os, time
import cv2, numpy as np, torch
from transformers import Owlv2ForObjectDetection, Owlv2Processor

T0 = time.time(); BUDGET = float(os.environ.get("OWL_BUDGET_H", "8.3")) * 3600
IN = os.environ.get("OWL_INPUT", "/kaggle/input"); OUT = os.environ.get("OWL_OUT", "/kaggle/working"); os.makedirs(f"{OUT}/segs", exist_ok=True)
QUERIES = ["a photo of a handball", "a ball", "a small ball in the air"]
TILE = 480; XS = (0, 400, 800); YS = (0, 240)
dev = "cuda"
name = "google/owlv2-base-patch16-ensemble"
proc = Owlv2Processor.from_pretrained(name)
model = Owlv2ForObjectDetection.from_pretrained(name, torch_dtype=torch.float16).to(dev).eval()
tok = proc(text=[QUERIES], return_tensors="pt")
ids, mask = tok["input_ids"].to(dev), tok["attention_mask"].to(dev)
MEAN = torch.tensor([0.48145466, 0.4578275, 0.40821073], device=dev).view(1, 3, 1, 1)
STD = torch.tensor([0.26862954, 0.26130258, 0.27577711], device=dev).view(1, 3, 1, 1)


@torch.no_grad()
def detect(frame_bgr, thr=0.04, max_side=60):
    h, w = frame_bgr.shape[:2]
    if w != 1280:
        frame_bgr = cv2.resize(frame_bgr, (1280, round(h * 1280 / w))); h, w = frame_bgr.shape[:2]
    tiles, offs = [], []
    for y0 in YS:
        for x0 in XS:
            t = frame_bgr[y0:y0 + TILE, x0:x0 + TILE]
            if t.shape[0] < TILE or t.shape[1] < TILE:
                t = cv2.copyMakeBorder(t, 0, TILE - t.shape[0], 0, TILE - t.shape[1], cv2.BORDER_CONSTANT, value=(128, 128, 128))
            tiles.append(cv2.cvtColor(t, cv2.COLOR_BGR2RGB)); offs.append((x0, y0))
    x = torch.from_numpy(np.stack(tiles)).to(dev).permute(0, 3, 1, 2).float() / 255
    x = torch.nn.functional.interpolate(x, size=(960, 960), mode="bilinear", align_corners=False)
    x = ((x - MEAN) / STD).half()
    n = x.shape[0]
    out = model(input_ids=ids.repeat(n, 1), attention_mask=mask.repeat(n, 1), pixel_values=x)
    logits = out.logits.float().sigmoid()  # n, boxes, queries
    boxes = out.pred_boxes.float()  # cx cy w h in [0,1] of the tile
    res = []
    for i, (x0, y0) in enumerate(offs):
        sc, q = logits[i].max(-1)
        keep = (sc >= thr).nonzero().flatten()
        for k in keep.tolist():
            cx, cy, bw, bh = (boxes[i, k] * TILE).tolist()
            if bw > max_side or bh > max_side:
                continue
            res.append([round(x0 + cx, 1), round(y0 + cy, 1), round(bw, 1), round(bh, 1), round(float(sc[k]), 3), int(q[k])])
    return res


# 1) bench frames (centre frame of each labelled triplet)
ALL = glob.glob(f"{IN}/**/*", recursive=True)
print(len(ALL), "input files", sorted({os.path.dirname(a) for a in ALL})[:40], flush=True)
JPG = {os.path.basename(a)[:-4]: a for a in ALL if a.endswith(".jpg")}
B = [a for a in ALL if a.endswith(".json") and os.path.basename(os.path.dirname(a)) == "labels"]
bench = {}
for f in B:
    lab = json.load(open(f)); i = os.path.basename(f)[:-5]
    im = cv2.imread(JPG[i]) if i in JPG else None
    if im is None:
        continue
    W = lab["w"]; bench[i] = detect(im[:, W:2 * W])
json.dump(bench, open(f"{OUT}/bench_owl.json", "w"))
print("bench", len(bench), "frames", f"{time.time() - T0:.0f}s", flush=True)

# 2) bursts from the ingested segments
vids = sorted(a for a in ALL if a.endswith(".mp4"))
print(len(vids), "segments", flush=True)
for v in vids:
    if time.time() - T0 > BUDGET:
        print("budget reached", flush=True); break
    name_ = os.path.basename(v)[:-4]
    if os.path.exists(f"{OUT}/segs/{name_}.json"):
        continue
    cap = cv2.VideoCapture(v); fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    stride = max(1, round(fps / 25)); every = int(round(6 * fps)); n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    want = {}
    for s in range(int(fps), n - 6 * stride, every):
        for k in range(5):
            want[s + k * stride] = s
    bursts = {}; f = 0; t1 = time.time()
    while True:
        ok = cap.grab()
        if not ok:
            break
        if f in want:
            ok, im = cap.retrieve()
            if ok:
                bursts.setdefault(want[f], []).append({"f": f, "boxes": detect(im)})
        f += 1
    cap.release()
    json.dump({"file": os.path.basename(v), "fps": fps, "stride": stride,
               "bursts": [{"frame0": k, "frames": fr} for k, fr in sorted(bursts.items())]},
              open(f"{OUT}/segs/{name_}.json", "w"))
    print(name_, len(bursts), "bursts", f"{time.time() - t1:.0f}s", f"total {time.time() - T0:.0f}s", flush=True)
print("done", f"{time.time() - T0:.0f}s")
