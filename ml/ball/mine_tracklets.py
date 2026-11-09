"""Self-training with time: run the 3-frame net on a video piece, link peaks over frames, keep long
moving tracklets as ball candidates. Saves every peak of such a tracklet as a triplet tile (to label
the whole tracklet with one look) and a review strip per tracklet.
usage: mine3.py model.onnx video start_s dur_s name out_dir [width] [threads]"""
from pathlib import Path as _P
ROOT=_P(__file__).resolve().parents[2]
import sys,json,time,cv2,numpy as np,onnxruntime as ort
from collections import deque
from pathlib import Path
sys.path.insert(0,str(ROOT/"packages/vision"))
from handball_vision import balltrack as bt
model,video,start,dur,name,out=sys.argv[1],sys.argv[2],float(sys.argv[3]),float(sys.argv[4]),sys.argv[5],Path(sys.argv[6])
MOVE=float(sys.argv[9]) if len(sys.argv)>9 else 0.5
WMAX=int(sys.argv[7]) if len(sys.argv)>7 else 1280
so=ort.SessionOptions(); so.intra_op_num_threads=int(sys.argv[8]) if len(sys.argv)>8 else 1
s=ort.InferenceSession(model,so,providers=["CPUExecutionProvider"])
cap=cv2.VideoCapture(video); fps=cap.get(cv2.CAP_PROP_FPS); G=3 if fps>40 else 2; T=192
cap.set(cv2.CAP_PROP_POS_MSEC,start*1000); N=int(dur*fps)
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
motion={}; tiles={}
buf=deque(maxlen=2*G+1); keep={}; offs=[]; peaks=[]; off=np.zeros(2); prev=None; t0=time.time()
for k in range(N+G):
    ok,f=cap.read()
    if not ok: break
    if f.shape[1]>WMAX: f=cv2.resize(f,(WMAX,round(f.shape[0]*WMAX/f.shape[1])))
    g=cv2.cvtColor(cv2.resize(f,None,fx=0.25,fy=0.25),cv2.COLOR_BGR2GRAY).astype(np.float32)
    if prev is not None:
        (dx,dy),_=cv2.phaseCorrelate(prev,g); off=off+np.array([dx,dy])*4
    prev=g; offs.append(off.copy()); buf.append(f)
    if len(buf)<2*G+1: continue
    c=k-G; H,W=f.shape[:2]; h2,w2=H//32*32,W//32*32
    keep[c]=(buf[0],buf[G],buf[2*G])
    for old in [q for q in keep if q<c]: del keep[old]
    x=np.concatenate([cv2.cvtColor(b[:h2,:w2],cv2.COLOR_BGR2RGB) for b in keep[c]],2).transpose(2,0,1)[None].astype(np.float32)
    hm=1/(1+np.exp(-s.run(None,{"x":x})[0][0,0]))
    for _ in range(4):
        yx=np.unravel_index(hm.argmax(),hm.shape)
        if hm[yx]<0.12: break
        px,py=yx[1]*4+2,yx[0]*4+2
        peaks.append(bt.Peak(c,float(px+offs[c][0]),float(py+offs[c][1]),float(hm[yx])))
        motion[(c,peaks[-1].x,peaks[-1].y)]=local_motion(keep[c],px,py)
        x0=int(np.clip(px-96,0,w2-T)); y0=int(np.clip(py-96,0,h2-T))
        tile=cv2.hconcat([b[y0:y0+T,x0:x0+T] for b in keep[c]])
        tiles[(c,peaks[-1].x,peaks[-1].y)]=(cv2.imencode(".jpg",tile,[cv2.IMWRITE_JPEG_QUALITY,90])[1],px-x0,py-y0)
        hm[max(0,yx[0]-6):yx[0]+6,max(0,yx[1]-6):yx[1]+6]=0
    if c%300==0: print(name,c,len(peaks),f"{time.time()-t0:.0f}s",flush=True)
W=w2; static=bt.static_cells(peaks,fps,W/80)
kept=[p for p in peaks if (int(p.x//(W/80)),int(p.y//(W/80))) not in static]
trs=bt.link(kept,fps,max_speed=W*0.9,radius=W/160,max_gap=2)
sel=[]
for t in trs:
    if len(t.peaks)<6: continue
    xs=[p.x for p in t.peaks]; ys=[p.y for p in t.peaks]
    if max(max(xs)-min(xs),max(ys)-min(ys))<W/60: continue  # does not move
    if np.mean([p.score for p in t.peaks])<0.2: continue
    if np.median([motion[(p.frame,p.x,p.y)] for p in t.peaks])<MOVE: continue  # glued to the background
    sel.append(t)
items=[]
for j,t in enumerate(sel):
    for p in t.peaks:
        jpg,bx,by=tiles[(p.frame,p.x,p.y)]
        fn=f"mine_{name}_{p.frame}_{j}.jpg"; (out/"cand"/fn).write_bytes(jpg.tobytes()); cx,cy=bx,by; x0=y0=0
        items.append({"motion":round(motion[(p.frame,p.x,p.y)],3),"file":fn,"tracklet":f"{name}_{j}","ball_in_tile":[cx-x0,cy-y0],"score":p.score,"vid":name,"frame":p.frame})
json.dump(items,open(out/f"mined_{name}.json","w"),default=float); json.dump([[p.frame,p.x,p.y,p.score,motion[(p.frame,p.x,p.y)]] for p in peaks],open(out/f"peaks_{name}.json","w"),default=float)
print(name,"peaks",len(peaks),"static cells",len(static),"tracklets",len(trs),"selected",len(sel),"tiles",len(items),f"{time.time()-t0:.0f}s",flush=True)
