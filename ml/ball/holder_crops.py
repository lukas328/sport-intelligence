"""Player crops for the holder classifier from the user's ball frames: the player holding the ball
(holder() on the clicked ball) is positive, every other player in that frame negative. Crops: box
widened 25 % each side and raised 25 % (ball overhead), the three frames t-G, t, t+G side by side."""
from pathlib import Path as _P
ROOT=_P(__file__).resolve().parents[2]
import sys,json,glob,cv2,numpy as np
sys.path.insert(0,str(ROOT/"packages/vision"))
from handball_vision.ballpossession import holder
P=sys.argv[1]; out=sys.argv[2]
boxes=json.load(open(P+"/person_boxes.json")); split=json.load(open(sys.argv[3]))
L=[json.load(open(f))|{"id":f.split("/")[-1][:-5]} for f in glob.glob(P+"/db2/labels/*.json")]
meta=[]
for l in L:
    if l["state"]!="ball": continue
    bs=[b for b in boxes[l["id"]] if b[3]-b[1]>=40]
    if not bs: continue
    h=holder((l["x"],l["y"]),[(i,*b[:4]) for i,b in enumerate(bs)])
    t=cv2.imread(f"{P}/t/{l['id']}.jpg"); W=l["w"]; H=t.shape[0]
    for i,(x1,y1,x2,y2,_) in enumerate(bs):
        w,hh=x2-x1,y2-y1; X1=int(max(0,x1-.25*w)); X2=int(min(W,x2+.25*w)); Y1=int(max(0,y1-.25*hh)); Y2=int(min(H,y2+.05*hh))
        crops=[cv2.resize(t[Y1:Y2,k*W+X1:k*W+X2],(96,192)) for k in range(3)]
        fn=f"{l['id']}_{i}.jpg"; cv2.imwrite(f"{out}/crops/{fn}",cv2.hconcat(crops),[cv2.IMWRITE_JPEG_QUALITY,92])
        meta.append({"file":fn,"y":int(i==h),"frame":l["id"],"hall":l["hall"],"split":split.get(l["id"],"train"),"box_h":round(hh,1)})
json.dump(meta,open(out+"/meta.json","w"))
from collections import Counter; print(Counter((m["split"],m["y"]) for m in meta))
