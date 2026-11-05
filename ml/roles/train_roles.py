"""Role classifier (player / goalkeeper / referee) on person crops, ResNet18 (ImageNet), balanced batches.
Reports per-class recall on the held-out set (unseen halls)."""
import json,random,sys,time,numpy as np,cv2,torch,torch.nn as nn,torchvision
torch.set_num_threads(3); random.seed(0); torch.manual_seed(0)
D=sys.argv[1]; STEPS=int(sys.argv[2]) if len(sys.argv)>2 else 1500
meta=json.load(open(D+"/meta.json")); C=["player","goalkeeper","referee"]
tr=[m for m in meta if m["split"]=="train"]; va=[m for m in meta if m["split"]=="val"]; te=[m for m in meta if m["split"]=="test"]
r=torchvision.models.resnet18(weights=torchvision.models.ResNet18_Weights.IMAGENET1K_V1); r.fc=nn.Linear(512,3); net=r
MEAN=torch.tensor([0.485,0.456,0.406]).view(1,3,1,1)*255; STD=torch.tensor([0.229,0.224,0.225]).view(1,3,1,1)*255
def load(m,aug):
    x=cv2.cvtColor(cv2.imread(D+"/crops/"+m["file"]),cv2.COLOR_BGR2RGB)
    if aug:
        if random.random()<.5: x=x[:,::-1]
        s=random.uniform(.85,1); h,w=int(128*s),int(64*s); y0=random.randint(0,128-h); x0=random.randint(0,64-w); x=cv2.resize(np.ascontiguousarray(x[y0:y0+h,x0:x0+w]),(64,128))
        x=np.clip(x.astype(np.float32)*random.uniform(.75,1.25)+random.uniform(-20,20),0,255)
    return np.ascontiguousarray(x,dtype=np.float32)
def batch(ms,aug): x=torch.from_numpy(np.stack([load(m,aug) for m in ms])).permute(0,3,1,2); return (x-MEAN)/STD
def evaluate(ms):
    net.eval(); P=[]
    with torch.no_grad():
        for k in range(0,len(ms),256): P+=net(batch(ms[k:k+256],False)).argmax(1).tolist()
    net.train(); y=[C.index(m["role"]) for m in ms]; out={}
    for c in range(3):
        idx=[i for i,t in enumerate(y) if t==c]; pr=[i for i,p in enumerate(P) if p==c]
        out[C[c]]={"recall":round(float(np.mean([P[i]==c for i in idx])),3) if idx else None,"precision":round(float(np.mean([y[i]==c for i in pr])),3) if pr else None}
    return out
if __name__=="__main__":
    by={c:[m for m in tr if m["role"]==c] for c in C}; opt=torch.optim.AdamW(net.parameters(),lr=3e-4,weight_decay=1e-4); lossf=nn.CrossEntropyLoss(); t0=time.time()
    for it in range(1,STEPS+1):
        ms=random.choices(by["player"],k=24)+random.choices(by["goalkeeper"],k=20)+random.choices(by["referee"],k=20)
        y=torch.tensor([C.index(m["role"]) for m in ms]); loss=lossf(net(batch(ms,True)),y); opt.zero_grad(); loss.backward(); opt.step()
        if it%500==0: print(f"it {it} loss {loss.item():.3f} {time.time()-t0:.0f}s val",evaluate(va),flush=True)
    print("TEST (held-out halls):",evaluate(te),flush=True); torch.save(net.state_dict(),D+"/roles.pt")
