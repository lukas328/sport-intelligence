"""Sequences for path labelling: 3 s per clip, a keyframe every ~0.1 s (30 per clip), packed into one
6x5 sprite per clip (1280 wide frames), plus the ball net's top-3 peaks per keyframe as suggestions."""
from pathlib import Path as _P
ROOT=_P(__file__).resolve().parents[3]
import cv2,json,random,sys,numpy as np,onnxruntime as ort
from collections import deque
from pathlib import Path
out=Path(sys.argv[1]); model=sys.argv[2]; R=Path(str(ROOT/"data/videos")); random.seed(21)
so=ort.SessionOptions(); so.intra_op_num_threads=3; sess=ort.InferenceSession(model,so,providers=["CPUExecutionProvider"])
plan=[("uznach_dietikon","segs/uznach_dietikon_s0.mp4",1),("uznach_dietikon","segs/uznach_dietikon_s2.mp4",1),("uznach_dietikon","segs/uznach_dietikon_s3.mp4",1),("uznach_dietikon","segs/uznach_dietikon_s4.mp4",1),
      ("leimental_frauenfeld","segs/leimental_frauenfeld_0.mp4",1),("leimental_frauenfeld","segs/leimental_frauenfeld_2.mp4",1),
      ("muelheim_suedpfalz","segs/muelheim_suedpfalz_0.mp4",1),("muelheim_suedpfalz","segs/muelheim_suedpfalz_1.mp4",1),("muelheim_suedpfalz","segs/muelheim_suedpfalz_2.mp4",1),
      ("u20_sui_ger","segs/u20_sui_ger_0.mp4",1),("u20_sui_ger","segs/u20_sui_ger_2.mp4",1),("magdeburg_rostock","segs/magdeburg_rostock_0.mp4",2),
      ("eisenach_wetzlar","segs/eisenach_wetzlar_2.mp4",2),("horgen_moehlin","ch-nlb-2017-horgen-moehlin.mp4",2),("horgen_staefa","ch-nlb-2017-horgen-staefa.mp4",2),
      ("leimental_arbon","ch-spl2-2024-leimental-arbon.mp4",2),("cottbus_seg","full/cb_seg_1080.mp4",2)]
seqs=[]
for hall,rel,n in plan:
    cap=cv2.VideoCapture(str(R/rel)); fps=cap.get(cv2.CAP_PROP_FPS); total=int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total<fps*20: print("skip short",rel,total); continue
    step=max(1,round(fps/10)); G=3 if fps>40 else 2
    for _ in range(n):
        start=random.randint(int(fps*5),total-int(fps*8))
        cap.set(cv2.CAP_PROP_POS_FRAMES,start-G); frames={}
        for k in range(30*step+2*G+1):
            ok,f=cap.read()
            if not ok: break
            if f.shape[1]!=1280: f=cv2.resize(f,(1280,round(f.shape[0]*1280/f.shape[1])),interpolation=cv2.INTER_AREA)
            frames[start-G+k]=f
        keys=[start+i*step for i in range(30)]
        if any(k+G not in frames for k in keys): print("short read",rel); continue
        H=frames[keys[0]].shape[0]; sprite=np.zeros((H*5,1280*6,3),np.uint8); sugg=[]
        h2=H//32*32
        for i,k in enumerate(keys):
            r,c=divmod(i,6); sprite[r*H:(r+1)*H,c*1280:(c+1)*1280]=frames[k]
            x=np.concatenate([cv2.cvtColor(frames[k+d][:h2],cv2.COLOR_BGR2RGB) for d in (-G,0,G)],2).transpose(2,0,1)[None].astype(np.float32)
            hm=1/(1+np.exp(-sess.run(None,{"x":x})[0][0,0])); pk=[]
            for _ in range(3):
                yx=np.unravel_index(hm.argmax(),hm.shape)
                if hm[yx]<0.08: break
                pk.append([int(yx[1]*4+2),int(yx[0]*4+2),round(float(hm[yx]),2)]); hm[max(0,yx[0]-8):yx[0]+8,max(0,yx[1]-8):yx[1]+8]=0
            sugg.append(pk)
        sid=f"{Path(rel).stem.replace('-','_')}_{start}"
        cv2.imwrite(str(out/"s"/f"{sid}.jpg"),sprite,[cv2.IMWRITE_JPEG_QUALITY,72])
        seqs.append({"id":sid,"hall":hall,"video":rel,"fps":round(fps,3),"step":step,"gap":G,"frames":keys,"w":1280,"h":H,"cols":6,"sugg":sugg})
        print(sid,flush=True)
random.shuffle(seqs); json.dump(seqs,open(out/"seqs.json","w")); print(len(seqs),"sequences")
