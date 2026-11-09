"""2-second clips (1 s before to 1 s after the labelled frame), 1280 wide, H.264, no audio."""
from pathlib import Path as _P
ROOT=_P(__file__).resolve().parents[3]
import json,subprocess,sys,cv2
from pathlib import Path
P=Path(sys.argv[1]); R=Path(str(ROOT/"data/videos"))
for it in json.load(open(P/"items.json")):
    out=P/"v"/f"{it['id']}.mp4"
    if out.exists(): continue
    cap=cv2.VideoCapture(str(R/it["video"])); fps=cap.get(cv2.CAP_PROP_FPS); cap.release()
    t0=max(0.0,(it["frame"]-fps)/fps)
    subprocess.run(["ffmpeg","-v","error","-y","-ss",f"{t0:.4f}","-i",str(R/it["video"]),"-t","2.0","-an","-vf","scale=1280:-2","-c:v","libx264","-preset","medium","-crf","27","-pix_fmt","yuv420p","-movflags","+faststart","-threads","2",str(out)],check=True)
    it["clip_offset_s"]=round(it["frame"]/fps-t0,4)
print("ok")
