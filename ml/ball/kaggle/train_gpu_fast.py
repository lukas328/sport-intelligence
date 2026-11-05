import glob,os,sys,json
_D=os.path.dirname(glob.glob("/kaggle/input/**/meta_tt.json",recursive=True)[0])
_D2=os.path.dirname(glob.glob("/kaggle/input/**/meta_seq.json",recursive=True)[0])
_DS=glob.glob("/kaggle/input/**/basketball-instants-dataset.json",recursive=True)
_RF=glob.glob("/kaggle/input/**/meta_roboflow.json",recursive=True)
_METAS="meta_tt.json,meta_ourlab.json,meta_lab3.json,meta_user.json,meta_konstanz_wuerzburg.json,meta_uznach_dietikon.json,meta_eisenach_wetzlar.json,meta_leimental_frauenfeld.json,meta_muelheim_suedpfalz.json,meta_u20_sui_ger.json"
ITERS_ENV=int(os.environ.get("ITERS","20000"))
sys.argv=[sys.argv[0],_D,"/kaggle/working/ball3f.onnx",str(ITERS_ENV),_METAS,(glob.glob("/kaggle/input/**/ball_best.pt",recursive=True) or [_D+"/ball3a.pt"])[0],"4"]
print("data",_D,_D2,_DS,flush=True)
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
    folder="cand" if m["file"].startswith(("cand_","mine_")) else "img"
    t=cv2.cvtColor(cv2.imread(str(Path(m.get("root",D))/folder/m["file"])),cv2.COLOR_BGR2RGB); w=t.shape[1]//3
    return np.concatenate([t[:,0:w],t[:,w:2*w],t[:,2*w:3*w]],2)  # tile,tile,9
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
    if not aug and (img.shape[0]>T or img.shape[1]>T):  # larger tiles: a fixed 192 window around the ball (or the centre)
        H,W=img.shape[:2]; cx,cy=(ball[0],ball[1]) if ball else (W/2,H/2)
        x0=int(np.clip(cx-T/2,0,W-T)); y0=int(np.clip(cy-T/2,0,H-T)); img=img[y0:y0+T,x0:x0+T]
        if ball: ball=[ball[0]-x0,ball[1]-y0,ball[2]]
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
                g=res.setdefault(m["src"].split("_")[0],{"pos":[],"neg":[]})
                yx=np.unravel_index(h.argmax(),h.shape); s=float(h.max())
                if m["ball"]: g["pos"].append(s if np.hypot(yx[1]*4+2-m["ball"][0],yx[0]*4+2-m["ball"][1])<8 else 0.0)
                else: g["neg"].append(s)
    net.train()
    return {src:{t:(round(float((np.array(g["pos"])>=t).mean()),3) if g["pos"] else None,round(float((np.array(g["neg"])>=t).mean()),4) if g["neg"] else None) for t in (0.3,0.5)} for src,g in res.items()}

# research-only extras: our labelled sequences, DeepSport basketball (CC BY-NC-SA)
_seq=json.load(open(_D2+"/meta_seq.json"))
for m in _seq: m["root"]=_D2
"""DeepSport basketball instants -> triplet tiles for the 3-frame ball net (research only, CC BY-NC-SA).
The ball's 3D centre is projected with the camera calibration (Bouguet distortion); each image is scaled
so the ball measures 8 to 24 px like in our halls; neighbours are the +40 ms frame on both sides."""
import json,os,random,cv2,numpy as np
def project(cal,X):
    K=np.array(cal["KK"]).reshape(3,3); R=np.array(cal["R"]).reshape(3,3); T=np.array(cal["T"]); k1,k2,p1,p2,k3=cal["kc"]
    Xc=R@np.asarray(X)+T; x,y=Xc[0]/Xc[2],Xc[1]/Xc[2]; r2=x*x+y*y; rad=1+k1*r2+k2*r2*r2+k3*r2**3
    xd=x*rad+2*p1*x*y+p2*(r2+2*x*x); yd=y*rad+p1*(r2+2*y*y)+2*p2*x*y
    u,v,_=K@np.array([xd,yd,1.0]); return u,v,K[0,0]*12.0/Xc[2]  # radius 12 cm -> px
def build(root,out,T=320,seed=0):
    random.seed(seed); os.makedirs(out+"/img",exist_ok=True)
    ann=json.load(open(root+"/basketball-instants-dataset.json")); meta=[]
    for a in ann:
        for b in a.get("annotations",[]):
            if b.get("type")!="ball" or not b.get("visible",True): continue
            cam=b.get("image",0)+1; base=f"{root}/{a['arena_label']}/{a['game_id']}/camcourt{cam}_{a['timestamp']}"
            if not (os.path.exists(base+".json") and os.path.exists(base+"_0.png") and os.path.exists(base+"_40.png")): continue
            cal=json.load(open(base+".json"))["calibration"]; u,v,r=project(cal,b["center"])
            i0=cv2.imread(base+"_0.png"); i1=cv2.imread(base+"_40.png")
            if i0 is None or i1 is None or not (0<=u<i0.shape[1] and 0<=v<i0.shape[0]) or r<=1: continue
            s=random.uniform(8,24)/(2*r)
            if s<1: i0=cv2.resize(i0,None,fx=s,fy=s,interpolation=cv2.INTER_AREA); i1=cv2.resize(i1,None,fx=s,fy=s,interpolation=cv2.INTER_AREA)
            else: s=1.0
            u,v=u*s,v*s; H,W=i0.shape[:2]
            if H<T or W<T: continue
            ims=[i1,i0,i1]; tag=f"ds_{a['arena_label']}_{a['timestamp']}_{cam}"
            for j in range(2):
                x0=int(np.clip(u-random.uniform(30,T-30),0,W-T)); y0=int(np.clip(v-random.uniform(30,T-30),0,H-T))
                fn=f"{tag}_p{j}.jpg"; cv2.imwrite(f"{out}/img/{fn}",cv2.hconcat([i[y0:y0+T,x0:x0+T] for i in ims]),[cv2.IMWRITE_JPEG_QUALITY,92])
                meta.append({"file":fn,"split":"train","ball":[u-x0,v-y0,2*r*s],"src":"deepsport","tile":T,"root":out})
            for j in range(2):
                for _ in range(20):
                    x0=random.randint(0,W-T); y0=random.randint(0,H-T)
                    if not (x0-20<u<x0+T+20 and y0-20<v<y0+T+20): break
                else: continue
                fn=f"{tag}_n{j}.jpg"; cv2.imwrite(f"{out}/img/{fn}",cv2.hconcat([i[y0:y0+T,x0:x0+T] for i in ims]),[cv2.IMWRITE_JPEG_QUALITY,92])
                meta.append({"file":fn,"split":"train","ball":None,"src":"deepsport","tile":T,"root":out})
    return meta

_dsp=build(os.path.dirname(_DS[0]),"/tmp/dsp") if _DS else []
print("seq",len(_seq),"deepsport",len(_dsp),flush=True)
_rf=json.load(open(_RF[0])) if _RF else []
for m in _rf: m["root"]=os.path.dirname(_RF[0])
print("roboflow",len(_rf),flush=True)
tr=tr+[m for m in _seq+_dsp]+[m for m in _rf if m["split"]=="train"]
va=va+[m for m in _rf if m["split"]!="train"][:600]

import math
from torch.utils.data import IterableDataset, DataLoader
dev="cuda" if torch.cuda.is_available() else "cpu"; print("device",dev,flush=True)
net=BallNet3(); net.load_state_dict(torch.load(INIT,map_location="cpu",weights_only=True)); net.to(dev); print("init",INIT,flush=True)
base=("stem","l1","l2")
opt=torch.optim.AdamW([{"params":[p for n,p in net.named_parameters() if n.startswith(base)],"lr":3e-4},{"params":[p for n,p in net.named_parameters() if not n.startswith(base)],"lr":1.5e-3}],weight_decay=1e-4)
sched=torch.optim.lr_scheduler.LambdaLR(opt,lambda i:min(1.0,(i+1)/300)*0.5*(1+math.cos(math.pi*min(i,ITERS)/ITERS)))
groups={"tt_pos":[m for m in tr if m["ball"] and m["src"]=="teamtrack"],
        "our_pos":[m for m in tr if m["ball"] and m["src"]!="teamtrack" and m["src"]!="deepsport" and not m["src"].startswith("roboflow")],
        "ds_pos":[m for m in tr if m["ball"] and m["src"]=="deepsport"],
        "rf_pos":[m for m in tr if m["ball"] and m["src"].startswith("roboflow")],
        "tt_neg":[m for m in tr if not m["ball"] and m["src"]=="teamtrack"],
        "our_neg":[m for m in tr if not m["ball"] and m["src"] not in ("teamtrack","deepsport") and not m["src"].startswith("roboflow") and not m.get("hard")],
        "ds_neg":[m for m in tr if not m["ball"] and m["src"]=="deepsport"],
        "rf_neg":[m for m in tr if not m["ball"] and m["src"].startswith("roboflow")],
        "hard_neg":[m for m in tr if not m["ball"] and m.get("hard")]}
mix={"tt_pos":24,"our_pos":56,"ds_pos":20,"rf_pos":36,"tt_neg":12,"our_neg":28,"ds_neg":8,"rf_neg":12,"hard_neg":36}
mix={k:v for k,v in mix.items() if groups[k]}
print({k:len(v) for k,v in groups.items()},"batch",sum(mix.values()),flush=True)
S_IN=256
def fast_load(m):
    """Decode only (single-threaded): three frames resized to 256x256, ball scaled with them; the native
    scale factor goes along so the GPU zoom keeps the ball at its true pixel size."""
    folder="cand" if m["file"].startswith(("cand_","mine_")) else "img"
    t=cv2.imread(str(Path(m.get("root",D))/folder/m["file"]))
    w=t.shape[1]//3; h=t.shape[0]; f=S_IN/w
    x=np.concatenate([cv2.resize(t[:,k*w:(k+1)*w],(S_IN,round(h*f))) for k in range(3)],2)
    if x.shape[0]!=S_IN: x=cv2.copyMakeBorder(x[:S_IN],0,max(0,S_IN-x.shape[0]),0,0,cv2.BORDER_REFLECT) if x.shape[0]<S_IN else x[:S_IN]
    b=m["ball"]; ball=[b[0]*f,b[1]*f,1.0] if b else [-1.0,-1.0,0.0]
    return x[...,::-1].copy() if False else x, np.array(ball+[f],np.float32)  # BGR kept; swapped on the GPU
class Stream(IterableDataset):
    def __iter__(self):
        wi=torch.utils.data.get_worker_info(); seed=1234+(wi.id if wi else 0)
        random.seed(seed); np.random.seed(seed); cv2.setNumThreads(1); torch.set_num_threads(1)
        while True:
            ms=[m for k,v in mix.items() for m in random.choices(groups[k],k=v)]
            xs,bs=zip(*[fast_load(m) for m in ms])
            yield torch.from_numpy(np.stack(xs)),torch.from_numpy(np.stack(bs))
K=torch.tensor([1.0,1.0,1.0],device=dev)/math.sqrt(3)
def hue_matrices(theta):
    c,s=torch.cos(theta),torch.sin(theta); kx=torch.tensor([[0,-K[2],K[1]],[K[2],0,-K[0]],[-K[1],K[0],0]],device=dev)
    I=torch.eye(3,device=dev); kk=torch.outer(K,K)
    return c[:,None,None]*I+s[:,None,None]*kx+(1-c)[:,None,None]*kk
def gpu_augment(x8,b,T=192):
    """uint8 BGR N,256,256,9 + (bx,by,valid,native) -> float RGB N,9,192,192 in 0..255 and N,1,48,48 heat."""
    n=x8.shape[0]; x=x8.to(dev,non_blocking=True).permute(0,3,1,2).float()
    x=x[:,[2,1,0,5,4,3,8,7,6]]  # BGR -> RGB per frame
    b=b.to(dev); rev=torch.rand(n,device=dev)<0.5
    x=torch.where(rev[:,None,None,None],x[:,[6,7,8,3,4,5,0,1,2]],x)
    zoom=torch.empty(n,device=dev).uniform_(0.7,1.5); wr=T*b[:,3]/zoom  # input pixels covered by the output
    valid=b[:,2]>0
    u=torch.empty(n,device=dev).uniform_(12,T-12); v=torch.empty(n,device=dev).uniform_(12,T-12)
    ox=torch.where(valid,b[:,0]-u*wr/T,torch.rand(n,device=dev)*(S_IN-wr).clamp(min=0))
    oy=torch.where(valid,b[:,1]-v*wr/T,torch.rand(n,device=dev)*(S_IN-wr).clamp(min=0))
    ox=torch.minimum(torch.maximum(ox,torch.zeros_like(ox)),(S_IN-wr).clamp(min=0)); oy=torch.minimum(torch.maximum(oy,torch.zeros_like(oy)),(S_IN-wr).clamp(min=0))
    flip=torch.rand(n,device=dev)<0.5
    a=wr/S_IN; tx=(2*ox+wr)/S_IN-1; ty=(2*oy+wr)/S_IN-1
    theta=torch.zeros(n,2,3,device=dev); theta[:,0,0]=torch.where(flip,-a,a); theta[:,0,2]=tx; theta[:,1,1]=a; theta[:,1,2]=ty
    grid=F.affine_grid(theta,(n,9,T,T),align_corners=False); x=F.grid_sample(x,grid,mode="bilinear",padding_mode="reflection",align_corners=False)
    cx=(b[:,0]-ox)*T/wr; cy=(b[:,1]-oy)*T/wr; cx=torch.where(flip,T-cx,cx)
    # colour: hue rotation around the grey axis (same for the three frames), saturation, gain, offset
    R=hue_matrices(torch.rand(n,device=dev)*2*math.pi)
    xr=x.view(n,3,3,T,T); xr=torch.einsum("nij,nfjhw->nfihw",R,xr)
    grey=xr.mean(dim=2,keepdim=True); sat=torch.empty(n,1,1,1,1,device=dev).uniform_(0.6,1.4); xr=grey+sat*(xr-grey)
    xr=xr*torch.empty(n,1,1,1,1,device=dev).uniform_(0.7,1.3)+torch.empty(n,1,1,1,1,device=dev).uniform_(-25,25)
    x=xr.reshape(n,9,T,T).clamp(0,255)
    yy,xx=torch.meshgrid(torch.arange(48,device=dev,dtype=torch.float32),torch.arange(48,device=dev,dtype=torch.float32),indexing="ij")
    inside=valid&(cx>=0)&(cx<T)&(cy>=0)&(cy<T)
    heat=torch.exp(-(((xx[None]-(cx/4)[:,None,None])**2+(yy[None]-(cy/4)[:,None,None])**2)/(2*1.2**2)))*inside[:,None,None]
    return x,heat[:,None]
def evaluate_dev(net):
    net.eval(); res={}
    with torch.no_grad():
        for k in range(0,len(va),128):
            ms=va[k:k+128]; x,_=batch(ms,False); hm=torch.sigmoid(net(x.to(dev)))[:,0].float().cpu().numpy()
            for m,h in zip(ms,hm):
                g=res.setdefault(m["src"].split("_")[0],{"pos":[],"neg":[]})
                yx=np.unravel_index(h.argmax(),h.shape); s=float(h.max())
                if m["ball"]: g["pos"].append(s if np.hypot(yx[1]*4+2-m["ball"][0],yx[0]*4+2-m["ball"][1])<8 else 0.0)
                else: g["neg"].append(s)
    net.train()
    return {src:{t:(round(float((np.array(g["pos"])>=t).mean()),3) if g["pos"] else None,round(float((np.array(g["neg"])>=t).mean()),4) if g["neg"] else None) for t in (0.3,0.5)} for src,g in res.items()}
if os.environ.get("CHECK_AUG"):  # save a few augmented samples with their heat peaks for a visual check
    xb,bb=next(iter(Stream())); sel=torch.nonzero(bb[:,2]>0)[:,0][::7][:12]; x,h=gpu_augment(xb[sel],bb[sel])
    for i in range(len(sel)):
        im=x[i,3:6].permute(1,2,0).cpu().numpy().astype(np.uint8)[:,:,::-1].copy(); hh=h[i,0].cpu().numpy()
        if hh.max()>0.5:
            yx=np.unravel_index(hh.argmax(),hh.shape); cx,cy=int(yx[1]*4+2),int(yx[0]*4+2)
            pad=cv2.copyMakeBorder(im,32,32,32,32,cv2.BORDER_CONSTANT); crop=cv2.resize(pad[cy:cy+64,cx:cx+64],(192,192),interpolation=cv2.INTER_NEAREST)
            cv2.drawMarker(crop,(96,96),(0,0,255),cv2.MARKER_CROSS,20,1); cv2.imwrite(f"/kaggle/working/aug_{i}.png",crop)
    raise SystemExit
loader=DataLoader(Stream(),batch_size=None,num_workers=max(2,(os.cpu_count() or 4)),prefetch_factor=4,persistent_workers=True,pin_memory=True)
scaler=torch.amp.GradScaler("cuda",enabled=dev=="cuda")
print("val at start:",evaluate_dev(net),flush=True); t0=time.time()
for it,(xb,bb) in enumerate(loader,1):
    x,h=gpu_augment(xb,bb)
    with torch.autocast(device_type="cuda",dtype=torch.float16,enabled=dev=="cuda"):
        logit=net(x)
    loss=focal(logit.float(),h); opt.zero_grad(set_to_none=True); scaler.scale(loss).backward(); scaler.step(opt); scaler.update(); sched.step()
    if it%200==0: print(f"it {it} loss {loss.item():.3f} {time.time()-t0:.0f}s",flush=True)
    if it%2000==0 or it==ITERS:
        print("val (found, false alarm):",evaluate_dev(net),flush=True); torch.save(net.state_dict(),"/kaggle/working/ball3f.pt")
    if it>=ITERS: break
print("done",flush=True)
