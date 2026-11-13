# 029. Scope, four destinations, hidden team features

- Status: accepted (structure and data built; the look is still open)
- Date: 2026-11-10
- Supersedes: the navigation of ADR 023 and the identity "Die Halle" of ADR 024
- Numbering: the brief for this work called it ADR 025; 025 to 028 were taken, so it is 029.

## Context

66 screenshots (`docs/design/ux-reset/ASSESSMENT.md`) showed an app that offers a club everything
and a coach nothing in particular: four destinations per role that mixed match, training and team
life, two levels of tabs inside a match, nine sub-tabs, several words for the same thing, and
communication features that only work when everyone in the club uses the app.

## Decision

1. **Scope: the coach, alone.** The product is match analysis for the coach: upload a match, get
   three things, see the scenes behind them. The test for every feature: does the coach get
   something out of it if nobody else in the club opens the app? Tiers as in `SPEC.md`, section 1:
   core (built now), next (training plan, drills, plays: kept, out of the navigation), last (player
   and parent accounts, RSVP, dates, attendance, tasks: kept behind a team setting), never (chat,
   messages, line-ups, car pools, fees).
2. **Four destinations for staff** (coach, analyst, team manager, admin): Spiele · Szenen · Saison
   · Team, Spiele is the start. "Video hochladen" is one action reachable from everywhere; search
   stays. At most one level of tabs inside a destination (`lib/nav-model.ts`, tested).
   A match has Spiel · Video · Zahlen; Szenen has Szenen · Sammlungen · Spielzüge · Tabelle.
3. **"Teamfunktionen"**, a team setting (`teams.settings.team_features`), off by default, also for
   existing teams. Off: training, dates, RSVP, tasks and the destinations of players and parents
   leave the navigation and the search. Nothing is deleted; every route stays reachable. On,
   staff get Kader, Termine, Training and Aufgaben as tabs of Team.
4. **Routes after `SPEC.md`, section 6.** Old addresses redirect where the target exists
   (`/live`, `/marks` to Spieltag, `library` to Sammlungen, `search` to Szenen with its filters,
   `paper` to the dialog "Spielbericht hinzufügen", `settings` and `profile` to Ich and Verein).
5. **One word per thing** (`SPEC.md`, section 9) in de-CH, fr and en, e-mails, PDF labels and the
   mobile app.
6. **Sammlung** is one object (scenes, plays, notes) instead of playlist, presentation and
   assignment. The older objects stay as data and are read as collections.
7. **Consent through a link** without an account is the one thing players and parents must do.
8. **The look is not decided here.** It is decided in `docs/design/ux-reset/` and still open
   (several directions are being explored). The data the screens need in any direction is built:
   the club's first and second colour with their contrast values (`lib/color.ts`), and the
   opponent's colour per match, remembered per opponent club and never guessed, with a rule for
   colours too close to ours (second colour, then ink).

## Consequences

- Phase 1 (this ADR) changes structure and data only: navigation, routes, words, the team setting,
  and the data the new screens need (kit, opponent colour, goals conceded by position, season
  themes, shared links for scenes and collections with Open Graph data, consent links,
  collections, demo data). Screens that did not exist are plain pages with the existing
  components. The look follows once it is decided.
- The workspace inside the Video tab still has its own tool tabs; they go in phase 2 (SPEC 7.3:
  no sub-tabs). Matrix and the data assistant stay as pages under Szenen until the search field
  answers questions itself.
- E2e specs follow the new addresses and words; Mailpit-dependent specs were not run in the
  cloud session (see `docs/runbooks/local-stack-without-docker.md`).

## Alternatives considered

- Deleting the player and parent features: rejected, they work and may come back; a setting
  hides them at no cost.
- Keeping playlists and presentations as separate objects: rejected, the coach thinks in one
  thing to show the team; a read-only mapping keeps the data without a migration.
- Recording a visual direction here: left out on purpose; it is still being explored.
