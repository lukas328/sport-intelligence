"""One row per mined tracklet: 6 peaks spread over it, centre frame cropped around the peak (64 px, x2).
usage: review3.py mined.json out.jpg start n"""
import sys,json,cv2,numpy as np
from collections import OrderedDict
items=json.load(open(sys.argv[1])); out=sys.argv[2]; s0,n=int(sys.argv[3]),int(sys.argv[4])
by=OrderedDict()
for it in items: by.setdefault(it["tracklet"],[]).append(it)
names=list(by)[s0:s0+n]; rows=[]
for k,tn in enumerate(names):
    its=by[tn]; pick=[its[int(i)] for i in np.linspace(0,len(its)-1,6)]
    row=np.full((148,6*132+60,3),255,np.uint8); cv2.putText(row,str(s0+k),(4,80),cv2.FONT_HERSHEY_SIMPLEX,0.7,(200,0,0),2)
    for j,it in enumerate(pick):
        t=cv2.imread("cand/"+it["file"])[:,192:384]; bx,by_=map(int,it["ball_in_tile"])
        pad=cv2.copyMakeBorder(t,32,32,32,32,cv2.BORDER_CONSTANT); c=cv2.resize(pad[by_:by_+64,bx:bx+64],(128,128),interpolation=cv2.INTER_CUBIC)
        cv2.circle(c,(64,64),18,(0,0,255),1); row[10:138,60+j*132:60+j*132+128]=c
    cv2.putText(row,f"{len(its)}",(4,120),cv2.FONT_HERSHEY_SIMPLEX,0.45,(0,0,0),1); rows.append(row)
cv2.imwrite(out,np.vstack(rows)); print(len(by),"tracklets")
