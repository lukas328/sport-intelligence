"""Build and push the Kaggle kernel of testset_gpu.py with the picks inserted.

    python ml/ball/kaggle/testset_push.py PICKS_JSON WORKDIR   # then: kaggle kernels push -p WORKDIR
"""
import json, sys
from pathlib import Path

here = Path(__file__).resolve().parent
picks = json.load(open(sys.argv[1])); work = Path(sys.argv[2]); work.mkdir(parents=True, exist_ok=True)
code = (here / "testset_gpu.py").read_text().replace("__PICKS__", json.dumps(picks))
(work / "kaggle_testset.py").write_text(code)
meta = {"id": "lukasde1000/handball-ball-testset2", "title": "handball ball testset2", "code_file": "kaggle_testset.py",
        "language": "python", "kernel_type": "script", "is_private": True, "enable_gpu": True, "enable_internet": True,
        "dataset_sources": sorted({f"lukasde1000/{p['dataset']}" for p in picks}),
        "competition_sources": [], "kernel_sources": []}
(work / "kernel-metadata.json").write_text(json.dumps(meta, indent=1))
print(work, len(picks), "picks", meta["dataset_sources"])
