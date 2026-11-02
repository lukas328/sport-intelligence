# data/

Local data only. Nothing in here is committed except this README.

- `data/paper_reports/*.json`: paper match reports for `import_paper_reports` (BRIEF 15). Not committed by default because they contain player names; decide per club (see docs/OPEN_QUESTIONS.md).
- Test videos: store them in object storage (local: `s3://videos` in docker compose) or in `data/videos/` locally. Never commit videos. For a shared test set use Git LFS or a bucket and keep only a manifest in `ml/eval/golden_set/manifest.json`.
