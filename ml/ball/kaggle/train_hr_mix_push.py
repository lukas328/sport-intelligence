"""Ball hr-mix (2026-11-26, plan docs/plans/ballnetz-ohne-deepsport.md step 1): hr-nods with the
human-checked labels weighted up.

hr-nods gave the batch share of DeepSport to the small own group (our_pos 44). The labels with the
best signal, the human-checked LLM points (D13) and the owner's peaks (D11), stayed at 12 of 132
positives per batch, fewer than the unchecked OWLv2 pseudo-labels (36) and the mined tracklets
(24). hr-mix: human_pos 12 -> 40, owl_pos 36 -> 20, mine_pos 24 -> 12 (positives stay 132,
negatives unchanged). Everything else as hr-nods: code, budget (9.5 h T4), augmentations,
exclusions (test set 2 games and their halls, the first test's halls).

With --no-teamtrack (the ablation of step 1): tt_pos and tt_neg 0, their shares to our_pos and
our_neg; the TeamTrack ball labels are legally open (OPEN_QUESTIONS 4c).

Decisions on a separate validation set of training-side games, never on ball test 2.

    kaggle kernels pull lukasde1000/handball-ml-hr-nods -p NODS -m
    python ml/ball/kaggle/train_hr_mix_push.py NODS WORKDIR [--no-teamtrack]
    kaggle kernels push -p WORKDIR
"""

import json
import sys
from pathlib import Path

nods, work = Path(sys.argv[1]), Path(sys.argv[2])
no_tt = "--no-teamtrack" in sys.argv
work.mkdir(parents=True, exist_ok=True)
src = (nods / "handball-ml-hr-nods.py").read_text()
old = (
    'MIX = {"tt_pos": 16, "our_pos": 44, "ds_pos": 0, "owl_pos": 36, "mine_pos": 24, "tt_neg": 8, '
    '"our_neg": 22, "ds_neg": 0, "owl_neg": 20, "mine_neg": 6, "hard_neg": 36, "human_pos": 12, '
    '"human_neg": 28}'
)
assert src.count(old) == 1, "mix anchor"
tt_pos, tt_neg, our_pos, our_neg = (0, 0, 60, 30) if no_tt else (16, 8, 44, 22)
new = (
    f'MIX = {{"tt_pos": {tt_pos}, "our_pos": {our_pos}, "ds_pos": 0, "owl_pos": 20, "mine_pos": 12, '
    f'"tt_neg": {tt_neg}, "our_neg": {our_neg}, "ds_neg": 0, "owl_neg": 20, "mine_neg": 6, '
    '"hard_neg": 36, "human_pos": 40, "human_neg": 28}'
)
src = src.replace(old, new)
name = "hrmixnott" if no_tt else "hrmix"
for a in (
    "ball_hrnods.pt",
    "hrnods_out.zip",
    "hrnods_stats.json",
    "hrnods_review_",
    "owl_tiles_hrnods.zip",
):
    src = src.replace(a, a.replace("hrnods", name))
src = f'"""Ball {name}: hr-nods with human labels weighted up (train_hr_mix_push.py)."""\n' + src
slug = "handball-ml-hr-mix-nott" if no_tt else "handball-ml-hr-mix"
(work / f"{slug}.py").write_text(src)
meta = json.loads((nods / "kernel-metadata.json").read_text())
meta.update(id=f"lukasde1000/{slug}", title=slug.replace("-", " "), code_file=f"{slug}.py")
meta.pop("id_no", None)
(work / "kernel-metadata.json").write_text(json.dumps(meta, indent=1))
print(work, slug, "written")
