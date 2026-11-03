# apps/site: marketing site and help centre

Static Next.js site (addendum 01, 4.13): start, features, pricing, demo analysis, recording guide,
help centre, blog, contact, terms, privacy, imprint; German (de-CH), French and English under
`/de/`, `/fr/`, `/en/`. `/` picks the browser language.

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
  events, statistics from `handball_metrics`); regenerate with `make plans`.

## Build variables
| variable | default |
|---|---|
| `NEXT_PUBLIC_SITE_URL` | `https://handball-ai.ch` (canonical URLs, sitemap) |
| `NEXT_PUBLIC_APP_URL` | `https://app.handball-ai.ch` (sign-up and log-in links, `?lang=` sets the app language) |
| `NEXT_PUBLIC_SUPPORT_EMAIL` | `support@handball-ai.ch` |
| `NEXT_PUBLIC_STATUS_URL` | empty (link hidden) |
| `NEXT_PUBLIC_COMPANY_NAME`, `_ADDRESS`, `_UID` | empty (imprint says the details follow) |

The site sets no cookies and loads nothing from third parties. Lighthouse (mobile defaults, local
static server): performance 92 to 98, accessibility 100, best practices 96, SEO 100.
