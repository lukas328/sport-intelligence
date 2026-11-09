"""How often is the labelled ball inside a player box (held / at the body) vs free? Also saves the
person boxes per user frame for the holder classifier."""
from pathlib import Path as _P
ROOT=_P(__file__).resolve().parents[2]
import sys,json,glob,cv2,numpy as np
sys.path.insert(0,str(ROOT/"packages/vision"))
from pathlib import Path
from handball_vision.detection import YoloxDetector
from handball_vision.ballpossession import holder
P=sys.argv[1]; det=YoloxDetector(Path(str(ROOT/"data/models/yolox_m.onnx")),threads=3)
L=[json.load(open(f))|{"id":f.split("/")[-1][:-5]} for f in glob.glob(P+"/db2/labels/*.json")]
boxes={}; inside=[]; by={}
for l in L:
    t=cv2.imread(f"{P}/t/{l['id']}.jpg"); W=l["w"]; c=t[:,W:2*W]
    ds=[d for d in det.detect([c])[0] if d.cls=="person"]
    boxes[l["id"]]=[[round(d.x1,1),round(d.y1,1),round(d.x2,1),round(d.y2,1),round(d.score,3)] for d in ds]
    if l["state"]=="ball":
        h=holder((l["x"],l["y"]),[(i,d.x1,d.y1,d.x2,d.y2) for i,d in enumerate(ds)])
        inside.append(h is not None); by.setdefault(l["hall"],[]).append(h is not None)
json.dump(boxes,open(P+"/person_boxes.json","w"))
print("ball frames",len(inside),"ball at a player",round(float(np.mean(inside)),2))
for h,v in sorted(by.items()): print(f"  {h:20s} {np.mean(v):.2f} of {len(v)}")
