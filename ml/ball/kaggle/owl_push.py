"""Build Kaggle kernels of owl_gpu.py for chosen segments (OWLv2 pseudo-labels on a free Kaggle GPU).

    python ml/ball/kaggle/owl_push.py SEL_JSON WORKDIR PARTS SLUG_PREFIX [BUDGET_H]
SEL_JSON: [[dataset, segment file], ...]. Writes WORKDIR/<prefix>-<i>/ per part; push each with
`kaggle kernels push -p <dir>`. The kernel's output segs/*.json is the input format of train_r6/r7.
"""
import json, sys
from pathlib import Path

here = Path(__file__).resolve().parent
sel = json.load(open(sys.argv[1])); work = Path(sys.argv[2]); parts = int(sys.argv[3]); prefix = sys.argv[4]
budget = sys.argv[5] if len(sys.argv) > 5 else "8.0"
code = (here / "owl_gpu.py").read_text()
for i in range(parts):
    chunk = sel[i::parts]; d = work / f"{prefix}-{i + 1}"; d.mkdir(parents=True, exist_ok=True)
    head = ("import os, json\nos.environ['OWL_ONLY_JSON'] = " + repr(json.dumps([f for _, f in chunk]))
            + f"\nos.environ.setdefault('OWL_BUDGET_H', '{budget}')\n")
    (d / "kaggle_owl.py").write_text(head + code)
    meta = {"id": f"lukasde1000/{prefix}-{i + 1}", "title": f"{prefix} {i + 1}", "code_file": "kaggle_owl.py",
            "language": "python", "kernel_type": "script", "is_private": True, "enable_gpu": True, "enable_internet": True,
            "dataset_sources": sorted({f"lukasde1000/{ds}" for ds, _ in chunk}), "competition_sources": [], "kernel_sources": []}
    (d / "kernel-metadata.json").write_text(json.dumps(meta, indent=1))
    print(d, len(chunk), "segments", meta["dataset_sources"])
