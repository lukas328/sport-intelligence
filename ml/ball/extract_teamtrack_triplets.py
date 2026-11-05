"""TeamTrack triplet tiles (t-2, t, t+2), 192x192 each, stored side by side as one 576x192 JPEG."""
import csv,cv2,json,random,sys
from collections import deque
from pathlib import Path
root=Path(sys.argv[1]); out=Path(sys.argv[2]); T=192; G=2; random.seed(0); meta=[]
for split in ("train","val","test"):
    for ann in sorted((root/split/"annotations").glob("*.csv")):
        rows=list(csv.reader(open(ann))); ball=[i for i,v in enumerate(rows[0]) if v=="BALL"]; hdr=[rows[2][i] for i in ball]; B={}
        for k,r in enumerate(rows[4:]):
            try: v={h:float(r[i]) for h,i in zip(hdr,ball)}
            except ValueError: continue
            B[k]=(v["bb_left"]+v["bb_width"]/2,v["bb_top"]+v["bb_height"]/2,max(v["bb_width"],v["bb_height"]))
        cap=cv2.VideoCapture(str(root/split/"videos"/(ann.stem+".mp4"))); buf=deque(maxlen=2*G+1); n=-1
        while True:
            ok,f=cap.read()
            if not ok: break
            n+=1; buf.append(f)
            c=n-G
            if len(buf)<2*G+1 or c%6 or c not in B: continue
            H,W=f.shape[:2]; bx,by,bs=B[c]
            if not (0<=bx<W and 0<=by<H): continue
            def tile(x0,y0): return cv2.hconcat([buf[0][y0:y0+T,x0:x0+T],buf[G][y0:y0+T,x0:x0+T],buf[2*G][y0:y0+T,x0:x0+T]])
            x0=int(min(max(0,bx-random.randint(16,T-16)),W-T)); y0=int(min(max(0,by-random.randint(16,T-16)),H-T))
            name=f"tt_{ann.stem}_{c}_p.jpg"; cv2.imwrite(str(out/"img"/name),tile(x0,y0),[cv2.IMWRITE_JPEG_QUALITY,90])
            meta.append({"file":name,"split":split,"ball":[bx-x0,by-y0,bs],"src":"teamtrack"})
            for j in range(2):
                for _ in range(10):
                    x0=random.randint(0,W-T); y0=random.randint(0,H-T)
                    if not (x0-20<bx<x0+T+20 and y0-20<by<y0+T+20): break
                name=f"tt_{ann.stem}_{c}_n{j}.jpg"; cv2.imwrite(str(out/"img"/name),tile(x0,y0),[cv2.IMWRITE_JPEG_QUALITY,90])
                meta.append({"file":name,"split":split,"ball":None,"src":"teamtrack"})
    print(split,len(meta),flush=True)
json.dump(meta,open(out/"meta_tt.json","w"))
