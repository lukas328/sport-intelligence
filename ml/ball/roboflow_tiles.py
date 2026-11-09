"""Roboflow handball sets (CC BY 4.0, YOLOv8 export, 640x640 stretched) -> triplet tiles.
Images are stretched back to 16:9 so the ball is round again; single images become still triplets
(same frame three times): they teach the ball's look, not its motion."""
import glob,os,random,cv2,numpy as np
SETS={"ballon":0,"xutbx":0,"collado":0,"custom":0,"h5":0}  # class id of the ball per set
def build(root,out,T=256,seed=0,neg_per_img=1):
    random.seed(seed); os.makedirs(out+"/img",exist_ok=True); meta=[]
    for name,cid in SETS.items():
        ys=glob.glob(f"{root}/**/{name}/data.yaml",recursive=True)
        if not ys: print("missing",name); continue
        base=os.path.dirname(ys[0])
        for lf in glob.glob(f"{base}/*/labels/*.txt"):
            split="val" if "/test/" in lf else "train"
            imgs=glob.glob(lf.replace("/labels/","/images/").rsplit(".",1)[0]+".*")
            if not imgs: continue
            im=cv2.imread(imgs[0])
            if im is None: continue
            im=cv2.resize(im,(1138,640)); H,W=im.shape[:2]
            balls=[]
            for l in open(lf):
                p=l.split()
                if len(p)>=5 and int(p[0])==cid:
                    cx,cy,bw,bh=map(float,p[1:5]); balls.append((cx*W,cy*H,max(bw*W,bh*H)))
            tag=f"rf_{name}_{os.path.basename(lf)[:-4][:40]}"
            for j,(bx,by,bs) in enumerate(balls):
                x0=int(np.clip(bx-random.uniform(30,T-30),0,W-T)); y0=int(np.clip(by-random.uniform(30,T-30),0,H-T)); t=im[y0:y0+T,x0:x0+T]
                fn=f"{tag}_p{j}.jpg"; cv2.imwrite(f"{out}/img/{fn}",cv2.hconcat([t,t,t]),[cv2.IMWRITE_JPEG_QUALITY,90])
                meta.append({"file":fn,"split":split,"ball":[bx-x0,by-y0,bs],"src":"roboflow_"+name,"tile":T,"root":out,"still":True})
            for j in range(neg_per_img):
                for _ in range(20):
                    x0=random.randint(0,W-T); y0=random.randint(0,H-T)
                    if all(not (x0-20<bx<x0+T+20 and y0-20<by<y0+T+20) for bx,by,_ in balls): break
                else: continue
                t=im[y0:y0+T,x0:x0+T]; fn=f"{tag}_n{j}.jpg"; cv2.imwrite(f"{out}/img/{fn}",cv2.hconcat([t,t,t]),[cv2.IMWRITE_JPEG_QUALITY,90])
                meta.append({"file":fn,"split":split,"ball":None,"src":"roboflow_"+name,"tile":T,"root":out,"still":True})
    return meta
if __name__=="__main__":
    import sys; m=build(sys.argv[1],sys.argv[2]); from collections import Counter; print(Counter((x["src"],x["ball"] is not None,x["split"]) for x in m))
