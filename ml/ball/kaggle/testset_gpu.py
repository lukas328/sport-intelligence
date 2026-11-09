"""Second ball test set on a Kaggle GPU: for each pick of `testset_pick.py` (PICKS, inserted by
`testset_push.py`) the triplet t-G, t, t+G as one 3x1280-wide JPEG (t/<id>.jpg), a 2-second clip
around it (v/<id>.mp4, the frame 1 s in), and OWLv2's ball boxes on the three frames as a
pre-filled suggestion for the labelling page (items.json). Same OWLv2 setup as owl_gpu.py."""
import glob, json, os, shutil, subprocess, sys, time
import cv2, numpy as np, torch
from transformers import Owlv2ForObjectDetection, Owlv2Processor

PICKS = json.loads(r'''__PICKS__''')
T0 = time.time()
IN = os.environ.get("OWL_INPUT", "/kaggle/input"); OUT = os.environ.get("OWL_OUT", "/kaggle/working")
os.makedirs(f"{OUT}/t", exist_ok=True); os.makedirs(f"{OUT}/v", exist_ok=True)
FFMPEG = shutil.which("ffmpeg")
if not FFMPEG:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "imageio-ffmpeg"], check=True)
    import imageio_ffmpeg
    FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

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
    """Boxes [cx, cy, w, h, score, query] in 1280-wide frame pixels."""
    h, w = frame_bgr.shape[:2]
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
    logits = out.logits.float().sigmoid()
    boxes = out.pred_boxes.float()
    res = []
    for i, (x0, y0) in enumerate(offs):
        sc, q = logits[i].max(-1)
        for k in (sc >= thr).nonzero().flatten().tolist():
            cx, cy, bw, bh = (boxes[i, k] * TILE).tolist()
            if bw > max_side or bh > max_side or y0 + cy >= h:
                continue
            res.append([round(x0 + cx, 1), round(y0 + cy, 1), round(bw, 1), round(bh, 1), round(float(sc[k]), 3), int(q[k])])
    # one box per spot (tiles overlap): keep the best within 12 px
    res.sort(key=lambda b: -b[4]); keep = []
    for b in res:
        if all(np.hypot(b[0] - k[0], b[1] - k[1]) > 12 for k in keep):
            keep.append(b)
    return keep[:8]


FILES = {os.path.basename(a): a for a in glob.glob(f"{IN}/**/*.mp4", recursive=True)}
print(len(FILES), "segments in the inputs", flush=True)
items = []
for p in PICKS:
    path = FILES.get(p["file"])
    if not path:
        print("missing", p["file"], flush=True); continue
    cap = cv2.VideoCapture(path); fps = cap.get(cv2.CAP_PROP_FPS) or 25.0; n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    G = 3 if fps > 40 else 2
    fr = min(max(int(round(p["t_ms"] / 1000 * fps)), int(fps * 1.2)), n - int(fps * 1.2))
    cap.set(cv2.CAP_PROP_POS_FRAMES, fr - G); ims = []
    for k in range(2 * G + 1):
        ok, f = cap.read()
        if not ok:
            break
        if k in (0, G, 2 * G):
            ims.append(f)
    cap.release()
    if len(ims) < 3:
        print("short read", p["id"], flush=True); continue
    sc = 1280 / ims[0].shape[1]
    ims = [cv2.resize(im, (1280, round(im.shape[0] * sc)), interpolation=cv2.INTER_AREA) for im in ims]
    H = ims[0].shape[0]
    cv2.imwrite(f"{OUT}/t/{p['id']}.jpg", np.concatenate(ims, 1), [cv2.IMWRITE_JPEG_QUALITY, 74])
    t0 = fr / fps - 1.0
    subprocess.run([FFMPEG, "-v", "error", "-y", "-ss", f"{t0:.4f}", "-i", path, "-t", "2.0", "-an",
                    "-vf", "scale=960:-2", "-c:v", "libx264", "-preset", "medium", "-crf", "30",
                    "-pix_fmt", "yuv420p", "-movflags", "+faststart", f"{OUT}/v/{p['id']}.mp4"], check=True)
    owl = [detect(im) for im in ims]
    items.append({"id": p["id"], "hall": p["game"], "video": f"{p['dataset']}/{p['file']}", "frame": fr, "gap": G,
                  "fps": fps, "scale": round(sc, 5), "w": 1280, "h": H, "clock_running": p["clock_running"],
                  "owl": owl[1], "owl_prev": owl[0], "owl_next": owl[2]})
    print(len(items), p["id"], f"{time.time() - T0:.0f}s", flush=True)
json.dump(items, open(f"{OUT}/items.json", "w"))
print("done", len(items), f"{time.time() - T0:.0f}s")
