# 004. Chart library: visx

- Status: accepted
- Date: 2026-11-02

## Context
BRIEF 11 asks for one chart library (visx or Recharts). Many visuals are domain specific (shot map on the
court, 3x3 goal grid, momentum chart with runs, matchup matrix) and every element must be clickable to
clips. Bundle budget: < 250 kB gzip JS on the start page, charts rendered only when visible.

## Decision
**visx** (Airbnb, MIT) for all charts, wrapped in our own components in `packages/ui/charts`.
Court, goal and tactics board drawings use the same primitives (SVG, Canvas for animation) with
`packages/court` geometry.

## Consequences
- Low-level: more code per chart than Recharts, but full control over interaction (click to clips),
  accessibility (ARIA, keyboard focus) and theming (CSS variables, dark mode).
- Modular imports keep bundles small; charts are lazy loaded per route.

## Alternatives considered
- Recharts: faster for standard charts, but custom court/goal visuals would need a second approach.
- ECharts: powerful but large bundle and canvas-first, weaker for accessible SVG.

## Amendment (2026-11-03, M4)
The M4 visuals (score progression, shot map on the court half, 3x3 goal grid, comparison tables) are plain
SVG components in `apps/web/src/components/analysis` built on `@handball/court` geometry. They needed no
scales or axes beyond a few lines of code, so visx is **not installed yet** (0 kB added). visx stays the
choice once charts with real axes, brushing or many series arrive (season trends in M7); the components keep
the same props so the switch is local.
