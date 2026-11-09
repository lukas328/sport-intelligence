"""Benchmark ball nets on the user's labelled frames (1280-wide triplets t-G, t, t+G)."""
import sys,json,glob,cv2,numpy as np,onnxruntime as ort,collections
P=sys.argv[1]; models=sys.argv[2:]
L=[json.load(open(f))|{"id":f.split("/")[-1][:-5]} for f in glob.glob(P+"/db2/labels/*.json")]
L=[l for l in L if l["state"]!="unsure"]
import os
if os.environ.get("SPLIT"): sp=json.load(open(os.environ["SPLIT"])); L=[l for l in L if sp.get(l["id"])=="test"]; print("test half:",len(L),"frames")
so=ort.SessionOptions(); so.intra_op_num_threads=2
def peaks(hm,k=5):
    hm=hm.copy(); out=[]
    for _ in range(k):
        yx=np.unravel_index(hm.argmax(),hm.shape); out.append((yx[1]*4+2,yx[0]*4+2,float(hm[yx]))); hm[max(0,yx[0]-6):yx[0]+6,max(0,yx[1]-6):yx[1]+6]=0
    return out
for m in models:
    s=ort.InferenceSession(m,so,providers=["CPUExecutionProvider"]); ch=s.get_inputs()[0].shape[1]
    res=collections.defaultdict(list)
    for l in L:
        t=cv2.imread(f"{P}/t/{l['id']}.jpg"); W=l["w"]; ims=[t[:,k*W:(k+1)*W] for k in range(3)]
        h2,w2=ims[0].shape[0]//32*32,W//32*32
        x=np.concatenate([cv2.cvtColor(i[:h2,:w2],cv2.COLOR_BGR2RGB) for i in (ims if ch==9 else ims[1:2])],2).transpose(2,0,1)[None].astype(np.float32)
        hm=1/(1+np.exp(-s.run(None,{s.get_inputs()[0].name:x})[0][0,0])); pk=peaks(hm)
        if l["state"]=="ball":
            d=[np.hypot(px-l["x"],py-l["y"]) for px,py,_ in pk]
            yy,xx=int(l["y"]/4),int(l["x"]/4); loc=hm[max(0,yy-3):yy+4,max(0,xx-3):xx+4]
            res[l["hall"]].append(("ball",d[0]<12,min(d)<12,float(loc.max()) if loc.size else 0.0,pk[0][2]))
        else: res[l["hall"]].append(("none",pk[0][2]))
    print("==",m.split("/")[-1])
    allb=[];alln=[]
    for h,r in sorted(res.items()):
        b=[x for x in r if x[0]=="ball"]; n=[x[1] for x in r if x[0]=="none"]; allb+=b; alln+=n
        print(f"{h:20s} balls {len(b):2d} top1 {np.mean([x[1] for x in b]):.2f} top5 {np.mean([x[2] for x in b]):.2f} score@ball med {np.median([x[3] for x in b]):.2f} | no-ball frames {len(n)} max peak med {np.median(n) if n else float('nan'):.2f}")
    print(f"{'ALL':20s} balls {len(allb)} top1 {np.mean([x[1] for x in allb]):.2f} top5 {np.mean([x[2] for x in allb]):.2f} score@ball>=0.3 {np.mean([x[3]>=0.3 for x in allb]):.2f}",flush=True)
