# ml/

- `datasets/`: download and conversion scripts per dataset (M3+). Licences in `datasets/LICENSES.md`.
- `training/`: reproducible training per model (config files, seeds, data snapshots).
- `eval/`: evaluation harness `run.py`, benchmark `bench.py` (M3), golden-set manifest.
- `models/`: model cards (`*.md`). **No weights in git**; artefacts live in object storage and are registered as `ModelVersion`.

Every model used in production must be trained only on data whose licence allows commercial use (ADR 003).
