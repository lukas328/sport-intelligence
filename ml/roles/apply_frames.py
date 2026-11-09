import json,cv2,numpy as np,torch,torch.nn as nn,torchvision,random,sys
S=sys.argv[2]  # working folder
r=torchvision.models.resnet18(weights=None); r.fc=nn.Linear(512,3); r.load_state_dict(torch.load(S+"/roles/roles.pt",map_location="cpu",weights_only=True)); r.eval()
MEAN=torch.tensor([0.485,0.456,0.406]).view(1,3,1,1)*255; STD=torch.tensor([0.229,0.224,0.225]).view(1,3,1,1)*255
boxes=json.load(open(S+"/labelpage/person_boxes.json")); items={i["id"]:i for i in json.load(open(S+"/labelpage/items.json"))}
random.seed(int(sys.argv[1]) if len(sys.argv)>1 else 3); pick=[]
for hall in ["uznach_dietikon","leimental_arbon","horgen_moehlin","horgen_staefa","cottbus_seg","eisenach_wetzlar_2"]:
    pick+=random.sample([k for k in boxes if items[k]["hall"]==hall],1)
out=[]; COL={1:(0,200,255),2:(255,0,255)}
for k in pick:
    it=items[k]; t=cv2.imread(f"{S}/labelpage/t/{k}.jpg"); W=it["w"]; im=t[:,W:2*W].copy(); H=im.shape[0]
    crops=[]; bs=[b for b in boxes[k] if b[3]-b[1]>=24]
    for x1,y1,x2,y2,_ in bs:
        mx,my=.1*(x2-x1),.1*(y2-y1); c=im[max(0,int(y1-my)):int(y2+my),max(0,int(x1-mx)):int(x2+mx)]
        crops.append(cv2.resize(cv2.cvtColor(c,cv2.COLOR_BGR2RGB),(64,128)).astype(np.float32))
    if crops:
        with torch.no_grad(): p=torch.softmax(r((torch.from_numpy(np.stack(crops)).permute(0,3,1,2)-MEAN)/STD),1).numpy()
        for (x1,y1,x2,y2,_),pp in zip(bs,p):
            c=int(pp.argmax()); col=COL.get(c,(0,255,0)) if pp.max()>0.6 else (128,128,128)
            cv2.rectangle(im,(int(x1),int(y1)),(int(x2),int(y2)),col,2 if c else 1)
            if c: cv2.putText(im,"TW" if c==1 else "SR",(int(x1),int(y1)-3),cv2.FONT_HERSHEY_SIMPLEX,0.6,col,2)
    out.append(cv2.resize(im,(960,540)))
cv2.imwrite(S+"/roles/apply.jpg",np.vstack([np.hstack(out[i:i+2]) for i in range(0,6,2)]))
