"""Self-training on the GPU: the ball net over every frame of the game segments, peaks linked over
time (balltrack), fixed spots and spots glued to the background dropped; long moving tracklets are
saved as triplet tiles with a review strip per segment."""
import glob,json,os,time,math,bisect,itertools
from collections import defaultdict
from dataclasses import dataclass, field
import cv2,numpy as np,torch,torch.nn as nn,torch.nn.functional as F,torchvision





@dataclass(frozen=True)
class Peak:
    frame: int
    x: float
    y: float
    score: float


@dataclass
class Tracklet:
    peaks: list[Peak] = field(default_factory=list)
    vx: float = 0.0
    vy: float = 0.0
    value: float = 0.0

    @property
    def first(self) -> int:
        return self.peaks[0].frame

    @property
    def last(self) -> int:
        return self.peaks[-1].frame


@dataclass(frozen=True)
class BallPoint:
    frame: int
    x: float
    y: float
    score: float  # 0 for interpolated points
    tracklet: int


def _logit(p: float) -> float:
    p = min(max(p, 1e-4), 1 - 1e-4)
    return math.log(p / (1 - p))


def static_cells(
    peaks: list[Peak], fps: float, cell: float, min_share: float = 0.15, min_seconds: int = 8
) -> set[tuple[int, int]]:
    """Grid cells (size `cell`) holding peaks in at least `min_share` of the seconds with peaks
    (and at least `min_seconds` of them): fixed things in the hall."""
    seconds: dict[tuple[int, int], set[int]] = defaultdict(set)
    all_seconds: set[int] = set()
    for p in peaks:
        s = int(p.frame / fps)
        all_seconds.add(s)
        seconds[(int(p.x // cell), int(p.y // cell))].add(s)
    if not all_seconds:
        return set()
    need = max(min_seconds, min_share * len(all_seconds))
    # a spot on a cell border spreads over two cells: count the 2x2 neighbourhood
    out = set()
    for c in seconds:
        near: set[int] = set()
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                near |= seconds.get((c[0] + dx, c[1] + dy), set())
        if len(seconds[c]) >= need / 2 and len(near) >= need:
            out.add(c)
    return out


def link(
    peaks: list[Peak],
    fps: float,
    max_speed: float,
    radius: float,
    max_gap: int = 3,
) -> list[Tracklet]:
    """Tracklets from peaks: each peak joins the open tracklet whose constant-velocity prediction
    is nearest (within `radius` + half the maximal step, and a step no longer than `max_speed`
    allows), stronger peaks first; a tracklet closes after `max_gap` frames without a peak."""
    by_frame: dict[int, list[Peak]] = defaultdict(list)
    for p in peaks:
        by_frame[p.frame].append(p)
    done: list[Tracklet] = []
    open_: list[Tracklet] = []
    for f in sorted(by_frame):
        still: list[Tracklet] = []
        for t in open_:
            (done if f - t.last > max_gap else still).append(t)
        open_ = still
        taken: set[int] = set()
        for p in sorted(by_frame[f], key=lambda q: -q.score):
            best, best_d = None, math.inf
            for k, t in enumerate(open_):
                if k in taken:
                    continue
                last = t.peaks[-1]
                dt = (f - last.frame) / fps
                step = math.hypot(p.x - last.x, p.y - last.y)
                if step > radius + max_speed * dt:
                    continue
                d = math.hypot(p.x - (last.x + t.vx * dt), p.y - (last.y + t.vy * dt))
                if d <= radius + 0.5 * max_speed * dt and d < best_d:
                    best, best_d = k, d
            if best is None:
                open_.append(Tracklet([p]))
                taken.add(len(open_) - 1)
                continue
            t = open_[best]
            last = t.peaks[-1]
            dt = (f - last.frame) / fps
            vx, vy = (p.x - last.x) / dt, (p.y - last.y) / dt
            a = 0.5 if len(t.peaks) > 1 else 1.0  # smoothed velocity
            t.vx, t.vy = (1 - a) * t.vx + a * vx, (1 - a) * t.vy + a * vy
            t.peaks.append(p)
            taken.add(best)
    return done + open_


def track(
    peaks: list[Peak],
    fps: float,
    max_speed: float,
    radius: float,
    min_score: float = 0.3,
    max_gap: int = 3,
    min_length: int = 3,
    static_cell: float | None = None,
    static_after_s: float = 1.5,
    free_after_s: float = 2.0,
) -> tuple[list[BallPoint], dict[str, int]]:
    """The ball path: chosen tracklets' peaks plus linear interpolation over their short gaps."""
    cell = static_cell if static_cell is not None else 2 * radius
    static = static_cells(peaks, fps, cell)
    kept = [p for p in peaks if (int(p.x // cell), int(p.y // cell)) not in static]
    tracklets = link(kept, fps, max_speed, radius, max_gap)
    bias = _logit(min_score)
    good: list[Tracklet] = []
    n_static = n_short = 0
    for t in tracklets:
        if len(t.peaks) < min_length:
            n_short += 1
            continue
        if (t.last - t.first) / fps >= static_after_s:
            xs = sorted(p.x for p in t.peaks)
            ys = sorted(p.y for p in t.peaks)
            spread = max(xs[-1] - xs[0], ys[-1] - ys[0])
            if spread < radius:
                n_static += 1
                continue
        t.value = sum(_logit(p.score) - bias for p in t.peaks)
        if t.value > 0:
            good.append(t)
    good.sort(key=lambda t: t.last)
    ends = [t.last for t in good]
    best = [0.0] * len(good)
    prev: list[int | None] = [None] * len(good)
    prefix: list[tuple[float, int | None]] = []  # running max of best[] by end frame
    free_gap = int(free_after_s * fps)
    for j, t in enumerate(good):
        candidate, came = 0.0, None
        # anything that ended long enough before is reachable: running maximum
        k = bisect.bisect_left(ends, t.first - free_gap) - 1
        if k >= 0 and prefix[k][0] > candidate:
            candidate, came = prefix[k]
        # recent ones must be reachable at ball speed
        i = bisect.bisect_left(ends, t.first) - 1
        while i > k:
            a = good[i]
            gap_s = (t.first - a.last) / fps
            pa, pb = a.peaks[-1], t.peaks[0]
            reach = math.hypot(pb.x - pa.x, pb.y - pa.y) <= radius + max_speed * gap_s
            if reach and best[i] > candidate:
                candidate, came = best[i], i
            i -= 1
        best[j] = t.value + candidate
        prev[j] = came
        top = prefix[-1] if prefix else (0.0, None)
        prefix.append((best[j], j) if best[j] > top[0] else top)
    chain: list[int] = []
    at: int | None = max(range(len(good)), key=lambda q: best[q]) if good else None
    while at is not None:
        chain.append(at)
        at = prev[at]
    out: list[BallPoint] = []
    for n, j in enumerate(reversed(chain)):
        ps = good[j].peaks
        for p0, p1 in itertools.pairwise(ps):
            out.append(BallPoint(p0.frame, p0.x, p0.y, p0.score, n))
            for f in range(p0.frame + 1, p1.frame):
                w = (f - p0.frame) / (p1.frame - p0.frame)
                out.append(BallPoint(f, p0.x + w * (p1.x - p0.x), p0.y + w * (p1.y - p0.y), 0.0, n))
        out.append(BallPoint(ps[-1].frame, ps[-1].x, ps[-1].y, ps[-1].score, n))
    stats = {
        "peaks": len(peaks),
        "static_cells": len(static),
        "tracklets": len(tracklets),
        "short": n_short,
        "static_tracklets": n_static,
        "chosen": len(chain),
        "frames_with_ball": sum(1 for p in out if p.score > 0),
    }
    return out, stats

class BallNet3(nn.Module):
    def __init__(s):
        super().__init__()
        r=torchvision.models.resnet18(weights=None)
        c1=nn.Conv2d(9,64,7,2,3,bias=False)
        s.stem=nn.Sequential(c1,r.bn1,r.relu,r.maxpool); s.l1=r.layer1; s.l2=r.layer2
        s.up=nn.Sequential(nn.Conv2d(128,64,3,padding=1),nn.BatchNorm2d(64),nn.ReLU())
        s.head=nn.Sequential(nn.Conv2d(128,64,3,padding=1),nn.BatchNorm2d(64),nn.ReLU(),nn.Conv2d(64,1,1))
        s.register_buffer("mean",torch.tensor([0.485,0.456,0.406]*3).view(1,9,1,1)*255); s.register_buffer("std",torch.tensor([0.229,0.224,0.225]*3).view(1,9,1,1)*255)
    def forward(s,x):  # N,9,H,W RGB 0..255 (prev, centre, next) -> N,1,H/4,W/4 logits
        x=(x-s.mean)/s.std; a=s.l1(s.stem(x)); b=s.l2(a)
        b=F.interpolate(s.up(b),size=a.shape[-2:],mode="bilinear",align_corners=False)
        return s.head(torch.cat([a,b],1))
def local_motion(trip,cx,cy,r=64,q=8):
    # how much the spot moves relative to its own surroundings (0: glued to the background)
    H,W=trip[0].shape[:2]; x0=int(np.clip(cx-r,0,W-2*r)); y0=int(np.clip(cy-r,0,H-2*r))
    g=[cv2.cvtColor(t[y0:y0+2*r,x0:x0+2*r],cv2.COLOR_BGR2GRAY).astype(np.float32) for t in trip]
    px,py=int(cx-x0),int(cy-y0); c=g[1][max(0,py-q):py+q,max(0,px-q):px+q]
    if c.size==0: return 0.0
    contrast=float(c.std())+4.0; out=[]
    for o in (g[0],g[2]):
        (dx,dy),_=cv2.phaseCorrelate(g[1],o)
        M=np.float32([[1,0,-dx],[0,1,-dy]]); al=cv2.warpAffine(o,M,(2*r,2*r),borderMode=cv2.BORDER_REPLICATE)
        a=al[max(0,py-q):py+q,max(0,px-q):px+q]; out.append(float(np.abs(a-c).mean())/contrast)
    return min(out)

dev="cuda" if torch.cuda.is_available() else "cpu"; print("device",dev,flush=True)
W_ = glob.glob("/kaggle/input/**/ball_best.pt",recursive=True)[0]
model=BallNet3(); model.load_state_dict(torch.load(W_,map_location="cpu",weights_only=True)); model.eval().to(dev)
OUT="/kaggle/working/mined"; os.makedirs(OUT,exist_ok=True); T=192; MOVE=0.25
def run(path):
    name=os.path.basename(path)[:-4]; cap=cv2.VideoCapture(path); fps=cap.get(cv2.CAP_PROP_FPS) or 30; G=3 if fps>40 else 2
    frames=[]; ok=True
    while ok:
        ok,f=cap.read()
        if ok:
            if f.shape[1]!=1280: f=cv2.resize(f,(1280,round(f.shape[0]*1280/f.shape[1])),interpolation=cv2.INTER_AREA)
            frames.append(f)
    H,Wd=frames[0].shape[:2]; h2,w2=H//32*32,Wd//32*32
    offs=[np.zeros(2)]; prev=None; off=np.zeros(2)
    for f in frames:
        g=cv2.cvtColor(cv2.resize(f,None,fx=0.25,fy=0.25),cv2.COLOR_BGR2GRAY).astype(np.float32)
        if prev is not None:
            (dx,dy),_=cv2.phaseCorrelate(prev,g); off=off+np.array([dx,dy])*4
        prev=g; offs.append(off.copy())
    offs=offs[1:]
    peaks=[]; motion={}; tiles={}
    idx=list(range(G,len(frames)-G)); B=16
    for k in range(0,len(idx),B):
        cs=idx[k:k+B]
        x=np.stack([np.concatenate([cv2.cvtColor(frames[c+d][:h2,:w2],cv2.COLOR_BGR2RGB) for d in (-G,0,G)],2) for c in cs]).transpose(0,3,1,2)
        with torch.no_grad(): hm=torch.sigmoid(model(torch.from_numpy(x).float().to(dev)))[:,0].cpu().numpy()
        for c,h in zip(cs,hm):
            for _ in range(4):
                yx=np.unravel_index(h.argmax(),h.shape)
                if h[yx]<0.08: break
                px,py=yx[1]*4+2,yx[0]*4+2; trip=(frames[c-G],frames[c],frames[c+G])
                p=Peak(c,float(px+offs[c][0]),float(py+offs[c][1]),float(h[yx])); peaks.append(p)
                motion[(c,p.x,p.y)]=local_motion(trip,px,py)
                x0=int(np.clip(px-96,0,w2-T)); y0=int(np.clip(py-96,0,h2-T))
                tiles[(c,p.x,p.y)]=(cv2.imencode(".jpg",cv2.hconcat([t[y0:y0+T,x0:x0+T] for t in trip]),[cv2.IMWRITE_JPEG_QUALITY,90])[1],px-x0,py-y0)
                h[max(0,yx[0]-6):yx[0]+6,max(0,yx[1]-6):yx[1]+6]=0
    static=static_cells(peaks,fps,w2/80); kept=[p for p in peaks if (int(p.x//(w2/80)),int(p.y//(w2/80))) not in static]
    trs=link(kept,fps,max_speed=w2*0.9,radius=w2/160,max_gap=2); sel=[]
    for t in trs:
        if len(t.peaks)<6: continue
        xs=[p.x for p in t.peaks]; ys=[p.y for p in t.peaks]
        if max(max(xs)-min(xs),max(ys)-min(ys))<w2/60: continue
        if np.mean([p.score for p in t.peaks])<0.15: continue
        if np.median([motion[(p.frame,p.x,p.y)] for p in t.peaks])<MOVE: continue
        sel.append(t)
    items=[]
    for j,t in enumerate(sel):
        for p in t.peaks:
            jpg,bx,by=tiles[(p.frame,p.x,p.y)]; fn=f"mine_{name}_{p.frame}_{j}.jpg"; open(f"{OUT}/{fn}","wb").write(jpg.tobytes())
            items.append({"file":fn,"tracklet":f"{name}_{j}","ball_in_tile":[int(bx),int(by)],"score":p.score,"vid":name,"frame":p.frame,"motion":round(float(motion[(p.frame,p.x,p.y)]),3)})
    json.dump(items,open(f"/kaggle/working/mined_{name}.json","w"))
    print(name,"frames",len(frames),"peaks",len(peaks),"tracklets",len(trs),"selected",len(sel),"tiles",len(items),flush=True)
t0=time.time()
for v in sorted(glob.glob("/kaggle/input/**/*.mp4",recursive=True)):
    try: run(v)
    except Exception as e: print("failed",v,e,flush=True)
    print("elapsed",round(time.time()-t0),flush=True)
