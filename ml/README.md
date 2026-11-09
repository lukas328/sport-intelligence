# ml/

Everything around the models: data, research, evaluation and model cards. The product code that
runs the models lives in `packages/vision` (library) and `apps/gpu-worker` (jobs).

Licences: models in production must be trained only on data whose licence allows commercial use
(ADR 003). For the feasibility phase non-commercial data is accepted (docs/OPEN_QUESTIONS.md,
Q-ML-5 and Q-ML-6); anything trained on it is marked below and must be retrained or replaced
before a commercial launch.

## Folders

| Folder | What | Status |
|---|---|---|
| `models/` | Model cards of everything the product loads (detector, text OCR, ReID). No weights in git. | product |
| `data/` | Game video library: lists (`videos.csv`, `videos_next.csv`), ingest to Kaggle (`ingest_drive.py`, `local_ingest.py`), match clock per segment (`segment_clock.py`; `library.py` for the batches from the owner's computer), official data per game (`match_official.py`, `official/`, `catalog.json`), labels per segment (`segment_labels/`). Guide: `ANLEITUNG_DOWNLOAD.md`. | active |
| `eval/` | Evaluation harness and ground truth: `run.py`/`bench.py`, golden set, official logs for the test videos (`official/`, `align_official.py`, `fetch_handball_ch.py`, `fetch_dhb_report.py`), event clips. | active |
| `ball/` | Ball detector research: 3-frame heatmap net (rounds 1 to 5, Kaggle GPU in `kaggle/`), OWLv2 teacher, labelling pages, user benchmark. README has the benchmark table. | research, active |
| `goals/` | Goal moments from the picture; produced the shipped goal candidates (`goal_template.py` regenerates `packages/vision/.../data/goal_template.json`). | research, shipped |
| `roles/` | Player / goalkeeper / referee classifier from Roboflow sets (CC BY 4.0). | research, shipped (ADR 028) |
| `holder/` | "Does this player hold the ball?" classifier, v2 AUC 0.78. | research, on hold until better ball labels |
| `reid/` | Own ReID model trained on handball crops (rank-1 0.59 vs MSMT 0.74). | research, closed: MSMT model kept |
| `datasets/` | Dataset licences (`LICENSES.md`). | reference |
| `scripts/` | `export_reid.py` (ReID ONNX export, see `models/reid-fastreid.md`). | product tooling |

Research folders are excluded from ruff (pyproject `extend-exclude`) and are not imported by the
product. Results and decisions are in each folder's README and in docs/adr.

## Where things run
- Kaggle (account `lukasde1000`): private datasets `handball-segs-bNN` (cloud ingest) and
  `handball-segs-lNN` (ingest from the owner's computer), ball training data and models; GPU
  notebooks for training, mining and OWLv2 pseudo-labels (scripts in `ball/kaggle/`).
- Scratch work of the sessions is not in git; anything needed to reproduce a result is.
