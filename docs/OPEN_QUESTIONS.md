# Open questions

Each question has the **assumption** I work with until it is answered. Status: open unless marked.

## Product and business
- **Q-PROD-1 Product name and domain.** "Handball AI" is very close to the competitor *handball.ai*
  named in the brief (trademark and confusion risk). *Assumption:* working title only; no domain hard-coded
  (problem URIs use `urn:handball-platform:...`).
- **Q-PROD-2 Languages.** de-CH ("ss") first. Germany uses "ß". *Assumption:* v1 ships de-CH only, a de-DE
  variant can be added as a separate locale later.
- **Q-PROD-3 Company entity, VAT and currencies for Stripe** (CHF only, or CHF + EUR). *Assumption:* CHF and EUR prices in config.
- **Q-PROD-4 Prices** are placeholders from BRIEF 13.

## Data and test material
- **Q-DATA-1 Test videos** (you mentioned you have some). Needed per video: camera type (fixed / auto-follow,
  Veo, Spiideo, ...), resolution and fps, venue, whether goal cams exist, final score and scorers (ground
  truth), and **consent of the filmed players** (minors?). *Decided:* videos are never committed to
  git; they go to the R2 test-data bucket (ADR 002) via `scripts/testdata.py`, and the repo holds only
  `ml/eval/golden_set/manifest.json` (metadata, no player names). See `data/README.md`.
- **Q-DATA-2 Paper match report JSON schema and files** (BRIEF 15). *Assumption:* importer is built in M4
  once the schema is provided; files live in `data/paper_reports/` (gitignored by default, they contain names).
- **Q-DATA-3 Golden set annotation**: who annotates the 5 full matches, with which tool (CVAT, Label Studio,
  own backoffice tool from M8)? Budget?
- **Q-DATA-4 Customer data for training**: opt-in in the terms or separate consent (BRIEF 12)?
  *Assumption:* separate, explicit opt-in per organisation, off by default.
- **Q-DATA-5 handball.ch**: is there an official data access (API, export, partnership)? *Assumption:* stub
  adapter only, nothing is scraped (BRIEF 7.4).

## Accounts and roles (M1)
- **Q-AUTH-1 Google and Apple sign-in**: implemented (ADR 010). **Needs credentials**: a Google OAuth
  client (Google Cloud Console) and, for Apple, a paid Apple Developer account (Services ID + key).
  Without them the buttons stay hidden.
- **Q-AUTH-2 2FA for org admins**: enforced for org-level write actions after a 14-day grace period
  (configurable), so the 5-minute onboarding is not blocked. Is that acceptable, or must 2FA be set up
  during onboarding?
- **Q-ROLES-1 Players see the roster** (names, numbers, positions) of their team. Statistics visibility
  follows `players_see_team_stats` from M4. *Assumption:* roster is not sensitive within a team.
- **Q-ROLES-2 Coaches can invite** analysts, players and goalkeepers to their own team, and other
  coaches. Only org admins can invite org admins. Confirm.
- **Q-ROLES-3 Season** defaults to 1 July to 30 June and is created with the team. Other cut-offs needed
  (e.g. youth tournaments)?

## Infrastructure
- **Q-INFRA-1 Hosting provider.** *Answered 2026-11-03/04 (ADR 002), region updated 2026-11-09 (ADR 025):*
  EU is enough, cost first. Object storage: Cloudflare R2 with EU jurisdiction. App, Postgres, Redis,
  secrets and monitoring: Azure Container Apps and Postgres Flexible Server, Switzerland North. Still
  open: **GPU** (CPU workers first, about 2 x video length; later an EU/CH GPU provider with DPA).
  Owner checklists: `docs/LIVEGANG.md`, `docs/plans/produktion-checkliste.md`.
- **Q-INFRA-2 GitHub repository and org**, CI secrets, preview deploy target. *Assumption:* GitHub Actions,
  preview job disabled until hosting exists (`vars.PREVIEW_DEPLOY_ENABLED`).
- **Q-INFRA-3 E-mail provider** Postmark vs Resend (ADR in M1). *Assumption:* Postmark (EU data residency to verify).
  *Proposal 2026-11-04:* Azure Communication Services Email (data location Europe, SMTP), so mail stays on the
  chosen platform; needs the owner's confirmation (`docs/LIVEGANG.md`).
- **Q-INFRA-4 MinIO** no longer ships community images; local S3 is SeaweedFS (ADR 006). Answered, for information.
- **Q-INFRA-5 Next.js version**: the brief pins Next.js 15; Next.js 16 is current. *Assumption:* stay on 15.5.x
  as specified, upgrade in a dedicated step if wanted.

## ML and licences
- **Q-ML-1 Ultralytics Enterprise licence**: buy or not? *Assumption:* no; Apache-2.0 detectors in production (ADR 003).
- **Q-ML-2 Licences** of TeamTrack, UNIRI-HBD and the Roboflow set need a legal check for commercial
  training (recorded in `ml/datasets/LICENSES.md`).

- **Q-ML-3 Model and dataset access**: from this build environment Hugging Face, PyTorch downloads, Kaggle,
  Zenodo and Roboflow are blocked. *Assumption:* heuristic baselines now (ADR 012); trained models are added
  in an environment with access, through the ONNX detector and the model registry.

- **Q-ML-5 Re-identification model licence**: the FastReID weights are Apache-2.0 but trained on MSMT17
  (non-commercial research terms). *Decision (2026-11-04, product owner):* the risk is accepted for
  the current phase; the model may be used while we find out what works. Before a commercial launch:
  legal clearance or our own handball model trained on crops labelled through the shirt numbers.
- **Q-ML-6 Ball data**: TeamTrack (MIT), five Roboflow handball sets (CC BY 4.0), our own labels and
  DeepSport basketball (CC BY-NC-SA) are in use (ml/ball/README.md). *Decision (2026-11-04, product
  owner):* non-commercial data are fine for the feasibility phase; a shipped ball model needs a
  retraining without them (or a licence).
- **Q-ML-7 Target footage**: uploads are raw amateur recordings from any camera position (phones,
  club cameras, Veo and similar), rarely with a score overlay, not TV broadcasts. *Consequence:* the
  overlay reader stays a bonus; goals, possession and players must work from the picture alone.

## Legal and privacy
- **Q-LEGAL-1** Privacy policy, DPA (AVV) and terms need legal review (placeholders from M8/M9).
- **Q-LEGAL-2 Youth consent workflow**: do parents get their own account, or does the club upload signed
  consent? *Assumption:* club records consent per player (who, when, document reference); parent accounts later.
- **Q-LEGAL-3 Retention periods** for raw video vs. derived data. *Assumption:* configurable per organisation,
  default raw video 24 months.

## QA
- **Q-QA-1 iPhone/Safari acceptance** (M2) needs a real device or a device cloud (BrowserStack/Sauce Labs).
  Playwright WebKit covers the engine, not iOS.

## Q-ML-4 Validation of physical load (M5)
Distances, speeds and sprints come from single-camera tracking and are estimates. To calibrate the
smoothing and speed bands we need one match with a reference system (local positioning or GPS vests) or at
least a few measured sprints filmed from the club's usual camera position. **Default until then**: values are
shown with the "geschätzt" badge and no comparisons across matches with different camera positions.

## Q-BILL-1 Stripe account and prices
To run a real purchase in Stripe test mode we need a Stripe account (test keys), a webhook endpoint secret
and price ids for Team, Club and the goalkeeper add-on (CHF, monthly). **Default until then**: billing is
not enforced; the settings page shows the plans and explains that online payment is not set up.

## Addendum 01

### Q-ADD-1 Automatic events before launch (P1 vs. reality)
P1 ("Automatisch zuerst") and the P0 items highlights, player feed and scouting report need automatic
events. They need trained models and the club's real videos. **Default**: build A3 with heuristics on
tracking (throw-off, shot and goal candidates with confidence), measure on real matches, and keep the
manual and import paths as optional supplements. If the measured quality is too low, launch needs the
product owner's decision (launch with "assisted" events or postpone).

### Q-ADD-2 Live tagging already built with match clock
A courtside live mode (match clock, offline queue) exists since M9. Addendum 5.3 (M11) wants device time
and automatic sync to the video. **Default**: keep the current mode and extend it in M11; it stays
optional (P1).

### Q-ADD-3 VAT and invoicing
Clubs are often not VAT registered; our own VAT status and the rates for CH and EU customers need a
fiduciary/tax review. **Default**: VAT rate configurable, Stripe Tax for EU, QR bill with the legally
required fields, marked "rechtlich prüfen lassen".

### Q-ADD-4 Tools and providers needing a decision
Support chat (Crisp or Intercom), status page provider, PostHog (EU cloud or self-hosted), email series
sender. **Default**: Crisp, a hosted status page with API, PostHog EU cloud, the existing e-mail provider;
all behind adapters.

### Q-ADD-5 Legal templates
Terms section on video use, hall notice, consent texts per purpose, model-training opt-in, data portability
for players. Templates will be marked "rechtlich prüfen lassen" and listed here for review.
**Status A4**: drafts for review, each page shows a "draft, not yet legally reviewed" note:
`apps/site/content/legal/{de,fr,en}/agb.mdx` (incl. the video-use section and training opt-in),
`datenschutz.mdx` (sub-processors only as categories until Q-INFRA-1 and Q-ADD-4 are decided),
`impressum.mdx`; the hall notice is on `/{locale}/aufnahme/`. Missing: the operating company's name,
address and UID (build variables `NEXT_PUBLIC_COMPANY_*`; until set the imprint says the details follow),
the DPA template for clubs and the processing records (GO_LIVE.md).

### Q-ADD-6 Test material for the addendum
Spotlight (95 % on the golden set), multi-angle sync (< 2 frames), portrait crop (90 %), special cases
(several files, tournaments, side change, similar kits, training) and the 10 paper sheets for 5.9 each
need real or synthetic test material. **Default**: extend the synthetic generator where possible; real
material from the club's uploads.

### Q-ADD-7 Child turns 18
A guardianship keeps existing when the child becomes an adult; from then on the player decides
(self-consent is accepted, parent consent is no longer required). **Default**: keep the parent's earlier
consents valid until the player changes them and show the player a reminder on the consent page (A4).
Needs a legal check whether consents given by parents must be renewed at 18 ("rechtlich prüfen lassen").

### Q-ADD-8 Real footage for the golden set: network access
Suitable open material exists: TeamTrack (handball full-pitch videos with tracking annotations,
Kaggle or Google Drive; dataset licence to be confirmed), UWB amateur women positions and
possession (Zenodo 12065335, CC BY 4.0), EIGD-H and the Roboflow handball set (non-commercial,
evaluation only). This environment's network policy blocks kaggle.com, drive.google.com,
zenodo.org, figshare.com, huggingface.co and archive.org. **Needed**: allow these hosts in the cloud
environment settings (Network access, Allowed domains) or provide the files; then the golden set and
`ml/eval/events.py` run on real matches. YouTube videos are not downloaded (terms of use, ADR 018).


### Q-M10-1 Data assistant: live evaluation needs a model key
The 62-question evaluation set runs in CI with a scripted model (tools, validator, logging; ADR 021).
The acceptance criteria of 5.1 for the model itself (90 % correct, p95 under 8 s) can only be measured
with a key: `HB_ANTHROPIC_API_KEY=... uv run pytest -m live apps/api/tests/test_assistant.py`
(writes `docs/perf/assistant-eval.md`, about 62 questions times a few cents). **Default**: the
assistant is off without a key (503 "not set up"); run the live evaluation before enabling it.

### Q-M10-2 Sportscode compatibility check
The export follows the public Sportscode XML layout (instances with ID, start, end, code, labels;
rows with RGB) and round-trips losslessly through our import (tested). Opening the file in Sportscode
itself needs a licence. **Default**: ask a club with Sportscode to open one export before launch.

### Q-M11-1 Paper sheets test set
The acceptance of 5.9 (95 % of number fields correct on 10 real sheets) needs 10 photos of real
match sheets with their true values (`ml/eval/paper_sheets/<name>.jpg` + `<name>.json` in the
extraction schema) and a model key; then `pytest -m live apps/api/tests/test_paper_vision.py`.
**Default**: the feature stays off without a key; review before import is always required.

### Q-M11-2 Device measurements
Cold start under 2 s (5.5) and a 70-minute recording without interruption (5.2) need device builds on
a mid-range iPhone and Android phone. **Default**: measure with the first internal build, record in
the M11 report.

### Q-M11-3 Store accounts and push credentials
Apple Developer and Google Play accounts of the operating company, an Expo (EAS) project id
(`app.json` extra.eas.projectId), APNs key and FCM credentials, the domain for app links
(`app.handball-ai.ch`, apple-app-site-association and assetlinks.json on the web server).
**Default**: prepared in `apps/mobile` (bundle id `ch.handballai.app`); submission once accounts exist.

### Q-UX-1 Usability test with real coaches, players and parents
The redesign (ADR 023) follows the jobs and roles in the brief and was checked with screenshots,
Playwright flows and axe, not with people. **Default**: five short sessions (two coaches, two
players, one parent) on a phone and a laptop before launch; tasks: find the next match, upload a
video, open the scenes behind a number, reply to a training, change the club colour.

### Q-UX-2 Typeface in the Expo app
The app uses the new colours; Archivo is not yet bundled in the Expo build (system font).
**Default**: add it with `expo-font` together with the first device build (Q-M11-3).

## Redesign phase 1 (ADR 029, 2026-11-10)
- **Q-UX-1 ADR number.** The brief asked for "ADR 025"; 025 to 028 exist. *Assumption:* ADR 029.
- **Q-UX-2 Matrix and data assistant.** SPEC routes both into Szenen. *Assumption:* until the
  search field answers questions itself they stay as pages: the matrix is the tab "Tabelle",
  the assistant a page under Szenen (palette "Suchen: …").
- **Q-UX-3 Video tab tools.** The match workspace keeps its tool tabs (comments, scenes,
  drawings) and step rail inside Video. *Assumption:* removed with the new look in phase 2.
- **Q-UX-4 Spieltag.** One address (`matches/[m]/matchday`) for both existing levels: score and
  team events by default, quick marks with `?mode=marks`. *Assumption:* merged into one screen
  (SPEC 7.11) in phase 2.
- **Q-UX-5 Prüfen.** `matches/[m]/check` opens the existing full-screen review (goals, then
  shots). *Assumption:* the question-by-question screen (SPEC 7.5) comes in phase 2.
- **Q-UX-6 Opponent colour from "Spiel anlegen".** The form now sends the opponent's shirt
  colour only when somebody picked it; a match created through the API with an explicit
  `kit_opponent` counts as said. *Assumption:* that is the meaning of "aus den Trikotfarben des
  Spiels".
- **Q-UX-7 Clash rule.** "Same hue family and similar lightness" is implemented with the
  measure of the existing kit warnings (CIE76 delta E < 25). *Assumption:* good enough; tune with
  real kits.
- **Q-UX-8 Goals conceded by position.** Positions come from the shot zones (wings, backs incl.
  half distance, circle); 7 m, fast breaks, empty goal and long range have none.
- **Q-UX-9 Season themes.** A theme repeats in at least two matches with video; positions count
  from six goals against and a share of 30 %. Values for themes without a clear figure stay empty.
- **Q-UX-10 Consent link.** One link per team, 90 days, players listed as number, first name and
  initial. *Assumption:* an adult player or a parent may answer for any player of the team; abuse
  is limited by the link being in the team chat, rate limits and the audit log.
- **Q-UX-11 Sammlungen of the old kinds** are read-only through the collections API (changed on
  their old pages). *Assumption:* no data migration; a coach who edits one creates a collection.
- **Q-UX-12 Onboarding in two steps** (SPEC 7.12) and the onboarding e-mail "Deine Spieler
  mitnehmen" (invites players, which is behind Teamfunktionen now) are left for phase 2.
- **Q-UX-13 Share a single scene.** The API and the shared page support it; a share button per
  scene comes with the Video tab in phase 2.
