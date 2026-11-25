"""Clips for the page "Abwürfe Dev" (ml/gold/labelling/release_dev.html, https://claude.ai/artifact/X1AUB2nXAkX9eVTV977paz):
one 12 s clip per dev shot of the official logs, 9 s before to 3 s after the logged time.
usage: uv run --project packages/vision python ml/gold/release_dev_clips.py SCRATCH  (SCRATCH holds devfeat.pkl from
ml/integration/shot_time_dev.py extract); writes SCRATCH/page/items.json and SCRATCH/cuts.txt, then cut with
ffmpeg -ss START -i SEG.mp4 -t DUR -an -vf scale=960:-2,fps=30 -c:v libx264 -crf 30."""
import pickle,json,subprocess,sys,os
sys.path.insert(0,'ml/goals'); import shot_eval as se
S=sys.argv[1]; D=pickle.load(open(f'{S}/devfeat.pkl','rb'))
KIND={'goal':'goal','penalty_goal':'goal','empty_goal':'goal','shot_saved':'save','penalty_saved':'save'}
os.makedirs(f'{S}/page/c',exist_ok=True)
items=[]; n=0
for seg in sorted(D):
    v=D[seg]
    for e in sorted(v['entries'],key=lambda e:e['t']):
        if e['kind'] not in se.SHOT+('empty_goal',): continue
        a=max(0.0,e['t']-9); b=min(v['duration'],e['t']+3)
        cid=f'{n:03d}'; n+=1
        items.append({'id':f'{seg}@{e["t"]:.1f}','seg':seg,'game':v['game'],'log_t':round(e['t'],2),'start':round(a,2),'dur':round(b-a,2),'kind':e['kind'],'out':KIND.get(e['kind'],'miss'),'video':f'c/{cid}.mp4'})
json.dump(items,open(f'{S}/page/items.json','w'))
print(len(items))
with open(f'{S}/cuts.txt','w') as f:
    for it in items: f.write(f"{it['seg']}.mp4 {it['start']} {it['dur']} {it['video']}\n")
