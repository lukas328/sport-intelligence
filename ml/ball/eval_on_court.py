"""Ball net restricted to the court (+2 m, plus the space up to ~4 m above the far side); collects
off-court peaks as automatic hard negatives."""
import sys,json,pickle,cv2,numpy as np,onnxruntime as ort
from pathlib import Path
from handball_vision.motion import CameraMotion
from handball_vision.calibration import Calibration
model,vid,video,out=sys.argv[1:5]; thr=float(sys.argv[5]) if len(sys.argv)>5 else 0.3
negdir=Path(sys.argv[6]) if len(sys.argv)>6 else None
V=Path("/home/user/handball-ai/data/views"); mo=CameraMotion.load(V/f"{vid}-motion2.npz")
cal=Calibration.from_dict(pickle.load(open(f"/tmp/claude-0/-home-user/3dc450e2-2499-5e21-b252-1c4e366c6b5a/scratchpad/exp/{vid}-cal.pkl","rb")))
so=ort.SessionOptions(); so.intra_op_num_threads=2; s=ort.InferenceSession(model,so,providers=["CPUExecutionProvider"])
def court_mask(n,shape):
    hc=mo.frame_to_canvas(n)
    if hc is None: return None
    H=np.linalg.inv(hc)@cal.homography
    poly=cv2.perspectiveTransform(np.array([[[-2,-2],[42,-2],[42,22],[-2,22]]],np.float64),H)[0]
    m=np.zeros(shape,np.uint8); cv2.fillPoly(m,[poly.astype(np.int32)],1)
    # up to ~4 m above the far touchline: the image height of 4 m there ~ 2.2 x the 1.85 m player height
    far=cv2.perspectiveTransform(np.array([[[0,22],[40,22]]],np.float64),H)[0]
    near=cv2.perspectiveTransform(np.array([[[0,21],[40,21]]],np.float64),H)[0]
    up=int(np.clip(np.linalg.norm(far[1]-far[0])/40*1.85*2.2,20,shape[0]/3))
    ys=np.nonzero(m.any(axis=1))[0]
    if len(ys): m[max(0,ys[0]-up):ys[0]]=m[ys[0]]
    return m.astype(bool)
cap=cv2.VideoCapture(video); fps=cap.get(cv2.CAP_PROP_FPS); n=0; dets=[]; negs=0; cands=[]
if negdir is not None: (negdir.parent/"cand").mkdir(exist_ok=True)
while True:
    ok,f=cap.read()
    if not ok: break
    if n%int(fps)==0:
        Hh,W=f.shape[:2]; h2,w2=Hh//32*32,W//32*32
        hm=1/(1+np.exp(-s.run(None,{"x":cv2.cvtColor(f[:h2,:w2],cv2.COLOR_BGR2RGB).transpose(2,0,1)[None].astype(np.float32)})[0][0,0]))
        cm=court_mask(n,(Hh,W))
        if cm is not None:
            cm4=cv2.resize(cm.astype(np.uint8)[:h2,:w2],(hm.shape[1],hm.shape[0]),interpolation=cv2.INTER_NEAREST).astype(bool)
            if negdir is not None:  # strongest off-court peaks: certainly not the ball
                off=np.where(cm4,0,hm); 
                for _ in range(3):
                    yx=np.unravel_index(off.argmax(),off.shape)
                    if off[yx]<0.3: break
                    cx,cy=int(yx[1]*4+2),int(yx[0]*4+2); x0=int(np.clip(cx-96,0,W-192)); y0=int(np.clip(cy-96,0,Hh-192))
                    cv2.imwrite(str(negdir/f"hn_{vid}_{n}_{negs}.jpg"),f[y0:y0+192,x0:x0+192],[cv2.IMWRITE_JPEG_QUALITY,92]); negs+=1
                    off[max(0,yx[0]-12):yx[0]+12,max(0,yx[1]-12):yx[1]+12]=0
            hm=np.where(cm4,hm,0)
        if negdir is not None:
            on=hm.copy()
            for _ in range(2):
                yx2=np.unravel_index(on.argmax(),on.shape)
                if on[yx2]<0.25: break
                cx2,cy2=int(yx2[1]*4+2),int(yx2[0]*4+2); x0=int(np.clip(cx2-96,0,W-192)); y0=int(np.clip(cy2-96,0,Hh-192))
                fn=f"cand_{vid}_{n}_{len(cands)}.jpg"; cv2.imwrite(str(negdir.parent/"cand"/fn),f[y0:y0+192,x0:x0+192],[cv2.IMWRITE_JPEG_QUALITY,92])
                cands.append({"file":fn,"score":float(on[yx2]),"ball_in_tile":[cx2-x0,cy2-y0],"vid":vid,"frame":n})
                on[max(0,yx2[0]-12):yx2[0]+12,max(0,yx2[1]-12):yx2[1]+12]=0
        yx=np.unravel_index(hm.argmax(),hm.shape); sc=float(hm.max())
        cx,cy=int(yx[1]*4+2),int(yx[0]*4+2); r=24; c=np.zeros((48,48,3),np.uint8); p=f[max(0,cy-r):cy+r,max(0,cx-r):cx+r]; c[:p.shape[0],:p.shape[1]]=p
        dets.append((sc,n,cx,cy,c))
    n+=1
if negdir is not None: json.dump(cands,open(negdir.parent/f"cands_{vid}.json","w"))
sc=np.array([d[0] for d in dets]); print(vid,"frames",len(dets),"court peak>=",thr,round(float((sc>=thr).mean()),2),"| >=0.5",round(float((sc>=0.5).mean()),2),"| hard negatives",negs)
sel=sorted([d for d in dets if d[0]>=thr],key=lambda d:-d[0]); sel=sel[::max(1,len(sel)//60)][:60]
tiles=[]
for sc_,n_,cx,cy,c in sel:
    t=np.full((116,96,3),255,np.uint8); t[:96]=cv2.resize(c,(96,96),interpolation=cv2.INTER_NEAREST); cv2.circle(t,(48,48),10,(0,0,255),1)
    cv2.putText(t,f"{sc_:.2f} {n_/fps:.0f}s",(2,111),cv2.FONT_HERSHEY_SIMPLEX,0.35,(0,0,200),1); tiles.append(t)
while len(tiles)%12: tiles.append(np.full((116,96,3),255,np.uint8))
if tiles: cv2.imwrite(out,np.vstack([np.hstack(tiles[i:i+12]) for i in range(0,len(tiles),12)]))
