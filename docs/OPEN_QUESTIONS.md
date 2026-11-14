# Open questions

Each question has the **assumption** I work with until it is answered. Status: open unless marked.

## Product and business
- **Q-PROD-1 Product name and domain.** "Handball AI" was very close to the competitor
  *handball.ai* named in the brief. *Decided 2026-11-12:* the product is called **Handball
  Intelligence**, logo «Taktik» (docs/design/brand2/taktik). *Open:* the domain
  (`handball-ai.ch` stays in config, mail addresses, deep links and the mobile bundle ids until a
  new domain is registered), the legal entity name on invoices (`Handball AI GmbH`), and a
  trademark search (Swissreg, EUIPO, classes 9, 41, 42).
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
- **Q-UX-7 Clash rule.** Since the Anlauf look (lib/color.ts `kit()`, ANLAUF.md): on the cloth
  the opponent changes to its second colour (then ink) when its hue is within 45 degrees of
  ours, or both are greys of similar lightness. On the tactics camera the opponents become grey
  rings only for the same colour family and a similar lightness (below 2.5:1); blue against red
  keeps both colours. *Assumption:* thresholds good enough; tune with real kits.
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
- **Q-UX-14 Dark scheme.** The Anlauf look has one light scheme (the cloth is the identity); the
  theme switch in the account menu was removed and the `hb_theme` cookie is ignored. Open: whether
  a dark scheme comes back (e.g. for the hall at night), and how the club colour and the cloth
  would work on it.
- **Q-UX-15 Ball and holder in the API.** `handball_vision.ballpossession` finds stretches where
  the ball is in the picture and who holds it, but the API does not consume it today. The tactics
  camera and the Ball-Linie have their place (`SceneCameraOut.ball`, a marker at the holder);
  until the analysis delivers it, `ball` is empty and the screen says «Ball in dieser Szene nicht
  erkannt». Lukas: UI first, detection later; no ball detection is built in phase 2.
- **Q-UX-16 Field detection in real halls.** The tactics camera needs a confirmed court
  (`field_confirmed`); without it the screen asks «Stimmt das Feld?». How well the automatic
  court fits in real club halls (lines of several sports, partial views, moving cameras) is
  untested and not improved in phase 2.
- **Q-UX-17 Runs and tactics camera with a real match video.** Runs (`goals[].run`, the
  scorer's track in the 3 s before the goal, sampled at about 9 per second) and scene positions
  are built from the tracking but only tested with stored test rows; the demo matches draw
  invented positions (`source: "demo"`). A test with a recorded match is open.
- **Q-UX-18 Smoothing of paths.** Runs are drawn with a Catmull-Rom curve through the measured
  points (display only, nothing added). Whether the raw tracks need filtering (jitter, ID
  switches) before they look like runs is open.
- **Q-UX-19 League table and rank.** Start (Tabelle), Saison (Rang in the Seitenkopf, Tabelle)
  and Nächster Gegner (three facts from the table) need the league table. Checked 2026-11-12:
  the handball.ch integration delivers it (`standing` in `GET /teams/{id}/official`, refreshed
  with the daily sync) once a team is linked to its official team; the Saison page shows rank
  and table from it. Not linked (DHB/HLA teams, teams without an official league, the demo
  club): no rank in the title («Fünf Spiele. Und rechts aussen bleibt offen.») and no table
  block. *Open:* a table for teams without a federation feed (entered by hand, or from the
  match reports of the whole group) is not planned; the demo club is not linked, so its
  screenshots show the page without a table.
- **Q-UX-20 Prüfen as questions.** Built 2026-11-12: the court first, then the goal candidates,
  then, once the court is confirmed, the own tracks without a name (longest in view first, at
  most six per video). The box around the person comes from the track's foot point and the court
  homography (`personBox` in lib/spotlight.ts: image scale at the feet, fixed body height
  1.85 m), shown as a crop of the running video. *Open:* the box is an estimate (only the ground
  plane is calibrated); a detector box per person would be exact. «Gegner» as an answer needs
  an API to mark a track as not ours; until then «Weiss nicht».

## UX test round 1, second delivery (2026-11-13)

- **Q-BILL-TRIAL Trial at sign-up (business rule, Lukas to confirm).** Checked 2026-11-13: with
  `billing_enforce` on, a new club started on Free (`analysis: false`, no `tracking`), so its
  first video was stored but never analysed, without a word; the 30 days of `trial_days` began
  only through Stripe checkout or `ops.extend_trial`. Built: creating a club starts the Team
  plan's trial from `packages/plans/plans.json` at once, without payment details
  (`services/orgs.py` `create_org`, switch `trial_on_signup` in `core/config.py`, default on;
  `trial_used` is set, so a later checkout starts no second trial). When it ends,
  `billing.effective_plan` falls back to Free; nothing is deleted. Test
  `test_billing.py::test_new_club_starts_the_trial_and_its_first_video_is_analysed`. *Open:*
  confirm the rule (trial without card for every new club) and the wording «30 Tage alles
  gratis. Danach entscheidest du.»
- **Q-AUTH-2b Two-factor reminder later (Lukas to confirm).** The obligation itself is unchanged
  (Q-AUTH-2). Only the reminder moved: no banner on every page; it appears once there is
  something to protect (a first video uploaded or a second person invited), as a quiet task on
  the team page and an entry with a dot in the account menu, dismissible for seven days.
- **Q-AUTH-OWNER Who does a team belong to? (Lukas to decide).** Saving a team from the public
  entry with one e-mail address makes that person its first administrator. That keeps the entry
  short, but a stranger could take a team before its real coach. A team that is already in the
  app is not handed over: saving sends an access request to its administrators. Options to check
  ownership: (a) «Das ist nicht dein Team?» with a hand-over by the support, (b) confirmation via
  the address the federation has on file for the team or club, (c) a second person of the club
  confirms. Built for now, the minimum only: on the «already in the app» answer a visible link
  «Dieses Team gehört mir, aber jemand anderes hat es schon» opens a prepared mail to the support
  (address from the configuration), next to the access request to the existing administrators.
  No new verification procedure.
- **Q-AUTH-LINK Sign-in link valid for a day (Lukas to confirm).** The e-mail link from the
  entry and from «Link schicken» was valid for 15 minutes; coaches read such mails hours later and
  then had to start over (UX test round 2, N15). Now 24 hours, still single use and void once
  used (setting `magic_link_ttl_minutes`). Trade-off: a mailbox someone else can read stays a way
  in for longer. Alternative if that is too long: a six-digit code next to the link.
- **Q-VIDEO-PARTS Two files for one match. Decided (2026-11-13), built on `claude/video-parts`.**
  A match has *parts* in a fixed order (usually the two halves; three or four when a phone splits
  the recording). The match timeline is the parts one after the other; every event, scene, goal
  candidate, possession, clip and throw-off time lies on it (`services/matches.parts_of`,
  `services/timeline.py`). Order: the camera clock in the file's metadata, else upload order
  (several files chosen at once go up in recording order); «Reihenfolge stimmt nicht? Tauschen»
  swaps without a new upload. *Way chosen: an offset per file, not joining the files before the
  analysis.* Each part is analysed on its own and its results are placed at the part's start, so a
  part added hours later analyses only itself, nothing is re-encoded or stored twice, and the
  court, the camera and a failure stay per part. For playback the API serves the first part's HLS
  playlists joined over all parts (segments of each file, a discontinuity between files): every
  player that plays the match video (Video tab, scenes, Prüfen, share links, the native app) plays
  across the break without a change. A change of the parts (added, deleted, failed, swapped) moves
  every match row with its part; the coach's answers are kept. The second half (second of two
  parts, or after a break of 5 min or more) tells the event baseline which side the home team
  defends (`side_hint`); its court tries the other part's confirmed court first and is asked in
  Prüfen only when it was not carried over, with «Ecken der 1. Halbzeit übernehmen». The second
  half's first throw-off opens half 2 of the match clock (`kickoff_ms["2"]`); without one Prüfen
  asks for it and starts the player at the second file. Existing matches with several files keep
  the first uploaded file at the start (migration 0044); their further files were never analysed
  into the match and show «noch nicht ausgewertet» with «Auswerten». Still open:
  - **Q-PARTS-MARKS** Courtside marks are synced with one offset per mark session; over a break
    that is not in any file, the marks of the second half are off by the break. A piecewise sync
    (one offset per part) is not built.
  - **Q-PARTS-OVERLAY** The workbench overlays (spotlight, mini court) read the first part's
    tracks; in the second half they show nothing instead of wrong positions. The tactics camera,
    the runs of the three things, shot positions and the physical load already read each part.
  - **Q-PARTS-RENDITIONS** Playback across files: since this change every ingested file gets a
    sound track (silent when it has none), and the player loads again at the same moment when a
    file does not continue cleanly at the break (hls.js media error, native error, a stall near a
    part start). Files ingested *before* without sound next to a file with sound, portrait next
    to landscape, and native Safari on an iPhone are untested here (no Apple device): Lukas'
    real test checks them. Reels and the presentation export cut each scene from its own file.
  - **Q-PARTS-ORDER-RERUN** After a swap the side hint of the part that is now second is not
    recomputed; «Erneut versuchen» on that part runs it with the new hint.

## UX test round 3 (2026-11-13)

- **Q-OLD-AREAS Areas from the earlier product (Lukas to decide).** Spielzüge (with its own play
  editor), the opponent profile with its manual player list, «Zum Zeigen» (presentations) and the
  old playlists still work and are reachable (Szenen side links, the match «Mehr» menu, their
  addresses). Since round 3 each says in one line that it comes from the earlier version and that
  new things come under Szenen and Spiele, and Spielzüge no longer shows the second tab row (UX
  test A07). Nothing was deleted. *Open:* rebuild them in the new look (plays on the tactics
  board, the opponent from the federation's data), fold them into Sammlungen, or retire them
  with a data export.

## Real-video test (2026-11-13, two NLB clips; docs/ux-test/echttest/BERICHT.md on the test branch)

Weaknesses of the recognition, recorded here and not fixed in the interface work (E01 to E12):

- **Q-REC-SCOREBOARD The hall's scoreboard is not read.** In clip 1 the board (8:7 to 11:11) is
  readable when the camera points left; the analysis finds no goal by itself.
- **Q-REC-CALQUALITY The court's quality is not measured.** `observe.py` sets the reprojection
  error to 0 and the confidence to 1.0, also for a court 2 to 5 m off; until it is measured the
  interface never treats the court as sure and always asks for it (done, E03).
- **Q-REC-SIDES The defended side flips.** In clip 2 the side the home team defends changes twice
  although the teams never swap; the team split at one moment counted 9, 2, 3 instead of 7, 6, 2.
- **Q-REC-CANDTIME Goal candidates come late.** Their times lie 4 to 7 s after the goal (the
  throw-off after it), so «the way before the goal» would show the way back.
- **Q-REC-CAMERA Tactics camera in a checked scene.** 8 red dots instead of 6, one referee instead
  of two, and the attack drawn on the left goal while the video shows the right one (the
  mirroring is gone since G3: the camera draws the half the video shows).
- **Q-REC-OPPKIT The team split needs both shirt colours.** `teams.relabel_by_clusters` labels
  the teams only with the home and the away kit; without the opponent's colour (no longer
  invented, E09) it labels nothing, so the interface asks for it before the upload. Open: a
  split by the two largest clusters that names only the own team.
- **Q-REC-PERSONBOX Person boxes with a panning camera.** The box needs the homography of each
  frame (camera motion times court); the worker has it (`motion.CameraMotion`) but does not hand
  it out, so person questions are asked only with a fixed camera (E05).
- **Q-REC-OFFCOURT People beside the court tracked as players.** Third real-video test: up to
  14 red dots instead of 7 (spectators in red behind the court, the bench in white in front), and
  goalkeepers in another colour. The interface now draws only positions on the court (1 m
  margin) and says under the camera that positions are estimated and may include people beside
  the court (G3). Open: separate players from spectators and bench in the recognition, and the
  goalkeeper's kit as its own class.

## Website (docs/site/KONZEPT.md, 2026-11-12)
- **Q-SITE-1 Prices on the website.** The site shows the plan table of `packages/plans`
  (CHF 0 / 39 / 199, yearly 10 monthly fees) with a visible line «Die Preise sind noch nicht
  endgültig» (Q-PROD-4). The goalkeeper add-on (CHF 7) is not shown: outside the core.
  *Open:* final prices, and whether «Gratis» (no automatic analysis) stays a plan.
- **Q-SITE-2 Analysis duration.** The site promises no time («die App schickt dir eine
  Nachricht»). The app's empty state says «Nach etwa 40 Minuten» (SPEC 7.13), the CPU path takes
  about twice the video length (Q-INFRA-1). *Open:* one number for both, once the GPU is decided.
- **Q-SITE-3 «Wer wir sind».** No text about the team exists; the page «Über uns und Kontakt»
  shows a placeholder. *Open:* text and whether to name people.
- **Q-SITE-4 Storage location stated as fact.** The site says «App und Datenbank auf Servern in
  der Schweiz, Videos in einem Speicher in der EU» (ADR 025, ADR 002). *Open:* confirm before
  launch; the providers are named in the privacy policy (Q-LEGAL-1).
- **Q-SITE-5 Public demo.** The app has no demo match at all (EINSTIEG.md on `claude/ux-test`).
  Without an account there is the invented match of the website (`apps/site/public/demo/match.json`,
  marked «Erfundenes Spiel»). *Open:* a public read-only demo in the app.
- **Q-SITE-6 Help guides outside the core.** Guides for training, tactics board, assistant,
  presentation, player feed, scouting report, roles and the statistics matrix stay reachable
  (the app links to them, `help-map.ts`) but are not listed and carry a note. *Open:* update
  `help-map.ts` in the app to the new screens, then delete these guides.
- **Q-SITE-7 Trial «30 Tage gratis».** `trial_days: 30` stands in `packages/plans` and
  `apps/api/src/handball_api/services/plans.py` (lines 55, 66), but a trial only starts through a
  Stripe checkout (`services/billing.py`, lines 285 to 286 and 328: `trial_period_days`) or a
  support action (`services/ops.py extend_trial`, lines 154 to 164); a new club gets none
  automatically. The site names «30 Tage gratis» only on the pricing page next to the plan, with
  «Die Preise sind noch nicht endgültig»; the start page just says «Kostenlos starten».
  *Update 2026-11-13:* the app now starts the trial for every new club (Q-BILL-TRIAL below);
  the site keeps «30 Tage» on the pricing page only until Lukas confirms the rule.
- **Q-SITE-8 Mail when the three things are ready.** The site says «Du bekommst eine Mail, wenn
  die drei Dinge da sind» again; the app session is building that mail and the bell on phones
  (2026-11-13). *Answered 2026-11-13:* mail built in the app and confirmed in the UX test.
- **Q-SITE-9 Team field and colour.** Answered: «Wie heisst dein Team?» sends a GET to
  `{NEXT_PUBLIC_APP_URL}/einstieg?q=…&farbe=…&lang=…`, «Kostenlos starten» to
  `/einstieg?farbe=…&lang=…`; `farbe` (blau, rot, gelb, schwarz, weiss, gruen, orange, violett)
  only once the visitor picked a colour. The app takes it over.
