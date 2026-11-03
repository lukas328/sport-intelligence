# data/

Local data only. Nothing in here is committed except this README.

- `data/paper_reports/*.json`: paper match reports for `import_paper_reports` (BRIEF 15). Not committed by default because they contain player names; decide per club (see docs/OPEN_QUESTIONS.md).
- `data/videos/`: real test videos, downloaded from the shared bucket with `make testdata`. Never commit videos.

## Shared test videos (ADR 002, Q-DATA-1)

Real match videos live in a Cloudflare R2 bucket with EU jurisdiction (`handball-testdata`). The repo holds only `ml/eval/golden_set/manifest.json`: object key, checksum and metadata per video, no player names.

**Setup (once)**

1. Cloudflare dashboard → R2 → create bucket `handball-testdata`, location/jurisdiction **EU**.
2. *Manage R2 API Tokens*: one token **Object Read & Write** (owner, for uploads) and one **Object Read only** scoped to this bucket (CI, cloud agent sessions).
3. Set the environment (locally in `.env` or your shell; for cloud sessions in the environment settings, never in chat or git):

   ```
   TESTDATA_S3_ENDPOINT=https://<account-id>.eu.r2.cloudflarestorage.com
   TESTDATA_S3_ACCESS_KEY=...
   TESTDATA_S3_SECRET_KEY=...
   TESTDATA_S3_BUCKET=handball-testdata
   ```

   Cloud sessions additionally need `<account-id>.eu.r2.cloudflarestorage.com` under *Allowed domains*.
4. Check: `uv run python scripts/testdata.py check`

**Daily use**

```bash
make testdata                                              # download all videos to data/videos/
uv run python scripts/testdata.py list                     # what is in the bucket / manifest / local
uv run python scripts/testdata.py push match.mp4 --id 2026-10-12-u17-home \
    --camera fixed --camera-system Veo --level U17 --minors --consent club --score 28:25
```

`push` uploads the file, reads resolution, fps and duration with ffprobe and adds a manifest entry; commit the manifest afterwards. Uploading through the R2 dashboard also works, then add the manifest entry by hand (the `sha256` is needed for `pull`).

Ids describe the match, never people (`2026-10-12-u17-home`, not names). Only upload videos the club has agreed to share for testing; mark `--minors` when children are visible.

`make eval-real` runs the analysis health checks on every manifest video found in `data/videos/` (report in `docs/perf/eval-real.md`, debug images in `data/eval-real/`). Until the bucket exists, copy the files there by hand with the manifest id as file name (e.g. `data/videos/ch-nlb-2017-horgen-staefa.mp4`) (`eval-real` looks files up by that name).

To test the app itself with a real video, start the stack (`docker compose up -d`) and upload the file from `data/videos/` in the web UI; it is then stored in the local SeaweedFS bucket.
