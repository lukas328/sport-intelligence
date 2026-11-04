"""3-frame ball net on a video piece + temporal path (balltrack). Writes peaks, path and an overlay video.
usage: eval3.py model.onnx video.mp4 start_s dur_s out_prefix [threads]"""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
import sys,json,time,cv2,numpy as np,onnxruntime as ort
from collections import deque
sys.path.insert(0,str(ROOT/"packages/vision"))
from handball_vision import balltrack as bt
model,video,start,dur,out=sys.argv[1],sys.argv[2],float(sys.argv[3]),float(sys.argv[4]),sys.argv[5]
so=ort.SessionOptions(); so.intra_op_num_threads=int(sys.argv[6]) if len(sys.argv)>6 else 2
s=ort.InferenceSession(model,so,providers=["CPUExecutionProvider"])
cap=cv2.VideoCapture(video); fps=cap.get(cv2.CAP_PROP_FPS); G=3 if fps>40 else 2
cap.set(cv2.CAP_PROP_POS_MSEC,start*1000); N=int(dur*fps)
buf=deque(maxlen=2*G+1); gbuf=deque(maxlen=2*G+1); offs=[]; peaks=[]; frames={}; off=np.zeros(2); prev=None; t0=time.time()
for k in range(N+G):
    ok,f=cap.read()
    if not ok: break
    if f.shape[1]>1920: f=cv2.resize(f,(1920,round(f.shape[0]*1920/f.shape[1])))
    g=cv2.cvtColor(cv2.resize(f,None,fx=0.25,fy=0.25),cv2.COLOR_BGR2GRAY).astype(np.float32)
    if prev is not None:
        (dx,dy),_=cv2.phaseCorrelate(prev,g); off=off+np.array([dx,dy])*4  # camera pan in px
    prev=g; offs.append(off.copy()); buf.append(f)
    if len(buf)<2*G+1: continue
    c=k-G; H,W=f.shape[:2]; h2,w2=H//32*32,W//32*32
    x=np.concatenate([cv2.cvtColor(b[:h2,:w2],cv2.COLOR_BGR2RGB) for b in (buf[0],buf[G],buf[2*G])],2).transpose(2,0,1)[None].astype(np.float32)
    hm=1/(1+np.exp(-s.run(None,{"x":x})[0][0,0]))
    for _ in range(5):
        yx=np.unravel_index(hm.argmax(),hm.shape)
        if hm[yx]<0.2: break
        px,py=yx[1]*4+2,yx[0]*4+2
        peaks.append(bt.Peak(c,float(px+offs[c][0]),float(py+offs[c][1]),float(hm[yx])))  # canvas coords
        hm[max(0,yx[0]-6):yx[0]+6,max(0,yx[1]-6):yx[1]+6]=0
    frames[c]=buf[G]
    if c%100==0: print(c,len(peaks),f"{time.time()-t0:.0f}s",flush=True)
Wd=frames[next(iter(frames))].shape[1]
path,stats=bt.track(peaks,fps,max_speed=Wd*0.9,radius=Wd/160,min_score=0.35)
print(stats,flush=True)
json.dump({"fps":fps,"offs":[o.tolist() for o in offs],"peaks":[p.__dict__ for p in peaks],"path":[p.__dict__ for p in path],"stats":stats},open(out+".json","w"))
vw=cv2.VideoWriter(out+".mp4",cv2.VideoWriter_fourcc(*"mp4v"),fps/2,(960,round(960*frames[next(iter(frames))].shape[0]/Wd)))
pp={p.frame:p for p in path}; pk={}
for p in peaks: pk.setdefault(p.frame,[]).append(p)
for c,f in sorted(frames.items()):
    im=f.copy(); o=offs[c]
    for p in pk.get(c,[]): cv2.circle(im,(int(p.x-o[0]),int(p.y-o[1])),10,(0,200,255),1)
    if c in pp: q=pp[c]; cv2.circle(im,(int(q.x-o[0]),int(q.y-o[1])),16,(0,0,255) if q.score>0 else (255,0,255),3)
    vw.write(cv2.resize(im,(960,round(960*im.shape[0]/im.shape[1]))))
vw.release(); print("done",out,flush=True)
