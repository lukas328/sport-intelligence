# How we work on the match workspace: rounds with checks

The owner's main complaint about the app is that it looks generated and loveless. Taste alone
does not fix that; every change goes through the same loop, with a check against how good
products solve the same job.

## The loop (one round per slice)

1. **Build** a small slice. Commit small. `pnpm lint`, `pnpm typecheck`, `pnpm test` stay green.
2. **Shoot** the fixed set of screenshots on the local stack with real-looking data:
   desktop 1440 × 900 light and dark, phone 390 (iPhone 13), each work step that changed, and
   the state after one real action (a goal confirmed, a list done, an empty state).
3. **Review with fresh eyes.** An agent that has not seen the code gets only the screenshots,
   `REFERENCES.md` (patterns from real products, anti-patterns, the rubric) and the identity
   (`docs/design/identity/`). It scores the rubric 1 to 5, names the five most important
   findings, and for each one the reference pattern that would solve it.
4. **Fix** concrete findings. At most three review rounds per slice, so it does not loop.
   Taste never wins against readability, accessibility (WCAG 2.2 AA, keyboard, 390 px) or honest
   data (estimates labelled, counts read against what the video covers).
5. **Gate** before a slice counts as done: the e2e specs that touch it (`match`, `analysis`,
   `layout`) and axe pass on the local stack.
6. **Log** the round in `PROGRESS.md`: scores, findings, what changed, what was left and why.

## What we compare against

`REFERENCES.md` collects concrete patterns from products coaches and analysts use or know:
sports video analysis (Hudl, Nacsport, Catapult, Veo, Wyscout), video review (Frame.io,
YouTube Studio), match centres of sports media (momentum, event timelines) and fast keyboard
triage (Superhuman, Linear, labelling tools). We adapt the idea, never the look: the identity
"Die Halle" stays the base.

## Questions every screen must answer

- What is the one job of this screen for a coach, and is it the loudest thing?
- Would someone recognise handball without the logo?
- What here would a template dashboard have done the same way? Replace or remove it.
- Is every number readable against what it refers to (the clip, the half, the season)?
- Does every number lead to the video?
- Is there an element without a purpose?
