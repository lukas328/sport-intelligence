"""Labelling grid for triplets: per cell the three frames cropped around the point (64 px, x2), index on top."""
import sys,json,cv2,numpy as np
items=json.load(open(sys.argv[1])); folder=sys.argv[2]; out=sys.argv[3]; start=int(sys.argv[4]); n=int(sys.argv[5]); key=sys.argv[6] if len(sys.argv)>6 else "ball"
cells=[]
for k,x in enumerate(items[start:start+n]):
    t=cv2.imread(f"{folder}/{x['file']}"); p=x.get(key) or x.get("ball_in_tile"); bx,by=int(p[0]),int(p[1]); r=32
    c=np.full((20+2*r*2,3*2*r*2+8,3),255,np.uint8)
    for j in range(3):
        f=t[:,192*j:192*(j+1)]; pad=cv2.copyMakeBorder(f,r,r,r,r,cv2.BORDER_CONSTANT,value=(0,0,0)); crop=pad[by:by+2*r,bx:bx+2*r]
        crop=cv2.resize(crop,(4*r,4*r),interpolation=cv2.INTER_CUBIC); cv2.circle(crop,(2*r,2*r),18,(0,0,255),1)
        c[20:,j*(4*r+4):j*(4*r+4)+4*r]=crop
    cv2.putText(c,f"{start+k}",(2,15),cv2.FONT_HERSHEY_SIMPLEX,0.5,(200,0,0),1); cells.append(c)
while len(cells)%4: cells.append(np.full_like(cells[0],255))
cv2.imwrite(out,np.vstack([np.hstack(cells[i:i+4]) for i in range(0,len(cells),4)]))
