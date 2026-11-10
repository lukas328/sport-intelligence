"""Build the Kaggle kernel of hardneg_gpu.py with the picks inserted.

    python ml/ball/kaggle/hardneg_push.py PICKS_JSON WORKDIR   # then: kaggle kernels push -p WORKDIR
"""
import json, sys
from pathlib import Path

here = Path(__file__).resolve().parent
picks = json.load(open(sys.argv[1])); work = Path(sys.argv[2]); work.mkdir(parents=True, exist_ok=True)
(work / "kaggle_hardneg.py").write_text((here / "hardneg_gpu.py").read_text().replace("__PICKS__", json.dumps(picks)))
meta = {"id": "lukasde1000/handball-ball-hardneg", "title": "handball ball hardneg", "code_file": "kaggle_hardneg.py",
        "language": "python", "kernel_type": "script", "is_private": True, "enable_gpu": True, "enable_internet": False,
        "dataset_sources": sorted({f"lukasde1000/{p['dataset']}" for p in picks} | {"lukasde1000/handball-ball-models"}),
        "competition_sources": [], "kernel_sources": []}
(work / "kernel-metadata.json").write_text(json.dumps(meta, indent=1))
print(work, len(picks), "picks", meta["dataset_sources"])
