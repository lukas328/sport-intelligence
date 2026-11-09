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
if __name__=="__main__":
    import sys; m=build(sys.argv[1],sys.argv[2]); print(len(m))
