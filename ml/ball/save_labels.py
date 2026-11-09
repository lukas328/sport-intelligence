import sys,json
from pathlib import Path
D=Path(sys.argv[1]); grid=sys.argv[2]; pos=set(map(int,sys.argv[3].split(","))) if sys.argv[3] else set(); skip=set(map(int,sys.argv[4].split(","))) if len(sys.argv)>4 and sys.argv[4] else set()
sel=json.load(open(D/grid)); p=D/"labels_ours.json"; lab=json.load(open(p)) if p.exists() else {}
for k,f in enumerate(sel):
    if k in skip: continue
    lab[f]=1 if k in pos else 0
json.dump(lab,open(p,"w")); print("labels",len(lab),"pos",sum(lab.values()))
