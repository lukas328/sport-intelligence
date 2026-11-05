"""Holder classifier: does this player hold the ball? Player crop over 3 frames (9 channels), ResNet18
(ImageNet) with the first conv extended (centre frame = pretrained weights, neighbours start at 0)."""
import json,random,sys,time,numpy as np,cv2,torch,torch.nn as nn,torchvision
torch.set_num_threads(3); random.seed(0); torch.manual_seed(0)
D=sys.argv[1]; EPOCHS=int(sys.argv[2]) if len(sys.argv)>2 else 12
meta=json.load(open(D+"/meta.json")); tr=[m for m in meta if m["split"]=="train"]; te=[m for m in meta if m["split"]=="test"]
def net9():
    r=torchvision.models.resnet18(weights=torchvision.models.ResNet18_Weights.IMAGENET1K_V1); w=r.conv1.weight.data
    c=nn.Conv2d(9,64,7,2,3,bias=False); c.weight.data=torch.cat([torch.zeros_like(w),w,torch.zeros_like(w)],1); r.conv1=c
    r.fc=nn.Linear(512,1); return r
MEAN=torch.tensor([0.485,0.456,0.406]*3).view(1,9,1,1)*255; STD=torch.tensor([0.229,0.224,0.225]*3).view(1,9,1,1)*255
def load(m,aug):
    t=cv2.cvtColor(cv2.imread(D+"/crops/"+m["file"]),cv2.COLOR_BGR2RGB); w=t.shape[1]//3
    x=np.concatenate([t[:,k*w:(k+1)*w] for k in range(3)],2)
    if aug:
        if random.random()<.5: x=x[:,::-1]
        if random.random()<.5: x=np.concatenate([x[...,6:9],x[...,3:6],x[...,0:3]],2)
        H,W=x.shape[:2]; s=random.uniform(.85,1.0); h2,w2=int(H*s),int(W*s); y0=random.randint(0,H-h2); x0=random.randint(0,W-w2)
        x=np.concatenate([cv2.resize(np.ascontiguousarray(x[y0:y0+h2,x0:x0+w2,k:k+3]),(W,H)) for k in (0,3,6)],2)
        dh=random.randint(0,179); out=[]
        for k in (0,3,6):
            hsv=cv2.cvtColor(np.ascontiguousarray(x[...,k:k+3]),cv2.COLOR_RGB2HSV).astype(np.int16); hsv[...,0]=(hsv[...,0]+dh)%180
            out.append(cv2.cvtColor(hsv.astype(np.uint8),cv2.COLOR_HSV2RGB))
        x=np.clip(np.concatenate(out,2).astype(np.float32)*random.uniform(.75,1.25)+random.uniform(-20,20),0,255)
    return np.ascontiguousarray(x,dtype=np.float32)
def batch(ms,aug):
    x=torch.from_numpy(np.stack([load(m,aug) for m in ms])).permute(0,3,1,2); return (x-MEAN)/STD
def evaluate(net,ms):
    net.eval(); ps=[]
    with torch.no_grad():
        for k in range(0,len(ms),64): ps+=torch.sigmoid(net(batch(ms[k:k+64],False))[:,0]).tolist()
    net.train(); by={}
    for m,p in zip(ms,ps): by.setdefault(m["frame"],[]).append((p,m["y"]))
    top=np.mean([max(v)[1]==1 for v in by.values()])  # the most likely player is the holder
    pos=[p for m,p in zip(ms,ps) if m["y"]]; neg=[p for m,p in zip(ms,ps) if not m["y"]]
    auc=np.mean([[pp>nn_ for nn_ in neg] for pp in pos])
    return {"frames":len(by),"holder_is_top":round(float(top),3),"auc":round(float(auc),3),"neg>0.5":round(float(np.mean(np.array(neg)>.5)),3),"pos>0.5":round(float(np.mean(np.array(pos)>.5)),3)}
if __name__=="__main__":
    net=net9(); opt=torch.optim.AdamW(net.parameters(),lr=3e-4,weight_decay=1e-4); lossf=nn.BCEWithLogitsLoss()
    pos=[m for m in tr if m["y"]]; neg=[m for m in tr if not m["y"]]; t0=time.time()
    print("train",len(pos),"pos",len(neg),"neg | test at start",evaluate(net,te),flush=True)
    for ep in range(EPOCHS):
        for _ in range(30):
            ms=random.choices(pos,k=12)+random.choices(neg,k=20); y=torch.tensor([m["y"] for m in ms],dtype=torch.float32)
            loss=lossf(net(batch(ms,True))[:,0],y); opt.zero_grad(); loss.backward(); opt.step()
        print(f"epoch {ep+1} loss {loss.item():.3f} {time.time()-t0:.0f}s test",evaluate(net,te),flush=True)
    torch.save(net.state_dict(),D+"/holder.pt")
