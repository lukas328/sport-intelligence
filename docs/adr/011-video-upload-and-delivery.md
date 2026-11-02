# 011. Video upload, processing and delivery

- Status: accepted
- Date: 2026-11-02

## Upload
- **Direct to storage**: the browser uploads S3 multipart parts with presigned URLs (1 h); the API only
  creates the upload, signs part URLs, lists parts and completes. Part size 16 MiB (5 MiB locally), grows
  automatically so files never exceed 10'000 parts; max 40 GB.
- **Resumable**: the client remembers the upload per file fingerprint (name, size, mtime, match, camera)
  in localStorage. On resume it lists stored parts (`GET .../parts`), re-uploads missing or truncated ones,
  4 in parallel with retries and fresh URLs on failure. Tested in Vitest and in Playwright (pause mid-upload,
  choose the same file again).
- Storage CORS (PUT/GET/HEAD, `ETag` exposed) is set by the bootstrap for the web origin. The CSP's
  `connect-src` gets the storage origin at runtime (`HB_S3_PUBLIC_URL`).
- **Link import**: `https` only, default port, no credentials, public IPs only; checked in the API and again in
  the worker on every redirect hop (SSRF). The worker streams to storage, then starts the normal ingest.

## Processing (pipeline stages 0 and 1)
- Worker job `handball_worker.ingest.run_ingest` (RQ queue `pipeline`): download, SHA-256, ffprobe,
  heuristic quality check, HLS, analysis proxy, poster, thumbnail sprite + WebVTT, upload.
- **ffmpeg**: static build copied from `mwader/static-ffmpeg:7.1` (pinned) instead of distro packages:
  small, reproducible, fewer CVEs, works behind restrictive networks.
- Progress goes to the API (`POST /internal/jobs/{id}`, shared secret, not exposed via the web origin) and is
  published on Redis (`match:{id}`); browsers follow it via Server-Sent Events. Callbacks are idempotent.

## Delivery
- **HLS** with fMP4 segments, 4 s, ladder 1080p + 720p (never upscaled), H.264 high profile, AAC 128 kbit/s,
  keyframes aligned to segments (frame-accurate seeking for analysis).
- Playlists and segments are served by the API with the same authorisation as the match (`.../media/...`),
  private caching. Originals and the analysis proxy are never served to browsers.
- hls.js (dynamic import, only on video pages) in Chrome/Firefox/Edge, native HLS in Safari and iOS.
- Clips are time windows on the HLS stream, never cut copies (BRIEF 6.2). Physical cuts only for downloads (M8).
- **Later (M9, with the hosting decision)**: CDN in front of the media endpoint with signed cookies, so
  segments do not pass through the API.
