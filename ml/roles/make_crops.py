"""Person crops with roles (player / goalkeeper / referee) from Roboflow handball sets (CC BY 4.0).
Images stretched back to 16:9; box + 10 % margin, 64x128. Set 'collado' is held out as unseen halls."""
import glob,os,json,random,cv2,numpy as np
import sys; R=sys.argv[1]  # working folder with rf/<set> exports
ROLE={"chandan":{0:"goalkeeper",1:"player",2:"referee"},"spin":{1:"goalkeeper",2:"player",3:"referee"},
      "collado":{1:"goalkeeper",2:"player",3:"referee"},"custom":{1:"goalkeeper",2:"player",3:"goalkeeper",4:"player",5:"referee"},
      "gergely":{1:"referee",2:"player",3:"player"}}
random.seed(0); meta=[]
for s,cmap in ROLE.items():
    for lf in glob.glob(f"{R}/rf/{s}/*/labels/*.txt"):
        imgs=glob.glob(lf.replace("/labels/","/images/").rsplit(".",1)[0]+".*")
        if not imgs: continue
        im=cv2.imread(imgs[0]); im=cv2.resize(im,(1138,640)); H,W=im.shape[:2]
        for k,l in enumerate(open(lf)):
            p=l.split()
            if len(p)<5 or int(p[0]) not in cmap: continue
            cx,cy,bw,bh=[float(x) for x in p[1:5]]; x1,y1,x2,y2=(cx-bw/2)*W,(cy-bh/2)*H,(cx+bw/2)*W,(cy+bh/2)*H
            if y2-y1<24: continue
            mx,my=.1*(x2-x1),.1*(y2-y1); c=im[max(0,int(y1-my)):int(y2+my),max(0,int(x1-mx)):int(x2+mx)]
            if c.size==0: continue
            fn=f"{s}_{os.path.basename(lf)[:-4][:40]}_{k}.jpg"; cv2.imwrite(f"{R}/roles/crops/{fn}",cv2.resize(c,(64,128)),[cv2.IMWRITE_JPEG_QUALITY,92])
            meta.append({"file":fn,"role":cmap[int(p[0])],"set":s,"img":os.path.basename(lf),"split":"test" if s=="collado" else ("val" if random.random()<0.12 else "train")})
json.dump(meta,open(f"{R}/roles/meta.json","w"))
from collections import Counter; print(Counter((m["split"],m["role"]) for m in meta))
