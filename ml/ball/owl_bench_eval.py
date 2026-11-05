import json, glob, numpy as np, collections
import os
S = os.environ["SCRATCH"]  # holds owl_local/bench_owl.json and labelpage/
res=json.load(open(S+"/owl_local/bench_owl.json"))
out=collections.defaultdict(list)
for i,boxes in res.items():
    lab=json.load(open(f"{S}/labelpage/db2/labels/{i}.json"))
    b=sorted(boxes,key=lambda x:-x[4])
    d=[np.hypot(x[0]-lab["x"],x[1]-lab["y"]) for x in b]
    hit=[k for k,v in enumerate(d) if v<12]
    rank=hit[0] if hit else None
    sc=b[rank][4] if hit else 0
    out[lab["hall"]].append((rank,sc,b[0][4] if b else 0,len(b)))
    print(f"{lab['hall']:18s} {i[:28]:28s} n={len(b):3d} rank={rank} score@ball={sc:.2f} top={b[0][4] if b else 0:.2f}")
allr=[r for v in out.values() for r in v]
print("frames",len(allr),"top1",np.mean([r[0]==0 for r in allr]),"top5",np.mean([r[0] is not None and r[0]<5 for r in allr]),"any",np.mean([r[0] is not None for r in allr]))
