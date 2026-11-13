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

## Hosting

`pnpm build` runs `next build` and then `scripts/redirects.mjs`, which adds to `out/`:

- a small page for every address without a language path (`/aufnahme/`, `/so-funktioniert-es/`,
  `/demo/`, `/preise/`, `/hilfe/` and every guide, `/daten/`, `/kontakt/`, `/blog/` and posts, `/agb/`,
  `/datenschutz/`, `/impressum/`, `/funktionen/`): it sends the visitor to the same page in the
  browser's language (fr or en, otherwise de), keeping `?query` and `#hash`; without scripts a meta
  refresh goes to `/de/…`. The app links to `/aufnahme/` from its upload, so keep that address.
- `404.html` in the site's look with Start, Demo-Spiel and Fragen, in the language of the path or the
  browser.

On the real host, set this up as well (the fallback pages above only work with a script or after a
second):

- **Unknown paths** answer `404.html` with status 404 (`error_page 404 /404.html;` in nginx,
  `handle_errors` in Caddy, `404.html` is picked up by Cloudflare Pages and Netlify by default).
- **Addresses without a language** answer with a 302 to `/{lang}/…` from `Accept-Language`
  (fr, en, else de), e.g. nginx:

  ```nginx
  map $http_accept_language $site_lang { default de; ~^fr fr; ~^en en; }
  location ~ ^/(so-funktioniert-es|aufnahme|demo|preise|hilfe|daten|kontakt|blog|agb|datenschutz|impressum|funktionen)(/.*)?$ {
    return 302 /$site_lang$request_uri;
  }
  ```

  On Cloudflare Pages a `_redirects` file can only send them to `/de/…` (no language test); then
  keep the fallback pages for fr and en.
- `/` stays `public/index.html` (language choice by script, meta refresh to `/de/`).

## Build variables
| variable | default |
|---|---|
| `NEXT_PUBLIC_SITE_URL` | `https://handball-ai.ch` (canonical URLs, sitemap) |
| `NEXT_PUBLIC_APP_URL` | `https://app.handball-ai.ch` (the team field and «Kostenlos starten» go to `/einstieg?q=…`, «Anmelden» to `/login`; `?lang=` sets the app language) |
| `NEXT_PUBLIC_SUPPORT_EMAIL` | `support@handball-ai.ch` |
| `NEXT_PUBLIC_STATUS_URL` | empty (link hidden) |
| `NEXT_PUBLIC_COMPANY_NAME`, `_ADDRESS`, `_UID` | empty (imprint says the details follow) |

The site sets no cookies and loads nothing from third parties. Results of the last check are in
`docs/site/TEST.md`.
