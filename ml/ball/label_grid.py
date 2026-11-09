import sys,json,random,cv2,numpy as np
from pathlib import Path
D=Path(sys.argv[1]); vid=sys.argv[2]; seed=int(sys.argv[3]); out=sys.argv[4]
c=json.load(open(D/f"cands_{vid}.json")); lab=json.load(open(D/"labels_ours.json")) if (D/"labels_ours.json").exists() else {}
c=[x for x in c if x["file"] not in lab]; random.seed(seed); c.sort(key=lambda x:-x["score"]); sel=c[:40]+random.sample(c[40:],min(20,max(0,len(c)-40)))
json.dump([x["file"] for x in sel],open(D/f"grid_{vid}_{seed}.json","w"))
S=96; img=np.full((5*S+20,12*S+20,3),255,np.uint8)
for k,x in enumerate(sel):
    t=cv2.imread(str(D/"cand"/x["file"])); bx,by=x["ball_in_tile"]; crop=np.zeros((48,48,3),np.uint8); p=t[max(0,by-24):by+24,max(0,bx-24):bx+24]; crop[:p.shape[0],:p.shape[1]]=p
    r,cc=divmod(k,12); im=cv2.resize(crop,(S-4,S-4),interpolation=cv2.INTER_NEAREST); cv2.circle(im,(S//2-2,S//2-2),12,(0,0,255),1); img[20+r*S:20+r*S+S-4,20+cc*S:20+cc*S+S-4]=im
for j in range(12): cv2.putText(img,str(j),(20+j*S+40,15),cv2.FONT_HERSHEY_SIMPLEX,0.5,(0,0,200),1)
for j in range(5): cv2.putText(img,str(j),(4,20+j*S+50),cv2.FONT_HERSHEY_SIMPLEX,0.5,(0,0,200),1)
cv2.imwrite(out,img); print(len(sel))
