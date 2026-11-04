"""Write labels from a triplet grid: python labels3.py list.json start n "pos idx" "skip idx" -> labels3.json"""
import sys,json
items=json.load(open(sys.argv[1])); s,n=int(sys.argv[2]),int(sys.argv[3])
pos=set(map(int,sys.argv[4].split(","))) if sys.argv[4] else set(); skip=set(map(int,sys.argv[5].split(","))) if len(sys.argv)>5 and sys.argv[5] else set()
try: lab=json.load(open("labels3.json"))
except FileNotFoundError: lab={}
for k in range(s,min(s+n,len(items))):
    if k in skip: continue
    lab[items[k]["file"]]=1 if k in pos else 0
json.dump(lab,open("labels3.json","w")); print(len(lab),"pos",sum(lab.values()))
