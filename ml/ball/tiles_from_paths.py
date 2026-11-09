"""Training data from the labelled ball paths: every clicked keyframe and the frames between two
clicked keyframes (linear interpolation) give a triplet tile around the ball; random and hard
negatives (net peaks away from the ball) from every decided keyframe. Also saves full centre frames
of clicked keyframes for the holder classifier."""
from pathlib import Path as _P
ROOT=_P(__file__).resolve().parents[2]
import sys,json,glob,random,cv2,numpy as np,onnxruntime as ort
from pathlib import Path
DB,out,model=sys.argv[1],Path(sys.argv[2]),sys.argv[3]; R=Path(str(ROOT/"data/videos")); T=320; random.seed(5)
sess=ort.InferenceSession(model,providers=["CPUExecutionProvider"])
(out/"seqframes").mkdir(exist_ok=True)
meta=[]; frames_meta=[]
for f in sorted(glob.glob(DB+"/*.json")):
    d=json.load(open(f)); sid=Path(f).stem; m=d["marks"]; keys=d["frames"]; G=d["gap"]
    lab={}  # frame -> (x,y) or None (not visible)
    for i,k in enumerate(keys):
        if not m[i]: continue
        lab[k]=None if m[i].get("none") else (m[i]["x"],m[i]["y"])
        if i+1<len(keys) and m[i] and m[i+1] and not m[i].get("none") and not m[i+1].get("none"):
            a,b=(m[i]["x"],m[i]["y"]),(m[i+1]["x"],m[i+1]["y"])
            if np.hypot(b[0]-a[0],b[1]-a[1])<120:  # skip interpolation over big jumps
                for j in range(1,keys[i+1]-k):
                    w=j/(keys[i+1]-k); lab[k+j]=(a[0]+w*(b[0]-a[0]),a[1]+w*(b[1]-a[1]))
    if not lab: continue
    cap=cv2.VideoCapture(str(R/d["video"])); lo,hi=min(lab)-G,max(lab)+G
    cap.set(cv2.CAP_PROP_POS_FRAMES,lo); buf={}
    for n in range(lo,hi+1):
        ok,fr=cap.read()
        if not ok: break
        if fr.shape[1]!=1280: fr=cv2.resize(fr,(1280,round(fr.shape[0]*1280/fr.shape[1])),interpolation=cv2.INTER_AREA)
        buf[n]=fr
    for n,ball in lab.items():
        if n-G not in buf or n+G not in buf: continue
        ims=[buf[n-G],buf[n],buf[n+G]]; H,W=ims[0].shape[:2]; key=n in keys
        def tile(x0,y0): return cv2.hconcat([i[y0:y0+T,x0:x0+T] for i in ims])
        if ball:
            x0=int(np.clip(ball[0]-random.uniform(30,T-30),0,W-T)); y0=int(np.clip(ball[1]-random.uniform(30,T-30),0,H-T))
            fn=f"seq_{sid}_{n}_p.jpg"; cv2.imwrite(str(out/"img"/fn),tile(x0,y0),[cv2.IMWRITE_JPEG_QUALITY,92])
            meta.append({"file":fn,"split":"train","ball":[ball[0]-x0,ball[1]-y0,12],"src":"seq_"+d["hall"],"tile":T,"interp":not key})
        if not key: continue
        if ball: cv2.imwrite(str(out/"seqframes"/f"{sid}_{n}.jpg"),cv2.hconcat(ims),[cv2.IMWRITE_JPEG_QUALITY,90]); frames_meta.append({"id":f"{sid}_{n}","hall":d["hall"],"x":ball[0],"y":ball[1],"w":W})
        for j in range(2):
            for _ in range(20):
                x0=random.randint(0,W-T); y0=random.randint(0,H-T)
                if not ball or not (x0-20<ball[0]<x0+T+20 and y0-20<ball[1]<y0+T+20): break
            else: continue
            fn=f"seq_{sid}_{n}_n{j}.jpg"; cv2.imwrite(str(out/"img"/fn),tile(x0,y0),[cv2.IMWRITE_JPEG_QUALITY,92])
            meta.append({"file":fn,"split":"train","ball":None,"src":"seq_"+d["hall"],"tile":T})
        h2=H//32*32
        x=np.concatenate([cv2.cvtColor(i[:h2],cv2.COLOR_BGR2RGB) for i in ims],2).transpose(2,0,1)[None].astype(np.float32)
        hm=1/(1+np.exp(-sess.run(None,{"x":x})[0][0,0]))
        for j in range(4):
            yx=np.unravel_index(hm.argmax(),hm.shape); sc=float(hm[yx]); cx,cy=yx[1]*4+2,yx[0]*4+2
            hm[max(0,yx[0]-8):yx[0]+8,max(0,yx[1]-8):yx[1]+8]=0
            if sc<0.08: break
            if ball and np.hypot(cx-ball[0],cy-ball[1])<40: continue
            x0=int(np.clip(cx-T//2,0,W-T)); y0=int(np.clip(cy-T//2,0,H-T))
            if ball and x0<ball[0]<x0+T and y0<ball[1]<y0+T: continue
            fn=f"seq_{sid}_{n}_h{j}.jpg"; cv2.imwrite(str(out/"img"/fn),tile(x0,y0),[cv2.IMWRITE_JPEG_QUALITY,92])
            meta.append({"file":fn,"split":"train","ball":None,"src":"seq_"+d["hall"],"hard":True,"tile":T})
    print(sid,len(meta),flush=True)
json.dump(meta,open(out/"meta_seq.json","w")); json.dump(frames_meta,open(out/"seqframes.json","w"))
from collections import Counter; print(Counter((m["ball"] is not None,bool(m.get("hard")),bool(m.get("interp"))) for m in meta))
