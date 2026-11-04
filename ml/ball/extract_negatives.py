import cv2,json,random,sys
from pathlib import Path
out=Path(sys.argv[1]); T=192; random.seed(1); meta=json.load(open(out/"meta_tt.json"))
vids={"staefa":"/home/user/handball-ai/data/videos/ch-nlb-2017-horgen-staefa.mp4","moehlin":"/home/user/handball-ai/data/videos/ch-nlb-2017-horgen-moehlin.mp4",
      "leimental":"/home/user/handball-ai/data/videos/ch-spl2-2024-leimental-arbon.mp4","cottbus":"/home/user/handball-ai/data/videos/full/cb_seg_1080.mp4"}
for name,p in vids.items():
    cap=cv2.VideoCapture(p); fps=cap.get(cv2.CAP_PROP_FPS); n=0; k=0
    while True:
        ok,f=cap.read()
        if not ok: break
        if n%int(fps*2)==0:
            H,W=f.shape[:2]
            for j in range(5):
                x0=random.randint(0,W-T); y0=random.randint(0,H-T); fn=f"our_{name}_{n}_{j}.jpg"
                cv2.imwrite(str(out/"img"/fn),f[y0:y0+T,x0:x0+T],[cv2.IMWRITE_JPEG_QUALITY,92])
                meta.append({"file":fn,"split":"train" if (n//int(fps*2))%5 else "val","ball":None,"src":name}); k+=1
        n+=1
    print(name,k,flush=True)
json.dump(meta,open(out/"meta.json","w")); print("total",len(meta),"pos",sum(m["ball"] is not None for m in meta))
