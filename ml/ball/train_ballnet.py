"""Ball heatmap net: ResNet18 (ImageNet) layers 1-2 + small decoder, stride-4 heatmap (CenterNet focal loss)."""
import json,random,time,sys,math,numpy as np,cv2,torch,torch.nn as nn,torch.nn.functional as F,torchvision
from pathlib import Path
torch.set_num_threads(4); random.seed(0); np.random.seed(0); torch.manual_seed(0)
D=Path(sys.argv[1]); OUT=Path(sys.argv[2]); ITERS=int(sys.argv[3]) if len(sys.argv)>3 else 3000
meta=json.load(open(D/(sys.argv[4] if len(sys.argv)>4 else "meta.json"))); tr=[m for m in meta if m["split"]=="train"]; va=[m for m in meta if m["split"]!="train"]
random.shuffle(va); va=va[:1500]
class BallNet(nn.Module):
    def __init__(s):
        super().__init__()
        r=torchvision.models.resnet18(weights=torchvision.models.ResNet18_Weights.IMAGENET1K_V1)
        s.stem=nn.Sequential(r.conv1,r.bn1,r.relu,r.maxpool); s.l1=r.layer1; s.l2=r.layer2
        s.up=nn.Sequential(nn.Conv2d(128,64,3,padding=1),nn.BatchNorm2d(64),nn.ReLU())
        s.head=nn.Sequential(nn.Conv2d(128,64,3,padding=1),nn.BatchNorm2d(64),nn.ReLU(),nn.Conv2d(64,1,1))
        s.head[-1].bias.data.fill_(-4.0)
        s.register_buffer("mean",torch.tensor([0.485,0.456,0.406]).view(1,3,1,1)*255); s.register_buffer("std",torch.tensor([0.229,0.224,0.225]).view(1,3,1,1)*255)
    def forward(s,x):  # x: N,3,H,W RGB 0..255 -> N,1,H/4,W/4 logits
        x=(x-s.mean)/s.std; a=s.l1(s.stem(x)); b=s.l2(a)
        b=F.interpolate(s.up(b),size=a.shape[-2:],mode="bilinear",align_corners=False)
        return s.head(torch.cat([a,b],1))
def load(m,aug):
    img=cv2.cvtColor(cv2.imread(str(D/"img"/m["file"])),cv2.COLOR_BGR2RGB); ball=m["ball"]
    if aug:
        sc=random.uniform(0.7,1.5); img=cv2.resize(img,None,fx=sc,fy=sc,interpolation=cv2.INTER_LINEAR)
        if ball: ball=[ball[0]*sc,ball[1]*sc,ball[2]*sc]
        H,W=img.shape[:2]; T=192
        if H<T: img=cv2.copyMakeBorder(img,0,T-H,0,T-W,cv2.BORDER_REFLECT); H,W=img.shape[:2]
        if ball:
            x0=int(np.clip(ball[0]-random.uniform(12,T-12),0,W-T)); y0=int(np.clip(ball[1]-random.uniform(12,T-12),0,H-T))
        else: x0=random.randint(0,W-T); y0=random.randint(0,H-T)
        img=img[y0:y0+T,x0:x0+T]
        if ball: ball=[ball[0]-x0,ball[1]-y0,ball[2]]
        if random.random()<.5:
            img=img[:,::-1].copy()
            if ball: ball[0]=T-1-ball[0]
        hsv=cv2.cvtColor(img,cv2.COLOR_RGB2HSV).astype(np.int16); hsv[...,0]=(hsv[...,0]+random.randint(0,179))%180
        hsv[...,1]=np.clip(hsv[...,1]*random.uniform(.6,1.4),0,255); img=cv2.cvtColor(hsv.astype(np.uint8),cv2.COLOR_HSV2RGB)
        img=np.clip(img.astype(np.float32)*random.uniform(.7,1.3)+random.uniform(-25,25),0,255).astype(np.uint8)
        if random.random()<.3:
            k=random.choice([3,5,7]); ker=np.zeros((k,k),np.float32); ker[k//2,:]=1/k
            M=cv2.getRotationMatrix2D((k/2-.5,k/2-.5),random.uniform(0,180),1); ker=cv2.warpAffine(ker,M,(k,k)); ker/=ker.sum()+1e-6; img=cv2.filter2D(img,-1,ker)
    hm=np.zeros((48,48),np.float32)
    if ball and 0<=ball[0]<192 and 0<=ball[1]<192:
        cx,cy=ball[0]/4,ball[1]/4; yy,xx=np.mgrid[0:48,0:48]; hm=np.exp(-((xx-cx)**2+(yy-cy)**2)/(2*1.2**2)).astype(np.float32)
    return img,hm,ball
def focal(logit,gt):
    p=torch.sigmoid(logit).clamp(1e-4,1-1e-4); pos=gt.eq(1) | (gt>0.95)
    pl=-torch.log(p)*(1-p)**2*pos; nl=-torch.log(1-p)*p**2*(1-gt)**4*(~pos)
    return (pl.sum()+nl.sum())/max(1,int(pos.sum()))
def batch(ms,aug):
    xs,hs=[],[]
    for m in ms:
        i,h,_=load(m,aug); xs.append(i); hs.append(h)
    return torch.from_numpy(np.stack(xs)).permute(0,3,1,2).float(),torch.from_numpy(np.stack(hs)).unsqueeze(1)
def evaluate(net):
    net.eval(); tp=fn=0; negs=[]; poss=[]
    with torch.no_grad():
        for k in range(0,len(va),64):
            ms=va[k:k+64]; x,_=batch(ms,False); hm=torch.sigmoid(net(x))[:,0].numpy()
            for m,h in zip(ms,hm):
                yx=np.unravel_index(h.argmax(),h.shape); s=float(h.max())
                if m["ball"]:
                    ok=np.hypot(yx[1]*4+2-m["ball"][0],yx[0]*4+2-m["ball"][1])<8
                    poss.append(s if ok else 0.0)
                else: negs.append(s)
    net.train(); poss=np.array(poss); negs=np.array(negs)
    return {t:(round(float((poss>=t).mean()),3),round(float((negs>=t).mean()),4)) for t in (0.3,0.5,0.7)}
net=BallNet()
if len(sys.argv)>5: net.load_state_dict(torch.load(sys.argv[5],map_location="cpu",weights_only=True)); print("start from",sys.argv[5],flush=True)
opt=torch.optim.AdamW([{"params":[p for n,p in net.named_parameters() if n.startswith(("stem","l1","l2"))],"lr":2e-4},{"params":[p for n,p in net.named_parameters() if not n.startswith(("stem","l1","l2"))],"lr":1e-3}],weight_decay=1e-4)
groups={"tt_pos":[m for m in tr if m["ball"] and m["src"]=="teamtrack"],"our_pos":[m for m in tr if m["ball"] and m["src"]!="teamtrack"],
        "tt_neg":[m for m in tr if not m["ball"] and m["src"]=="teamtrack"],"our_neg":[m for m in tr if not m["ball"] and m["src"] in ("staefa","moehlin","leimental","cottbus")],
        "hard_neg":[m for m in tr if not m["ball"] and m["src"] in ("hardneg","ours_labelled")]}
mix={"tt_pos":12,"our_pos":4,"tt_neg":8,"our_neg":4,"hard_neg":4}
mix={k:v for k,v in mix.items() if groups[k]}; print({k:len(v) for k,v in groups.items()},flush=True); t0=time.time()
for it in range(1,ITERS+1):
    ms=[m for k,v in mix.items() for m in random.choices(groups[k],k=v)]; x,h=batch(ms,True)
    loss=focal(net(x),h); opt.zero_grad(); loss.backward(); opt.step()
    if it%50==0: print(f"it {it} loss {loss.item():.3f} {time.time()-t0:.0f}s",flush=True)
    if it%500==0 or it==ITERS:
        print("val (ball found, false alarm) by threshold:",evaluate(net),flush=True)
        torch.save(net.state_dict(),OUT.with_suffix(".pt"))
net.eval(); torch.onnx.export(net,torch.zeros(1,3,192,192),str(OUT),input_names=["x"],output_names=["heat"],dynamic_axes={"x":{0:"n",2:"h",3:"w"},"heat":{0:"n",2:"h4",3:"w4"}},opset_version=17)
print("exported",OUT,flush=True)
