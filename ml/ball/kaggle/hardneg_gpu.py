"""Round 7's confident peaks on frames it never saw (picks from hardneg_pick.py, inserted as PICKS
by hardneg_push.py): for every peak >= MIN_SCORE (at most TOP per frame) a crop of the three frames
(c/<id>.jpg, 3 x 96 px side by side, 2x enlarged) and a context image of the centre frame with
the peak circled (x/<id>.jpg, 640 wide), for a one-click "ball / no ball" labelling page."""
import glob, json, os, time
import cv2, numpy as np, torch, torch.nn as nn, torch.nn.functional as F, torchvision

PICKS = json.loads(r'''__PICKS__''')
MIN_SCORE = 0.4; TOP = 3; R = 48
IN = "/kaggle/input"; OUT = "/kaggle/working"
os.makedirs(f"{OUT}/c", exist_ok=True); os.makedirs(f"{OUT}/x", exist_ok=True)
dev = "cuda" if torch.cuda.is_available() else "cpu"


class BallNet3(nn.Module):  # as in train_r6.py / bench_testset2.py
    def __init__(s):
        super().__init__()
        r = torchvision.models.resnet18(weights=None)
        c1 = nn.Conv2d(9, 64, 7, 2, 3, bias=False)
        s.stem = nn.Sequential(c1, r.bn1, r.relu, r.maxpool); s.l1 = r.layer1; s.l2 = r.layer2
        s.up = nn.Sequential(nn.Conv2d(128, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU())
        s.head = nn.Sequential(nn.Conv2d(128, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(), nn.Conv2d(64, 1, 1))
        s.register_buffer("mean", torch.tensor([0.485, 0.456, 0.406] * 3).view(1, 9, 1, 1) * 255)
        s.register_buffer("std", torch.tensor([0.229, 0.224, 0.225] * 3).view(1, 9, 1, 1) * 255)

    def forward(s, x):
        x = (x - s.mean) / s.std; a = s.l1(s.stem(x)); b = s.l2(a)
        b = F.interpolate(s.up(b), size=a.shape[-2:], mode="bilinear", align_corners=False)
        return s.head(torch.cat([a, b], 1))


def peaks(hm, k=5):
    hm = hm.copy(); out = []
    for _ in range(k):
        y, x = np.unravel_index(hm.argmax(), hm.shape)
        out.append((x * 4 + 2, y * 4 + 2, float(hm[y, x]))); hm[max(0, y - 6):y + 6, max(0, x - 6):x + 6] = 0
    return out


net = BallNet3()
net.load_state_dict(torch.load(glob.glob(f"{IN}/**/ball_r7.pt", recursive=True)[0], map_location="cpu", weights_only=True))
net.to(dev).eval()
FILES = {os.path.basename(a): a for a in glob.glob(f"{IN}/**/*.mp4", recursive=True)}
items = []; T0 = time.time()
for p in PICKS:
    path = FILES.get(p["file"])
    if not path:
        continue
    cap = cv2.VideoCapture(path); fps = cap.get(cv2.CAP_PROP_FPS) or 25.0; n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    G = 3 if fps > 40 else 2
    fr = min(max(int(round(p["t_ms"] / 1000 * fps)), G + 1), n - G - 2)
    cap.set(cv2.CAP_PROP_POS_FRAMES, fr - G); ims = []
    for k in range(2 * G + 1):
        ok, f = cap.read()
        if not ok:
            break
        if k in (0, G, 2 * G):
            ims.append(f)
    cap.release()
    if len(ims) < 3:
        continue
    sc = 1280 / ims[0].shape[1]
    ims = [cv2.resize(im, (1280, round(im.shape[0] * sc)), interpolation=cv2.INTER_AREA) for im in ims]
    H = ims[0].shape[0]; h2 = H // 32 * 32
    rgb = [cv2.cvtColor(im[:h2], cv2.COLOR_BGR2RGB) for im in ims]
    x = torch.from_numpy(np.concatenate(rgb, 2).transpose(2, 0, 1)[None].astype(np.float32)).to(dev)
    with torch.no_grad():
        hm = torch.sigmoid(net(x))[0, 0].float().cpu().numpy()
    kept = [pk for pk in peaks(hm) if pk[2] >= MIN_SCORE][:TOP]
    for rank, (px, py, s) in enumerate(kept):
        cid = f"{p['id']}_{rank}"
        crops = []
        for im in ims:
            pad = cv2.copyMakeBorder(im, R, R, R, R, cv2.BORDER_CONSTANT, value=(0, 0, 0))
            crops.append(cv2.resize(pad[py:py + 2 * R, px:px + 2 * R], (4 * R, 4 * R), interpolation=cv2.INTER_CUBIC))
        cv2.imwrite(f"{OUT}/c/{cid}.jpg", np.concatenate(crops, 1), [cv2.IMWRITE_JPEG_QUALITY, 85])
        ctx = ims[1].copy(); cv2.circle(ctx, (int(px), int(py)), 22, (0, 230, 255), 3)
        cv2.imwrite(f"{OUT}/x/{cid}.jpg", cv2.resize(ctx, (640, round(H * 640 / 1280))), [cv2.IMWRITE_JPEG_QUALITY, 70])
        items.append({"id": cid, "frame_id": p["id"], "game": p["game"], "video": f"{p['dataset']}/{p['file']}",
                      "frame": fr, "gap": G, "x": round(float(px), 1), "y": round(float(py), 1), "score": round(s, 3),
                      "rank": rank, "clock_running": p.get("clock_running")})
json.dump(items, open(f"{OUT}/items.json", "w"))
print("done", len(items), "crops from", len(PICKS), "frames", f"{time.time() - T0:.0f}s")
