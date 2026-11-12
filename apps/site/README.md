# apps/site: the public website and help centre

Static Next.js site in the app's look «Anlauf» (concept and texts: `docs/site/KONZEPT.md`):
start, So funktioniert es, Filmen, Demo-Spiel, Preise, Fragen (with the help guides), Daten und
Einwilligung, Über uns und Kontakt, blog, terms, privacy, imprint; German (de-CH), French and
English under `/de/`, `/fr/`, `/en/`. `/` picks the browser language. `/funktionen/` forwards to
`/so-funktioniert-es/`.

Set for older eyes: body text 19 px (18 on phones), nothing important under 16 px, targets 48 px,
no symbol-only buttons, motion off with `prefers-reduced-motion`. Kanit, Hanken Grotesk and IBM
Plex Mono are self-hosted (`src/fonts`, SIL OFL). The Anlauf building blocks (colour model, bundle,
tactics camera, flight) are copies of `apps/web/src/components/anlauf` and `apps/web/src/lib/color.ts`
in `src/components/anlauf` and `src/lib/color.ts`; keep them in step by hand.

```bash
pnpm --filter @handball/site dev      # http://localhost:3000/de/
pnpm --filter @handball/site build    # static files in apps/site/out
```

The output is plain files: serve `out/` from any web server or CDN (no Node at runtime). The help
centre lives at `{site}/{de|fr|en}/hilfe/{slug}/`; the app links there with `HB_HELP_BASE_URL`
(`apps/web/src/components/support/help-map.ts` must only use slugs that exist; a Vitest test checks it).

## Content
- Help articles: `content/help/{locale}/{slug}.mdx`, index with titles, summaries and search keywords in
  `content/help/index.ts`. Every article exists in all three languages (tested).
- Blog: `content/blog`, legal drafts: `content/legal` (marked as not yet legally reviewed, Q-ADD-5).
- Texts of the pages: `src/messages/{de,fr,en}.ts` (same keys and placeholders, tested).
- Prices: `@handball/plans` (`packages/plans/plans.json`), generated from the API plan table with
  `make plans`; CI fails when it is out of date.
- Demo match: `public/demo/match.json`, a fictional match from `scripts/make_demo.py` (seeded random
  events, statistics from `handball_metrics`); regenerate with `make plans`. `src/lib/demo.ts` turns it
  into what the pages draw (zones, invented runs, the three things, one scene without a ball); the
  page says «Erfundenes Spiel» at the top. The visitor's colour comes in with `?kit=red` (no storage).
- Help guides outside the core have `listed: false` in `content/help/index.ts`: reachable for the app's
  links, not listed, not in the sitemap, `noindex`.

## Build variables
| variable | default |
|---|---|
| `NEXT_PUBLIC_SITE_URL` | `https://handball-ai.ch` (canonical URLs, sitemap) |
| `NEXT_PUBLIC_APP_URL` | `https://app.handball-ai.ch` (sign-up and log-in links, `?lang=` sets the app language) |
| `NEXT_PUBLIC_SUPPORT_EMAIL` | `support@handball-ai.ch` |
| `NEXT_PUBLIC_STATUS_URL` | empty (link hidden) |
| `NEXT_PUBLIC_COMPANY_NAME`, `_ADDRESS`, `_UID` | empty (imprint says the details follow) |

The site sets no cookies and loads nothing from third parties. Results of the last check are in
`docs/site/TEST.md`.
