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
