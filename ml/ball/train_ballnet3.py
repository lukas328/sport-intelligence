"""3-frame ball heatmap net: frames t-G, t, t+G stacked (9 channels). ResNet18 layers 1-2 + decoder, stride 4.
Initialised from the single-frame net: centre channels get its first conv, neighbour channels start at zero,
so training starts from the single-frame behaviour and learns to use motion."""
import json,random,time,sys,numpy as np,cv2,torch,torch.nn as nn,torch.nn.functional as F,torchvision
from pathlib import Path
torch.set_num_threads(int(sys.argv[6]) if len(sys.argv)>6 else 4); random.seed(0); np.random.seed(0); torch.manual_seed(0)
D=Path(sys.argv[1]); OUT=Path(sys.argv[2]); ITERS=int(sys.argv[3]); METAS=sys.argv[4].split(","); INIT=sys.argv[5] if len(sys.argv)>5 else ""
meta=[m for f in METAS for m in json.load(open(D/f))]
tr=[m for m in meta if m["split"]=="train"]; va=[m for m in meta if m["split"]!="train"]; random.shuffle(va); va=va[:2000]
T=192
class BallNet3(nn.Module):
    def __init__(s):
        super().__init__()
        r=torchvision.models.resnet18(weights=None)
        c1=nn.Conv2d(9,64,7,2,3,bias=False)
        s.stem=nn.Sequential(c1,r.bn1,r.relu,r.maxpool); s.l1=r.layer1; s.l2=r.layer2
        s.up=nn.Sequential(nn.Conv2d(128,64,3,padding=1),nn.BatchNorm2d(64),nn.ReLU())
        s.head=nn.Sequential(nn.Conv2d(128,64,3,padding=1),nn.BatchNorm2d(64),nn.ReLU(),nn.Conv2d(64,1,1))
        s.register_buffer("mean",torch.tensor([0.485,0.456,0.406]*3).view(1,9,1,1)*255); s.register_buffer("std",torch.tensor([0.229,0.224,0.225]*3).view(1,9,1,1)*255)
    def forward(s,x):  # N,9,H,W RGB 0..255 (prev, centre, next) -> N,1,H/4,W/4 logits
        x=(x-s.mean)/s.std; a=s.l1(s.stem(x)); b=s.l2(a)
        b=F.interpolate(s.up(b),size=a.shape[-2:],mode="bilinear",align_corners=False)
        return s.head(torch.cat([a,b],1))
def init_from_single(net,path):
    sd=torch.load(path,map_location="cpu",weights_only=True); w=sd["stem.0.weight"]
    sd["stem.0.weight"]=torch.cat([torch.zeros_like(w),w,torch.zeros_like(w)],1)
    sd["mean"]=net.mean; sd["std"]=net.std
    print(net.load_state_dict(sd,strict=True),flush=True)
def read(m):
    folder="cand" if m["file"].startswith("cand_") else "img"
    t=cv2.cvtColor(cv2.imread(str(D/folder/m["file"])),cv2.COLOR_BGR2RGB)
    return np.concatenate([t[:,0:T],t[:,T:2*T],t[:,2*T:3*T]],2)  # 192,192,9
def load(m,aug):
    img=read(m); ball=list(m["ball"]) if m["ball"] else None
    if aug:
        sc=random.uniform(0.7,1.5); img=np.concatenate([cv2.resize(img[...,k:k+3],None,fx=sc,fy=sc) for k in (0,3,6)],2)
        if ball: ball=[ball[0]*sc,ball[1]*sc,ball[2]*sc]
        H,W=img.shape[:2]
        if H<T: img=np.concatenate([cv2.copyMakeBorder(img[...,k:k+3],0,T-H,0,T-W,cv2.BORDER_REFLECT) for k in (0,3,6)],2); H,W=img.shape[:2]
        if ball: x0=int(np.clip(ball[0]-random.uniform(12,T-12),0,W-T)); y0=int(np.clip(ball[1]-random.uniform(12,T-12),0,H-T))
        else: x0=random.randint(0,W-T); y0=random.randint(0,H-T)
        img=img[y0:y0+T,x0:x0+T]
        if ball: ball=[ball[0]-x0,ball[1]-y0,ball[2]]
        if random.random()<.5:
            img=img[:,::-1].copy()
            if ball: ball[0]=T-1-ball[0]
        if random.random()<.5: img=np.concatenate([img[...,6:9],img[...,3:6],img[...,0:3]],2)  # time reversed
        dh=random.randint(0,179); sat=random.uniform(.6,1.4); gain=random.uniform(.7,1.3); off=random.uniform(-25,25)
        out=[]
        for k in (0,3,6):
            hsv=cv2.cvtColor(np.ascontiguousarray(img[...,k:k+3]),cv2.COLOR_RGB2HSV).astype(np.int16); hsv[...,0]=(hsv[...,0]+dh)%180
            hsv[...,1]=np.clip(hsv[...,1]*sat,0,255); out.append(cv2.cvtColor(hsv.astype(np.uint8),cv2.COLOR_HSV2RGB))
        img=np.clip(np.concatenate(out,2).astype(np.float32)*gain+off,0,255).astype(np.uint8)
    hm=np.zeros((48,48),np.float32)
    if ball and 0<=ball[0]<T and 0<=ball[1]<T:
        cx,cy=ball[0]/4,ball[1]/4; yy,xx=np.mgrid[0:48,0:48]; hm=np.exp(-((xx-cx)**2+(yy-cy)**2)/(2*1.2**2)).astype(np.float32)
    return img,hm
def focal(logit,gt):
    p=torch.sigmoid(logit).clamp(1e-4,1-1e-4); pos=gt>0.95
    pl=-torch.log(p)*(1-p)**2*pos; nl=-torch.log(1-p)*p**2*(1-gt)**4*(~pos)
    return (pl.sum()+nl.sum())/max(1,int(pos.sum()))
def batch(ms,aug):
    xs,hs=zip(*[load(m,aug) for m in ms])
    return torch.from_numpy(np.stack(xs)).permute(0,3,1,2).float(),torch.from_numpy(np.stack(hs)).unsqueeze(1)
def evaluate(net):
    net.eval(); res={}
    with torch.no_grad():
        for k in range(0,len(va),64):
            ms=va[k:k+64]; x,_=batch(ms,False); hm=torch.sigmoid(net(x))[:,0].numpy()
            for m,h in zip(ms,hm):
                g=res.setdefault(m["src"] if m["src"]=="teamtrack" else "ours",{"pos":[],"neg":[]})
                yx=np.unravel_index(h.argmax(),h.shape); s=float(h.max())
                if m["ball"]: g["pos"].append(s if np.hypot(yx[1]*4+2-m["ball"][0],yx[0]*4+2-m["ball"][1])<8 else 0.0)
                else: g["neg"].append(s)
    net.train()
    return {src:{t:(round(float((np.array(g["pos"])>=t).mean()),3) if g["pos"] else None,round(float((np.array(g["neg"])>=t).mean()),4) if g["neg"] else None) for t in (0.3,0.5)} for src,g in res.items()}
if __name__=="__main__":
    net=BallNet3()
    if INIT.endswith("3.pt"): net.load_state_dict(torch.load(INIT,map_location="cpu",weights_only=True)); print("resume",INIT)
    elif INIT: init_from_single(net,INIT)
    base=("stem","l1","l2")
    opt=torch.optim.AdamW([{"params":[p for n,p in net.named_parameters() if n.startswith(base)],"lr":2e-4},{"params":[p for n,p in net.named_parameters() if not n.startswith(base)],"lr":1e-3}],weight_decay=1e-4)
    groups={"tt_pos":[m for m in tr if m["ball"] and m["src"]=="teamtrack"],"our_pos":[m for m in tr if m["ball"] and m["src"]!="teamtrack"],
            "tt_neg":[m for m in tr if not m["ball"] and m["src"]=="teamtrack"],"our_neg":[m for m in tr if not m["ball"] and m["src"]!="teamtrack" and not m.get("hard")],
            "hard_neg":[m for m in tr if not m["ball"] and m.get("hard")]}
    mix={"tt_pos":12,"our_pos":6,"tt_neg":6,"our_neg":4,"hard_neg":6}
    mix["our_pos"]=min(6,len(groups["our_pos"])//40); mix["hard_neg"]=min(6,max(1,len(groups["hard_neg"])//40))
    mix={k:v for k,v in mix.items() if groups[k] and v}; print({k:len(v) for k,v in groups.items()},flush=True); t0=time.time()
    print("val at start:",evaluate(net),flush=True)
    for it in range(1,ITERS+1):
        ms=[m for k,v in mix.items() for m in random.choices(groups[k],k=v)]; x,h=batch(ms,True)
        loss=focal(net(x),h); opt.zero_grad(); loss.backward(); opt.step()
        if it%100==0: print(f"it {it} loss {loss.item():.3f} {time.time()-t0:.0f}s",flush=True)
        if it%1000==0 or it==ITERS:
            print("val (found, false alarm):",evaluate(net),flush=True); torch.save(net.state_dict(),OUT.with_suffix(".pt"))
    net.eval(); torch.onnx.export(net,torch.zeros(1,9,192,192),str(OUT),input_names=["x"],output_names=["heat"],dynamic_axes={"x":{0:"n",2:"h",3:"w"},"heat":{0:"n",2:"h4",3:"w4"}},opset_version=17)
    print("exported",OUT,flush=True)
