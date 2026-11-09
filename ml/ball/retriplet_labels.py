"""Labelled single-frame candidates -> triplets (t-G, t, t+G); tile position found by template matching."""
import sys,json,random,cv2,numpy as np
from collections import deque
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
B=Path(sys.argv[1]); out=Path(sys.argv[2]); V=Path(str(ROOT/"data/videos")); T=192; random.seed(1)
labels=json.load(open(B/"labels_ours.json")); cands={c["file"]:c for f in B.glob("cands_*.json") for c in json.load(open(f))}
by={}
for fn,lab in labels.items(): c=cands[fn]; by.setdefault(c["vid"],[]).append((c,lab))
meta=[]
for vid,items in by.items():
    cap=cv2.VideoCapture(str(V/f"{vid}.mp4")); fps=cap.get(cv2.CAP_PROP_FPS); G=3 if fps>40 else 2
    want={c["frame"]:[] for c,_ in items}
    for c,l in items: want[c["frame"]].append((c,l))
    buf=deque(maxlen=2*G+1); n=-1; last=max(want)+G
    while n<last:
        ok,f=cap.read()
        if not ok: break
        n+=1; buf.append(f); c_=n-G
        if c_ not in want or len(buf)<2*G+1: continue
        for c,lab in want[c_]:
            tile=cv2.imread(str(B/"img"/c["file"]))
            if tile is None: continue
            r=cv2.matchTemplate(buf[G],tile,cv2.TM_SQDIFF_NORMED); _,_,(x0,y0),_=cv2.minMaxLoc(r)
            t=cv2.hconcat([buf[0][y0:y0+T,x0:x0+T],buf[G][y0:y0+T,x0:x0+T],buf[2*G][y0:y0+T,x0:x0+T]])
            fn="tri_"+c["file"]; cv2.imwrite(str(out/"img"/fn),t,[cv2.IMWRITE_JPEG_QUALITY,90])
            bx,by_=c["ball_in_tile"]
            meta.append({"file":fn,"split":"train" if random.random()<.8 else "val","ball":[bx,by_,12] if lab else None,"src":"ours_labelled","hard":not lab,"vid":vid})
    print(vid,fps,len([m for m in meta if m["vid"]==vid]),flush=True)
json.dump(meta,open(out/"meta_ourlab.json","w"))
