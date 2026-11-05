"""Frames for the labelling page: centre frame plus t-G and t+G, 1280 wide JPEG."""
from pathlib import Path as _P
ROOT=_P(__file__).resolve().parents[3]
import cv2,json,random,sys
from pathlib import Path
out=Path(sys.argv[1]); R=Path(str(ROOT/"data/videos")); random.seed(11)
src=[("uznach_dietikon_s0",R/"segs/uznach_dietikon_s0.mp4",15),("uznach_dietikon_s2",R/"segs/uznach_dietikon_s2.mp4",15),
     ("uznach_dietikon_s3",R/"segs/uznach_dietikon_s3.mp4",15),("uznach_dietikon_s4",R/"segs/uznach_dietikon_s4.mp4",15),
     ("eisenach_wetzlar_2",R/"segs/eisenach_wetzlar_2.mp4",10),("leimental_arbon",R/"ch-spl2-2024-leimental-arbon.mp4",15),
     ("horgen_moehlin",R/"ch-nlb-2017-horgen-moehlin.mp4",15),("horgen_staefa",R/"ch-nlb-2017-horgen-staefa.mp4",15),
     ("cottbus_seg",R/"full/cb_seg_1080.mp4",15)]
items=[]
for name,path,n in src:
    cap=cv2.VideoCapture(str(path)); fps=cap.get(cv2.CAP_PROP_FPS); total=int(cap.get(cv2.CAP_PROP_FRAME_COUNT)); G=3 if fps>40 else 2
    picks=sorted(random.sample(range(int(fps*5),total-int(fps*5)),n))
    for fr in picks:
        cap.set(cv2.CAP_PROP_POS_FRAMES,fr-G); ims=[]
        for k in range(2*G+1):
            ok,f=cap.read()
            if not ok: break
            if k in (0,G,2*G): ims.append(f)
        if len(ims)<3: continue
        W0=ims[0].shape[1]; sc=1280/W0
        iid=f"{name}_{fr}"
        for tag,im in zip(("a","b","c"),ims):
            im=cv2.resize(im,(1280,round(im.shape[0]*sc)),interpolation=cv2.INTER_AREA)
            cv2.imwrite(str(out/"f"/f"{iid}_{tag}.jpg"),im,[cv2.IMWRITE_JPEG_QUALITY,80])
        items.append({"id":iid,"hall":name.rsplit("_s",1)[0] if name.startswith("uznach") else name,"video":str(path.relative_to(R)),"frame":fr,"gap":G,"scale":round(sc,5),"w":1280,"h":round(ims[0].shape[0]*sc)})
    print(name,fps,len(items),flush=True)
random.shuffle(items)
json.dump(items,open(out/"items.json","w"))
