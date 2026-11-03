# 014. Tactics board format and play library

- Status: accepted
- Date: 2026-11-03

## Context
BRIEF 8.3 asks for a tactics editor (frames, animation, touch), video and board side by side, templates and a
play library. Plays must survive app updates, be renderable on the server later (PDF, M8) and be created from
tracking data.

## Decision
- One JSON document per play, `formatVersion: 1`, in court metres (same system as tracking and
  `@handball/court`): frames with tokens (id, side, label, x, y), ball, arrows (run, pass, dribble, screen),
  note and duration. Limits: 30 frames, 16 tokens, 20 arrows. The format, interpolation (`stateAt`: hold 30 %,
  then eased movement), `nextFrame` (tokens follow their run arrows) and validation live in
  `packages/tactics`; the API validates the same limits with Pydantic.
- Rendering is plain SVG with pointer events (mouse, pen, touch) and keyboard moves (0.5 m / 2 m), so the
  board works without a pointer and stays sharp at any size.
- Plays are team-scoped rows (`plays`, RLS) with category, formation, tags, an optional video source
  (`match_id`, `t_ms`) and `shared_with_players`.
- Templates are code (`packages/tactics/src/templates.ts`), not rows: they need no migration to improve and
  are copied into a play when used.
- "Als Spielzug übernehmen" reads the tracking chunk at the current moment and creates the first frame.

## Consequences
- A format change needs a version bump and a migration function in `packages/tactics`.
- Play clustering (DTW + HDBSCAN over possessions) is not part of this decision; it needs real tracking data.
