# 024. Identity "Die Halle": club colour as stage, Barlow, angular form, a voice from the data

- Status: accepted (pending review in the pull request `identity/halle`)
- Date: 2026-11-03
- Supersedes the visual language of ADR 023 (navigation and UX of ADR 023 stay)

## Context
After the UI-first rebuild (ADR 023) the app was clean and easy to use but still looked like a
generated SaaS dashboard: warm off-white with white panels and one accent, round soft panels and
pills everywhere, five equal stat tiles, stock icons, a sparkle symbol for AI, neutral copy. The
owner asked for identity, emotion and handball, "more love", while staying a highly produced app.
An identity blueprint came with reference screens; the owner later said the references themselves
are ugly and only the idea should be taken over (decisions in `docs/design/identity/DECISIONS.md`).

## Decision
- **Stage and workbench.** One stage per screen at most, at the top of overview, season and match
  (and landing, sign-in, onboarding): the raw club colour full bleed, the court's goal area drawn
  from `packages/court` as its frame, the score as the loudest element, one statement. Everything
  else is a calm workbench (match-sheet tables, hairlines, paper).
- **Colour from the club** (`lib/color.ts`): stage, deep shade for the sidebar, paper tinted
  towards the club, accent at 4.5:1, resin-yellow signal for one thing per screen, white marker
  for the current place; tested for six club colours in light and dark.
- **Type**: Barlow and Barlow Condensed, self-hosted (OFL); Reenie Beanie only for real coach
  notes; Archivo removed.
- **Form**: 6 to 8 px radius, no pills, no floating cards, no coloured side borders (checked in
  `design-lint.test.ts`).
- **Own icons** for navigation and handball objects; lucide only for neutral controls.
- **Voice** (`lib/voice.ts`): deterministic statements from real figures (runs, goals against
  expected goals, defence, record, match margin); neutral when the data is thin; estimates marked.
- **Moments**: score count-up, analysis-done on the stage, a match card as a local 4:5 PNG.

## Consequences
- Every club looks like itself; the same screen in red, green or yellow feels different. Light club
  colours (yellow) switch to dark ink on the stage and a neutral deep shade.
- The season chart appears only from three matches; a sentence says so before that.
- The focus figure on the season strip uses reference values (save rate 30 %, shooting 55 %,
  12 turnovers per match), not a league average; the page says so.
- Real coach notes in handwriting and video frames on the stage were not added: notes need a
  matching moment and frames need consent checks per player (open in `FOR_LUKAS.md`).
- The marketing site and the Expo app still use the ADR 023 look.
