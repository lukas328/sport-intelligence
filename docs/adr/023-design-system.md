# 023. Design system and navigation: four destinations, paper and ink, Archivo

- Status: accepted
- Date: 2026-11-03

## Context
After eleven milestones the web app had grown one menu entry per feature: ten links in the club
navigation, eleven team tabs, eight match tabs and six action buttons on the match page, all in
the same narrow column with system fonts, bordered boxes and symbol characters as controls. On a
phone the navigation took four rows before any content. The owner asked for a UI-first rebuild:
lean, simple to navigate, distinctive, not generic, production ready (UX blueprint, 2026-11).

## Decision
- **Navigation by role, at most four destinations** (`lib/nav-model.ts`, tested): coach Übersicht ·
  Spiele · Team · Training; player Übersicht · Szenen · Termine · Team; parent Übersicht · Termine ·
  Team. Two levels at most; account items in an avatar menu; a command palette (cmdk) for
  everything else. Sidebar on desktop, tab bar on phones, full screen for courtside and
  presentation tools.
- **State-driven pages**: one primary action that depends on the state (upload, live, prepare),
  the rest in a menu; dedicated empty, loading, processing and error states.
- **Visual language**: Archivo variable (weight and width axes, SIL OFL, self-hosted with
  `next/font/local`), wide cut for headings and scoreboard figures; warm paper background with
  white panels; one accent from the club colour, shifted per theme to 4.5:1 (`lib/color.ts`);
  lucide icons; light and dark themes with a user switch (cookie `hb_theme`, no flash).
- **Components**: own primitives on Radix (dialog, dropdown menu) and cmdk, styled with the
  tokens; no component kit look. `useConfirm` replaces browser dialogs.
- **Guard rails**: `design-lint.test.ts` (no browser dialogs, no symbol controls, colours from
  tokens, no long dashes, no ß), `nav-model.test.ts` (four destinations), axe in Playwright.
- Work went straight to `main` on the owner's request (the blueprint proposed a separate branch).

## Consequences
- Some features moved one click further away (matrix and assistant behind Saison, library items
  behind Bibliothek, PDF and data exchange behind "…"); the command palette reaches all of them
  directly. Playwright flows were updated to the new paths.
- Dependencies added: `lucide-react`, `@radix-ui/react-dialog`, `@radix-ui/react-dropdown-menu`,
  `cmdk` (all within the route budgets).
- The marketing site and the Expo app use the same tokens and typeface; their layouts were not
  rebuilt in this step.
- The product name stays a working title (Q-PROD-1); the mark (goal area seen from above) is
  easy to replace.
