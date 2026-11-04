"""Training tiles from the user's labels: train half per hall (test half kept for the benchmark).
Ball frames -> 4 triplet tiles of 320 px around the ball (random offsets); every frame -> 4 random
negatives away from the ball, plus the net's wrong peaks as hard negatives."""
import sys,json,glob,random,cv2,numpy as np,onnxruntime as ort
P,out,model=sys.argv[1],sys.argv[2],sys.argv[3]; random.seed(3); T=320
L=sorted([json.load(open(f))|{"id":f.split("/")[-1][:-5]} for f in glob.glob(P+"/db2/labels/*.json")],key=lambda l:l["id"])
L=[l for l in L if l["state"]!="unsure"]
by={}
for l in L: by.setdefault(l["hall"],[]).append(l)
split={}
for h,ls in by.items():
    for k,l in enumerate(ls): split[l["id"]]="test" if k%2 else "train"
json.dump(split,open(out+"/user_split.json","w"))
s=ort.InferenceSession(model,providers=["CPUExecutionProvider"])
meta=[]
def tile(ims,x0,y0): return cv2.hconcat([i[y0:y0+T,x0:x0+T] for i in ims])
for l in L:
    if split[l["id"]]!="train": continue
    t=cv2.imread(f"{P}/t/{l['id']}.jpg"); W=l["w"]; H=t.shape[0]; ims=[t[:,k*W:(k+1)*W] for k in range(3)]
    ball=(l["x"],l["y"]) if l["state"]=="ball" else None
    if ball:
        for j in range(4):
            x0=int(np.clip(ball[0]-random.uniform(30,T-30),0,W-T)); y0=int(np.clip(ball[1]-random.uniform(30,T-30),0,H-T))
            fn=f"usr_{l['id']}_p{j}.jpg"; cv2.imwrite(f"{out}/img/{fn}",tile(ims,x0,y0),[cv2.IMWRITE_JPEG_QUALITY,92])
            meta.append({"file":fn,"split":"train","ball":[ball[0]-x0,ball[1]-y0,12],"src":"user_"+l["hall"],"tile":T})
    def far(cx,cy): return ball is None or np.hypot(cx-ball[0],cy-ball[1])>40
    n=0
    for _ in range(40):
        if n>=4: break
        x0=random.randint(0,W-T); y0=random.randint(0,H-T)
        if ball and x0-20<ball[0]<x0+T+20 and y0-20<ball[1]<y0+T+20: continue
        fn=f"usr_{l['id']}_n{n}.jpg"; cv2.imwrite(f"{out}/img/{fn}",tile(ims,x0,y0),[cv2.IMWRITE_JPEG_QUALITY,92]); n+=1
        meta.append({"file":fn,"split":"train","ball":None,"src":"user_"+l["hall"],"tile":T})
    h2,w2=H//32*32,W//32*32
    x=np.concatenate([cv2.cvtColor(i[:h2,:w2],cv2.COLOR_BGR2RGB) for i in ims],2).transpose(2,0,1)[None].astype(np.float32)
    hm=1/(1+np.exp(-s.run(None,{"x":x})[0][0,0]))
    for j in range(5):
        yx=np.unravel_index(hm.argmax(),hm.shape); sc=float(hm[yx]); cx,cy=yx[1]*4+2,yx[0]*4+2
        hm[max(0,yx[0]-8):yx[0]+8,max(0,yx[1]-8):yx[1]+8]=0
        if sc<0.08: break
        if not far(cx,cy): continue
        x0=int(np.clip(cx-T//2,0,W-T)); y0=int(np.clip(cy-T//2,0,H-T))
        if ball and x0<ball[0]<x0+T and y0<ball[1]<y0+T: continue  # tile would contain the ball
        fn=f"usr_{l['id']}_h{j}.jpg"; cv2.imwrite(f"{out}/img/{fn}",tile(ims,x0,y0),[cv2.IMWRITE_JPEG_QUALITY,92])
        meta.append({"file":fn,"split":"train","ball":None,"src":"user_"+l["hall"],"hard":True,"tile":T})
json.dump(meta,open(out+"/meta_user.json","w"))
from collections import Counter; print(Counter((m["ball"] is not None, bool(m.get("hard"))) for m in meta))
