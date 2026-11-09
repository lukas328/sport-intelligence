"""One game from Drive: 3 segments of 3 min; negative triplets (random tiles every 2 s) and the
ball net's top-3 peaks per second as triplets to label. The video is deleted afterwards."""
import sys,json,random,subprocess,cv2,numpy as np,onnxruntime as ort,os
from collections import deque
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
gid,name,out=sys.argv[1],sys.argv[2],Path(sys.argv[3]); model=sys.argv[4]
tmp=Path(f"{ROOT}/data/videos/full/{name}.mp4")
if not tmp.exists():
    import gdown; gdown.download(id=gid,output=str(tmp),quiet=True)
probe=subprocess.run(["ffprobe","-v","error","-select_streams","v:0","-show_entries","stream=r_frame_rate:format=duration","-of","json",str(tmp)],capture_output=True,text=True)
pj=json.loads(probe.stdout); a,b=pj["streams"][0]["r_frame_rate"].split("/"); fps=float(a)/float(b); dur=float(pj["format"]["duration"])
SEGS=Path(str(ROOT/"data/videos/segs")); SEGS.mkdir(exist_ok=True)
G=3 if fps>40 else 2; T=192; random.seed(hash(name)%1000)
so=ort.SessionOptions(); so.intra_op_num_threads=3; s=ort.InferenceSession(model,so,providers=["CPUExecutionProvider"])
meta=[]; cands=[]
for si,frac in enumerate((0.2,0.5,0.8)):
    seg=SEGS/f"{name}_{si}.mp4"
    start=int(dur*frac*fps)
    subprocess.run(["ffmpeg","-v","error","-y","-ss",f"{dur*frac:.2f}","-t","180","-i",str(tmp),"-an","-vf","scale='min(1920,iw)':-2","-c:v","libx264","-preset","veryfast","-crf","20",str(seg)],check=True)
    cap=cv2.VideoCapture(str(seg)); buf=deque(maxlen=2*G+1)
    for k in range(int(fps*180)):
        ok,f=cap.read()
        if not ok: break
        if f.shape[1]>1920: f=cv2.resize(f,(1920,round(f.shape[0]*1920/f.shape[1])))
        buf.append(f); n=start+k-G
        if len(buf)<2*G+1: continue
        H,W=f.shape[:2]
        def tile(x0,y0): return cv2.hconcat([buf[0][y0:y0+T,x0:x0+T],buf[G][y0:y0+T,x0:x0+T],buf[2*G][y0:y0+T,x0:x0+T]])
        if k%int(fps*2)==0:
            for j in range(4):
                x0=random.randint(0,W-T); y0=random.randint(0,H-T); fn=f"neg_{name}_{n}_{j}.jpg"
                cv2.imwrite(str(out/"img"/fn),tile(x0,y0),[cv2.IMWRITE_JPEG_QUALITY,90]); meta.append({"file":fn,"split":"train" if random.random()<.85 else "val","ball":None,"src":name})
        if k%int(fps)==0:
            c=buf[G]; h2,w2=H//32*32,W//32*32
            hm=1/(1+np.exp(-s.run(None,{"x":cv2.cvtColor(c[:h2,:w2],cv2.COLOR_BGR2RGB).transpose(2,0,1)[None].astype(np.float32)})[0][0,0]))
            for j in range(3):
                yx=np.unravel_index(hm.argmax(),hm.shape)
                if hm[yx]<0.15: break
                cx,cy=int(yx[1]*4+2),int(yx[0]*4+2); x0=int(np.clip(cx-96,0,W-T)); y0=int(np.clip(cy-96,0,H-T)); fn=f"cand_{name}_{n}_{j}.jpg"
                cv2.imwrite(str(out/"cand"/fn),tile(x0,y0),[cv2.IMWRITE_JPEG_QUALITY,90]); cands.append({"file":fn,"score":float(hm[yx]),"ball_in_tile":[cx-x0,cy-y0],"vid":name,"frame":n})
                hm[max(0,yx[0]-12):yx[0]+12,max(0,yx[1]-12):yx[1]+12]=0
json.dump(meta,open(out/f"meta_{name}.json","w")); json.dump(cands,open(out/f"cands_{name}.json","w"))
print(name,"fps",fps,"negatives",len(meta),"candidates",len(cands),flush=True)
os.remove(tmp)
