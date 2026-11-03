# Plan

## 1. Understanding
A multi-tenant SaaS for amateur and youth handball clubs (CH, DE first). A club uploads a match video,
the platform analyses it fully automatically within 30 to 60 minutes and delivers match report, clips,
statistics, recognised plays on an animated tactics board, and insights written in plain language with
video evidence. Every number links to the clips behind it. The tactics board works in both directions:
detected plays become boards, and a drawn play finds its instances in video.

Hard constraints: honest ML (heuristic/mock outputs are labelled via `source`), confidence on every
claim, privacy by design (minors, no face recognition, data in CH/EU), performance budget
(60 min video in ≤ 45 min on one L4 GPU, < CHF 2 per match), strong typing and tests.

## 2. Architecture
See `docs/ARCHITECTURE.md` and ADRs in `docs/adr/`.

## 3. Main risks and mitigations
| # | Risk | Impact | Mitigation |
|---|---|---|---|
| R1 | **ML accuracy on amateur footage** (poor light, low cameras, occlusion) misses targets in BRIEF 10.3 | Core promise | Golden set early (M3), heuristics with explicit `source`, confidence-weighted stats, "geschätzt" in UI, correction flywheel, quality check with filming tips |
| R2 | **Training data licences**: key public datasets are non-commercial | Legal | Data lineage per ModelVersion, partner-club data with consent as the production source, ADR 003 |
| R3 | **Shot outcome / score correctness** without ball tracking | Trust | Throw-off detection + scoreboard OCR + official feed + final-score constraint solver (M4) |
| R4 | **Jersey numbers** at amateur resolution | Player stats | Legibility classifier + full-res crops + track-level voting + roster constraints; fall back to team-level stats |
| R5 | **GPU cost/runtime** above budget | Margin | Cascade, batching, ONNX/TensorRT FP16, chunk parallelism, bench.py per milestone |
| R6 | **Minors' data** (youth teams) | Legal, reputation | Consent model per player, no identification without consent, deletion jobs with proof, DPA templates for legal review |
| R7 | **Scope size** (16 screens, 18 stages, billing, backoffice) | Timeline | Strict milestone order, vertical slices, demo data so UI work is not blocked by ML |
| R8 | **Naming/trademark**: "Handball AI" is close to the competitor handball.ai | Brand, legal | Working title only; final name in OPEN_QUESTIONS Q-PROD-1 |
| R9 | Real test videos not yet in the repo | M3+ validation | Pipeline built against synthetic clips first; real videos via bucket/LFS with manifest (see `data/README.md`) |

## 4. Tasks per milestone

### M0 Foundation ✅ (this milestone)
- [x] Monorepo (uv + pnpm workspaces), Makefile, pre-commit, CI (lint, types, tests, migrations, images + Trivy, compose E2E, preview stub)
- [x] API skeleton: config, structured logging, RFC 9457 errors, request id, health/readiness, DB base + RLS helper, Alembic baseline
- [x] Worker: RQ, pipeline graph + v1 stage declaration; GPU worker: `GpuBackend` with local backend
- [x] Court geometry single source (JSON → Python + TS)
- [x] Web: Next.js 15, i18n (de-CH/en/fr), dark mode tokens, status page, Vitest + Playwright + axe
- [x] Docker Compose for all services, ADRs 001 to 007, ARCHITECTURE, OPEN_QUESTIONS

### M1 Accounts, tenants, roster ✅ (see docs/progress/M1.md)
- Models + migrations: Organization, User, Team, Season, Player, RosterEntry, Membership, Consent, AuditLog, Invitation; RLS policies
- Auth: email + Argon2, magic link, sessions (httpOnly cookie), CSRF, TOTP for org_admin, invitations (signed token), rate limits
- Policy layer + policy test matrix (role × endpoint), cross-tenant test suite
- E-mail port (ADR: Postmark vs Resend), mailpit locally
- Web: auth pages, onboarding (club, logo, colours, team, roster form + CSV import, invites), settings skeleton, shadcn/ui setup
- `make seed` (demo club, 2 teams, roster), Playwright: onboarding under 5 minutes
### M2 Matches, upload, player ✅ (see docs/progress/M2.md)
- Match CRUD, opponents, kit colours; S3 multipart upload (resumable, presigned), link import port
- Ingest stage (ffprobe, checksum, HLS 720p/1080p, proxy, thumbnails), heuristic quality check with tips
- HLS player (hls.js + native Safari), timeline, playlists, comments, drawing tool, keyboard shortcuts; SSE job progress
- Acceptance: 2 GB upload with abort/resume; playback Chrome, Safari, iPhone (needs real device or cloud device lab, Q-QA-1)
### M3 Pipeline skeleton, calibration, detection, tracking ✅ (see docs/progress/M3.md)
- ProcessingJob state, orchestrator over PipelineGraph, checkpoints/caching, chunked processing
- Streaming decode (PyAV/decord, NVDEC in CUDA image), batching, ONNX Runtime/TensorRT FP16 from day one
- Stages 0 to 5; Dockerfile.cuda; `ml/eval/run.py` + `bench.py`; golden-set manifest; mini court in player (Arrow chunks)
### M4 Events and match report ✅ manual + import path, automatic events open (see docs/progress/M4.md)
- Pose (RTMPose), shot heuristic + EventSpotter interface, throw-off detection, final-score constraint, official feed CSV adapter, scoreboard OCR, possessions/phases baseline
- `packages/metrics` with DEFINITIONS.md, zones (`zones.py`, `zones.ts`), stats caches; analysis screen (overview, match report, shots), everything clickable; paper report importer
### M5 Identity, goal zones, goal cams ✅ manual identity, sync, goalkeeper module; OCR model and goal-zone model open (see docs/progress/M5.md)
- Jersey OCR + roster assignment (Hungarian with constraints), audio sync of goal cams, goal-zone model, goalkeeper module
### M6 Plays and tactics board ✅ board, library, templates, video to board, defence systems; play clustering open (see docs/progress/M6.md)
- Role assignment, action detection rules, DTW distance, HDBSCAN clustering, naming, defence formation
- Tactics editor (SVG, frames, animation, touch), video + board side by side, template search, play library, matchup matrix
### M7 Insights, season, opponents, training
- Insight engine (catalogue, Wilson/Beta tests, min samples, ranking), TextGenerator (Claude API) + number validator + template fallback
- Season stats, problem radar, opponent profile, drill library, assignments, notifications (in-app, e-mail, web push)
### M8 Billing, sharing, export, backoffice
- Stripe (checkout, portal, idempotent webhooks, trials), plan limits + usage, share links, PDF reports, operator backoffice + annotation tool
### M9 Hardening and go-live
- Load tests, security review (ASVS L2), privacy functions (export, deletion, consent), monitoring/alerting, backups + restore test, runbooks, GO_LIVE.md
