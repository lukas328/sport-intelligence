# 017. Addendum 01: product principles, extended data model and new milestones

- Status: accepted (plan); implementation from milestone A1
- Date: 2026-11-03

## Context
`docs/BRIEF_ADDENDUM_01.md` adds product principles (P1 to P10), launch requirements (P0), first-season
features (P1), later items (P2), partner adapters and legal points. It takes precedence over BRIEF.md.
M0 to M9 are finished, so the items assigned to them are scheduled in new milestones A1 to A4 before
launch (PLAN.md section 5).

## Decision
### Data model (additive migrations, RLS on every tenant table, policy matrix extended)
- **Organisation level:** `Federation` (contract, quota) with `federation_memberships` to organisations;
  federation admins see usage and anonymised aggregates only, never videos without the club's release.
  `Invoice` (payment method `card` or `invoice_qr`, due date, dunning level, payment received).
- **Team and match:** `MatchFormat` (period length, periods, court, youth rules) referenced by matches and
  teams (default per team); `MatchSegment` (source asset, offsets, gaps) between matches and video assets,
  which also allows several matches per video; match type `training` without opponent.
- **Content:** `TagSet`/`Tag` per team, `ClipTag` polymorphic over clip, event and play;
  `SavedFilter` stores a filter definition that resolves to clips (smart playlist).
  `Presentation`/`PresentationSlide` (types clip, tactics_board, text, stat_card, image; clip slides with
  in/out, hold points, slow-motion ranges, drawings, spotlight track). `HighlightReel`, `ScoutingReport`
  (structured facts plus PDF), `PlayerFeedItem`, `SelfAssessment`.
- **People:** team roles `goalkeeper_coach`, `athletic_coach`, `team_manager`, `parent`; org role
  `federation_admin` lives on the federation. Parents link to players (`guardianships`) and see only
  their children's content. Consent becomes per purpose (`analysis`, `highlights_internal`,
  `highlights_public`, `public_profile`, `training_data`) with history (append-only rows, latest wins)
  and revocation; existing `video_analysis`/`identification` consents migrate to `analysis`.
- **Assistant and others:** `ConversationThread`/`AssistantMessage` (tools used, facts, clip ids, cost,
  rating), `PublicProfile`, `PaperReportUpload`, `TrainingSession`/`Attendance`, `LiveTagSession`/`LiveTag`
  (device time, offset to video, sync confidence) next to the existing match-clock live mode.

### Architecture
- Partner integrations behind adapters in `apps/api/src/handball_api/integrations/` (video sources,
  livestream, team ops, official feed, wearables, support chat, status page), each with a stub and tests.
- Presentation remote: WebSocket channel per presentation session via the existing Redis pub/sub bus.
- Exports with burned-in drawings and spotlight are rendered by the worker (ffmpeg filter graphs from
  track data), never in the browser.
- The assistant (M10) uses Claude tool use with typed, permission-checked tools only (no SQL) and the
  same number validator as the summaries (ADR 015).

## Consequences
- Many P0 items (highlights, player feed, scouting reports, spotlight accuracy, multi-angle sync below
  2 frames) assume automatic events and good tracking. Today events come from tagging and imports, and
  tracking is a heuristic baseline (ADR 012). Milestone A3 is therefore on the critical path and needs
  real footage (OPEN_QUESTIONS Q-DATA-1, Q-ADD-1).
- Role and consent changes touch every policy; the policy matrix test is extended before features use them.

## Implementation notes (A1, 2026-11-03)
Implemented in migrations 0015 and 0016; deviations (ClipTag on clips only, match type `training` and a
stored team default format moved to A2) are listed in `docs/progress/A1.md`. Adapters: ADR 018.

