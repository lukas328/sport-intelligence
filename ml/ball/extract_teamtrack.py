"""TeamTrack handball tiles: 192x192 at native resolution, ball tiles with the ball centre, plus
negatives away from the ball. Every 6th frame."""
import csv,cv2,json,random,sys
from pathlib import Path
root=Path(sys.argv[1]); out=Path(sys.argv[2]); (out/"img").mkdir(parents=True,exist_ok=True)
T=192; random.seed(0); meta=[]
for split in ("train","val","test"):
    for ann in sorted((root/split/"annotations").glob("*.csv")):
        rows=list(csv.reader(open(ann))); ball=[i for i,v in enumerate(rows[0]) if v=="BALL"]; hdr=[rows[2][i] for i in ball]
        B={}
        for k,r in enumerate(rows[4:]):
            try: v={h:float(r[i]) for h,i in zip(hdr,ball)}
            except ValueError: continue
            B[k]=(v["bb_left"]+v["bb_width"]/2,v["bb_top"]+v["bb_height"]/2,max(v["bb_width"],v["bb_height"]))
        cap=cv2.VideoCapture(str(root/split/"videos"/(ann.stem+".mp4"))); n=0
        while True:
            ok,f=cap.read()
            if not ok: break
            if n%6==0 and n in B:
                H,W=f.shape[:2]; bx,by,bs=B[n]
                if 0<=bx<W and 0<=by<H:
                    x0=int(min(max(0,bx-random.randint(16,T-16)),W-T)); y0=int(min(max(0,by-random.randint(16,T-16)),H-T))
                    name=f"tt_{ann.stem}_{n}_p.jpg"; cv2.imwrite(str(out/"img"/name),f[y0:y0+T,x0:x0+T],[cv2.IMWRITE_JPEG_QUALITY,92])
                    meta.append({"file":name,"split":split,"ball":[bx-x0,by-y0,bs],"src":"teamtrack"})
                    for _ in range(2):
                        for _try in range(10):
                            x0=random.randint(0,W-T); y0=random.randint(0,H-T)
                            if not (x0-20<bx<x0+T+20 and y0-20<by<y0+T+20): break
                        name=f"tt_{ann.stem}_{n}_n{_}.jpg"; cv2.imwrite(str(out/"img"/name),f[y0:y0+T,x0:x0+T],[cv2.IMWRITE_JPEG_QUALITY,92])
                        meta.append({"file":name,"split":split,"ball":None,"src":"teamtrack"})
            n+=1
    print(split,len(meta),flush=True)
json.dump(meta,open(out/"meta_tt.json","w"))
