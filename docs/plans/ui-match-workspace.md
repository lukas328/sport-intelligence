# Handover: UI rework, starting with the match workspace

For a new session that reworks the web app's UI. Written by the video-analysis session
(branch `vision/real-footage`, PR 3) on 2026-11-05.

## The situation
The video analysis grew a lot (detection, calibration, goals, official reports, shirt numbers,
goal candidates). Its UI was added panel by panel by an engineering session: it works, is
accessible (axe clean, keyboard, i18n de-CH/en/fr) and tested, but the owner finds it looks
"generated". The task: make the app feel designed and coherent, without losing what the
analysis needs. The analysis session keeps working on the analysis and the API and no longer edits
`apps/web`; new analysis results arrive as API fields plus a short note on how they should show.

## Base and process
- Branch from `identity/halle` after PR 3 (`vision/real-footage` -> `identity/halle`) is merged,
  so the identity "Die Halle" (PR 2) and all analysis UI are on one base. If PR 3 is not merged
  yet, ask the owner first.
- Design source of truth: `docs/design/identity/` (IDENTITY_BLUEPRINT, DECISIONS, FOR_LUKAS,
  screens), `docs/DESIGN.md`, the design-system components and tokens in `apps/web`.
- Rules that stay: de-CH with "ss" (never "ß") and no long dashes in UI text; every string in
  `apps/web/messages/de-CH.json`, `en.json`, `fr.json`; OFL fonts; WCAG 2.2 AA; max 4 destinations
  per role in the navigation; no invented people or generated images.
- Commit author `Claude <noreply@anthropic.com>`; no merge to `main`, no deploy.

## Free to change
Look, layout, hierarchy, wording, how panels are grouped or split into tabs, colours within the
identity, motion. The current match workspace is a long vertical stack of cards
(`apps/web/src/app/app/[orgId]/matches/[matchId]/`: `match-view.tsx`, `workspace.tsx`,
`analysis-views.tsx`, `official-goals.tsx`, `goal-candidates.tsx`, `official-report.tsx`,
`upload-panel.tsx`, `video-overview.tsx`, `exchange-panel.tsx`, `marks-panel.tsx`, ...). Rethink it.

## Must keep (the analysis depends on these)
Behaviour and data flows, not looks. Each item names the API it uses.

1. **Upload and processing**: multipart upload (`POST /videos/{id}/parts`, `.../complete`),
   processing state with steps and remaining time (`GET /videos/{id}/analysis`), reprocess
   (`POST /videos/{id}/reprocess`). Uploads can be long (full games, 1 to 2 GB).
2. **Court calibration**: automatic court shown for confirmation ("Passt so",
   `POST /videos/{id}/calibration/confirm`); when the view is too flat the analysis stops with a
   reason and asks for four clicked goal-post feet (`POST /videos/{id}/calibration`). Without a
   calibrated court there are no tracks, possession or positions, so this step must stay
   prominent while it is open.
3. **Match clock and throw-off**: setting the throw-off times (`PUT /matches/{id}/kickoff`) maps
   match time to video time; official goals, candidates and the event list depend on it.
4. **Kits**: the four team kits plus the optional referee kit on create and edit
   (`kit_referee`, migration 0030) with the similarity hint. Colours are usually entered after
   the game; the hint explains the effect on the analysis, it does not ask to change shirts.
5. **Official match report**: import from handball.ch or DHB by link (`POST
   /matches/{id}/official-report`) and the comparison of official goals with the video
   (`GET .../official-report/comparison`, `PUT .../official-report/review`): jump to the goal,
   confirm or dismiss, undo; goals outside the video (status `outside`, `counts.outside`) are
   hidden by default; goals without a video time cannot be checked.
6. **Goal candidates**: list of likely goal moments (`GET /matches/{id}/goal-candidates`,
   `PUT .../goal-candidates/{cid}/review`), with:
   - a 1 / 2 / 4 per minute switch (each candidate carries the lowest rate that proposes it, so
     switching needs no re-run);
   - a short clip per candidate (about 10 s before to 4 s after the peak);
   - confirm for team A or B, reject, undo; rejects must stay stored (hard negatives for training);
   - fast keyboard review (today: ↑/↓, Enter, 1/2, X, U), reviews applied in click order.
   Reviewing a whole game must take minutes, not more: keep it fast, focus moving to the next row.
7. **Events and corrections**: the event list with source and confidence (overlay, hall board,
   official, candidate, manual), editing any event (`PATCH /events/{id}`), manual tagging and
   courtside marks import; manual entries always win over automatic ones.
8. **Players and numbers**: assigning tracks to players ("Spuren zuordnen"), the roster that the
   shirt-number vote uses, per-player stats from it. Shirt numbers are read automatically but not
   for every player; the coach must be able to fix or add an assignment.
9. **Analysis results**: possession share and timeline, attacks list with filters (own, opponent,
   fast breaks; `GET /matches/{id}/possessions`), physical load (`GET .../physical`), stats and
   insights, shot export.
10. **Collaboration**: comments at a video time, clips, drawings, playlists.

## Known UX problems to solve
- Jumping to a goal or candidate scrolls the page up to the video and the list leaves the screen:
  consider a sticky or docked player, or a small player beside the list.
- With a short clip, "Offizielle Tore 53" next to "Im Video gefunden 4" looks alarming although
  most goals are simply outside the clip; counts should be read against what the video covers.
- Second-half goals of a video that covers only part of the game show as "missing" without a
  video time.
- Many separate cards, each with its own counts, filters and wording; no clear order of work for
  a coach (upload, check court, confirm goals, assign players, read the analysis).
- Names: shown as "#7 Lisa Zimmerli"; keep one format everywhere (`lib/player-name.ts`).
- Dev-only: next-intl `ENVIRONMENT_FALLBACK` from `NotificationBell` (`relativeTime` without `now`).

## How to run it with real data
- Local stack: `make install`, `make up`, `make migrate`, `make seed` (demo club with synthetic
  videos). For the analysis panels a match needs a real video, an imported official report and goal
  candidates. The analysis session seeded such a match in its own dev database (HSG Leimental vs
  HC Arbon, real 5-minute clip `data/videos/ch-spl2-2024-leimental-arbon.mp4` from `make
  testdata`); its seed script can be committed on request.
- A 66-second screen recording and screenshots of the current panels exist (ask the owner).

## Where the analysis goes next (so the UI can plan for it)
- Ball position and possession per player once the ball detector is good enough (today: per team).
- Shots with position and outcome from the official logs plus the video.
- More automatic shirt numbers; per-player timelines and clips.
- Full games (60 to 120 minutes) as the normal case, not 5-minute clips.

## API additions from the analysis session
Shot candidates (2026-11-05): the same one-click review as the goal candidates, for every shot
(goal, save, miss, post, blocked), with the official report's entry suggested so one key confirms.
Both kinds live in the goal-candidate table and share the review endpoint.
- `GET /v1/orgs/{org}/matches/{id}/shot-candidates` (same as `goal-candidates?kind=shot`; the plain
  `goal-candidates` still returns the goal candidates, unchanged apart from new fields). Response:
  `kind`, `template`, `rates` (shots: `[2, 4, 6]` per minute), `default_rate` (shots: 4), `counts`
  (new: `suggested` = open candidates with a report suggestion), `candidates`, and `official`
  (null without a report): `{counts: {total, confirmed, suggested, missing, outside}, shots: [...]}`,
  every shot of the report with `status` confirmed (its video time is known: confirmed on a
  candidate, or a goal read from the overlay), suggested (an open candidate suggests it, see
  `candidate_id`), outside (its time lies before or after the video) or missing (no candidate near
  it: the coach can still tag it by hand at `t_ms`).
- New fields on every candidate row: `kind` ("goal" | "shot"), `outcome` (confirmed outcome),
  `suggestion` (open shot candidates only, else null): the report entry at this moment,
  `{event_id, side, outcome, penalty, number, player_id, name, period, clock_s, official_time,
  t_ms, uncertainty_ms}`. `known` (a stored shot already at this moment) gained `outcome`; for shot
  candidates it is any shot with a known video time within 8 s (tagged, courtside mark, confirmed
  candidate, overlay goal), never a report entry whose time only comes from the clock (that is a
  suggestion instead). Shot candidate clips run from 8 s before to 4 s after the peak; `goal_ms` is
  the estimated shot time.
- Report rows (`suggestion`, `official.shots`) carry `t_ms` from the match clock map: the overlay
  clock of the analysis where it was read (`uncertainty_ms` 0), else counted from the nearest
  anchor (throw-off, an entry already confirmed on video); `uncertainty_ms` is the clock stop
  between the anchors around it, null when unknown. Every confirmation adds an anchor, so the
  suggestions get better while the coach works through the list.
- `PUT .../goal-candidates/{candidate_id}/review` body, all optional apart from `status`:
  `status` ("confirmed" | "rejected" | null to undo), `side`, `outcome` ("goal" | "save" | "miss" |
  "post" | "blocked"; goal candidates default to "goal", so the old body still works),
  `official_event_id` (pin this report entry), `number`, `player_id` (shooter when there is no
  report entry). One key: `{"status": "confirmed"}` on a shot candidate with a suggestion confirms
  that entry: no second event is made, the report entry (with its player) takes the candidate's
  video time (`attributes.video.source` "goal_candidate") and the row's `event_id` points to it.
  Without a suggestion `side` and `outcome` are required (422 `invalid-side`, `invalid-outcome`);
  a side or outcome that contradicts the pinned entry gives 422 `official-differs` (then send
  `side`/`outcome` without `official_event_id` to record the coach's own shot). 409
  `already-a-goal` when the moment is already a known shot. Undo or reject removes the candidate's
  own event or moves the report entry back to its clock time. A re-import of the report keeps
  confirmed video times, and saves or misses confirmed before the import are taken over by the
  report entry (the candidate follows it).
- A confirmed save or miss also covers a goal candidate at the same moment (`known`), so the two
  lists do not ask twice. Suggested UI: one "Shots" review list next to "Goals"; with a report,
  show the suggestion (player, outcome, official time) and confirm with Enter, reject with X; a
  filter "only with a report entry" turns 4 candidates per minute into roughly the logged shots.

Real footage audit (2026-11-05): fixes for full games, clips from mid-half, several files.
- Match clock without overlay for a video that starts after the throw-off: `PUT
  .../kickoff` takes an optional `clock_s`, the match clock shown at `t_ms` (any moment of that
  half). The throw-off is then stored before the video (a negative `kickoff_ms`). Suggested UI:
  besides "Anpfiff jetzt", "Spieluhr zeigt hier [mm:ss]" for the paused moment; 422
  `invalid-clock` when the time is not in that half.
- Timeline video: event and clip times refer to the match's first main video (upload order,
  failed uploads left out), the one the workspace already plays (`videos.find(main && ready)`).
  A second main file (second half, a split recording) gets its own tracks and court, but its
  analysis no longer changes the match's events, possessions, throw-off times, scenes or reels;
  its `analysis.auto_events` stays null. The UI could say "Ereignisse aus der ersten Datei".
- Events before or after the video (official report on a clip): search hits keep `t_ms` but have
  `start_ms`/`end_ms` null (no moment to show: do not offer "add to playlist / presentation");
  Sportscode export, focus playlists, scouting and assistant clips leave them out. Clip windows
  end at the video's end.
- A clip slide (`clip_id`) of a match without video gives 422 `no-video`; a clip of another team
  404.
- Re-analysis (court points clicked, reprocess): the coach's comparison check (confirmed or
  dismissed) of an overlay or estimated goal moves to the new row at the same moment, and
  automatic rows the coach deleted or changed are not created again. Clicked court points are
  kept with the video: reprocess and retries use them, so a flat view does not ask again.

Clubs and teams from the official data (2026-11-05, docs/plans/federation-onboarding.md phases 1
to 3, Switzerland via handball.ch). Errors are problem codes; handball.ch down gives 503
`official-unavailable` (try later). All new endpoints are in the api-client.
- Onboarding flow, step 1 "Mannschaft suchen" (signed in, no club needed):
  `GET /v1/official/teams?q=thalwil` (at least 3 letters, else 422 `query-too-short`; 30 per
  minute). Hits: `official_id`, `name` (official team name, e.g. "TV Thalwil 2"), `league`
  ("Männer 2. Liga"), `league_short`, `group_name`, `season_id`, `club {id, name, city}`,
  `registered_club_id`, `status` ("available" | "claimed" | "member"), `team_id` (set when the team
  is in the app: players use it for a join request), `organization_id` (only when "member").
  Suggested UI: group the hits by club, show league per team; "available" offers "Übernehmen",
  "claimed" offers "Zugang anfragen" (coach) and "Beitreten" (player), "member" opens the team.
- Step 2 "Übernehmen": `POST /v1/official/teams/{official_id}/claim` body `{club_id, team_name?,
  org_id?, message?}` (`club_id` = the hit's `club.id`; `org_id` links a club the user already
  administers instead of creating one; `message` goes with an access request). Answers:
  201 `{status: "claimed", organization_id, team_id, created_organization, verification,
  prefill: {matches_created, results, roster_suggestions, report_suggestions, other_suggestions}}`,
  202 `{status: "access_requested", access_request_id}` (club or team already in the app: its
  admins decide), 200 `{status: "already_member", organization_id, team_id}`. After 201 the team
  has the season schedule as matches (opponent, home/away, venue, `source` "official"), results of
  played games, and suggestions. Suggested UI: a short "Wir haben X Spiele, Y Spieler und Z
  Spielberichte gefunden" screen leading to the roster confirmation.
- Step 3 "Kader bestätigen" and the suggestion inbox (coach, team manager, club admin; 403 for
  others): `GET /v1/orgs/{org}/teams/{team}/official/suggestions?status=open&kind=` returns
  `{id, kind, status, payload, created_at, resolved_at}`. Kinds and payload:
  `roster_add` {official_player_id, first_name, last_name, jersey_number, appearances};
  `roster_number` {roster_entry_id, player_id, first_name, last_name, from, to};
  `roster_left` {roster_entry_id, player_id, first_name, last_name, jersey_number};
  `report` (past game with official log) and `match_new` {game_id, kickoff_at, is_home, opponent,
  venue, competition, played, score_own, score_opponent, match_id (report)};
  `match_moved` {same plus match_id, from {kickoff_at, venue}, to {kickoff_at, venue}};
  `season_new` {official_team_id, season_id, label, starts_on, ends_on, name, league, group_name}.
  `POST .../official/suggestions/{id}/accept` (body optional; `roster_add` takes
  `{jersey_number}` to override, null = none; a taken number is left empty) returns
  `{suggestion, player_id?, match_id?, season_id?, report?}` (`report` = the import result as in
  the manual report import); `POST .../dismiss`. 409 `suggestion-resolved` when already decided,
  409 `suggestion-stale` when the match or entry is gone. A dismissed suggestion is not proposed
  again. Suggested UI: roster list with checkboxes and number fields ("Alle übernehmen" = accept
  one by one), report rows with "Importieren", schedule changes as "Verschoben: alt → neu".
- Team page: `GET /v1/orgs/{org}/teams/{team}/official` (every team member) `{linked, provider,
  official_team_id, official_club_id, official_group_id, official_season_id, league, group_name,
  synced_at, standing: [{teamId, clubId, name, rank, games, won, drawn, lost, goalsFor,
  goalsAgainst, goalDifference, points}], open_suggestions}` (`open_suggestions` only for
  organisers, else 0); `{linked: false}` for teams made by hand. "Jetzt abgleichen":
  `POST .../official/sync` (organisers, 6 per hour) returns the counts and `synced_at`. Otherwise
  the sync runs daily; after each game the official report is imported automatically.
  `TeamOut.official_team_id` and `OrgOut.official_club_id` / `OrgOut.verification` are new fields.
- Join requests (players, way B): `POST /v1/teams/{team_id}/join-requests` body `{first_name,
  last_name, jersey_number?, role: "player" | "goalkeeper", message?}` (signed in, not a member;
  409 `join-request-pending`, 409 `already-member`) returns `{id, team_id, team_name,
  organization_id, organization_name, status, created_at}`. `GET /v1/me/join-requests` (status
  pending | approved | declined | withdrawn), `DELETE /v1/me/join-requests/{id}` withdraws. The
  requester never sees the roster. Coach side: `GET /v1/orgs/{org}/teams/{team}/join-requests`
  (pending) with `email` and `suggested` {kind: "player" | "suggestion", id, first_name,
  last_name, jersey_number} (the matching roster entry or roster suggestion, null when none or
  two equally good). `POST .../join-requests/{id}/approve` body optional `{player_id |
  suggestion_id | new_entry: true}` (empty = take `suggested`, else a new roster entry from the
  request); `POST .../decline`. Suggested UI: "Luca Müster möchte beitreten — passt zu #55 Luca
  Muster? [Bestätigen]". Parents still come through the coach's invitation.
- Access requests (second person of a claimed club): `GET /v1/orgs/{org}/access-requests` (club
  admins) `{id, user_id, name, email, team_id, official_team_id, message, status, created_at}`;
  `POST .../{id}/approve` body optional `{org_role: "member" | "org_admin", team_role: "coach"}`
  (a requested team not yet in the app is created from the official data with the person as its
  coach); `POST .../{id}/decline`. Requester: `GET /v1/me/access-requests`.
- Verification of claimed clubs: `GET /v1/orgs/{org}/verification` `{verification: "none" |
  "unverified" | "verified", verified_via: "mail_domain" | "second_official" | "federation" |
  "operator", verified_at, official_club_id, club_domains, methods}` (checks the automatic ways on
  each call). `POST /v1/orgs/{org}/verification/confirm`: a second club admin or coach (not the
  claimant, confirmed e-mail) confirms (403 `second-person-required`, 403 `email-unverified`).
  Operators: `POST /v1/ops/organizations/{org}/verification` `{verified}`. While "unverified":
  share links and public profiles give 403 `org-unverified`, official reports keep opponent
  players as numbers only. Suggested UI: a banner "Verein noch nicht bestätigt" with the ways
  (mail at the club domain, second person, federation licence, support).
- Data protection: roster entries taken from the official data are listed only for organisers
  until the person joins (account) or a consent is recorded; other team members do not see them.
- New notification kinds (in-app and push, need web texts): `join_request`, `join_approved`,
  `access_request`, `access_approved`, `official_suggestions` (params `team_id`, `count`),
  `official_report` (params `match_id`).

Official report import from nuLiga and the HLA (2026-11-05, backlog item 6): `POST
/v1/orgs/{org}/matches/{id}/official-report` also takes
- nuLiga game report links (German associations still on nuLiga: BHV, HHV, HVNB, HVS, HVSA, THV, HVMV,
  MHV; Austria: ÖHB): the page `https://<association>-handball.liga.nu/cgi-bin/WebObjects/
  nuLigaHBDE.woa/wa/groupMeetingReport?meeting=…&championship=…&group=…` or the PDF
  `…/nuLigaDokumentHBAT.woa/wa/nuDokument?dokument=meetingReportHB&meeting=…` (the link oehb.at
  shows). Result `provider` "nuliga", `game_id` = the nuLiga meeting id. Same events as the other
  sources (goals with scorer and number, 7 m, 2 minutes, warnings, disqualifications, time-outs).
- HLA report PDFs `https://infographics.sportradar.com/hla/pageSnapshot/pdf/de/<id>`, or `{"url":
  "<id>", "provider": "hla"}` (the request enum gained "hla"; nuLiga has no plain-id form). Result
  `provider` "hla". This report has no timed goals: only the result, half-time and the missed 7 m
  are imported, and `warnings[0]` says so and points to the ÖHB nuLiga report. Suggested UI: show
  the warnings as they come; the input hint can read "Link zum Spielbericht (handball.ch, DHB,
  nuLiga, HLA)".

Official onboarding, three decisions (2026-11-05, docs/plans/federation-onboarding.md
"Entscheide"; api-client regenerated):
- Plan limit: official games count toward the plan's matches per season (free: 2). With billing
  enforced the claim creates matches only up to the limit (next upcoming games first, then the
  most recent played ones); the claim's `prefill` has the new count `matches_held_back` (also in
  the sync answer, there always 0). The held-back games are `match_new` suggestions with
  `payload.reason: "plan_limit"`; `SuggestionOut` has the new field `blocked: "plan_limit" | null`
  (set on open `match_new` while accepting would exceed the plan; accept gives 402
  `plan-limit-matches`). After an upgrade `blocked` is null and accepting works; a played game
  then also gets its result and a `report` suggestion. Suggested UI: on the claim summary "X
  weitere Spiele im Gratis-Plan nicht übernommen" with an upgrade link; in the inbox those rows
  with a lock and "Upgrade" instead of "Übernehmen" while `blocked`.
- Roster suggestions with statistics: `roster_add` payload has the new `stats` (null when the
  player has no game yet) `{games, goals, goals_7m, attempts_7m, suspensions_2min, goalkeeper,
  saves, shots_faced}` (each null when handball.ch gives no value; `saves`/`shots_faced` only for
  goalkeepers), over the last 10 played games of the season like `appearances`. The coach chooses
  whether to show them: `GET .../teams/{team}/official` has `roster_stats` (bool, default false),
  `PATCH /v1/orgs/{org}/teams/{team}/official` body `{roster_stats}` (organisers; returns the link)
  keeps the choice for all organisers of the team. Suggested UI: a toggle "Statistik anzeigen"
  above the roster confirmation, extra columns Tore, 7 m, 2', Sp., Paraden (keepers).
- Club verification: unchanged (a second club admin or coach confirming is enough).
