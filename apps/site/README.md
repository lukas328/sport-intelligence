# apps/site: the public website and help centre

Static Next.js site in the app's look «Anlauf» (concept and texts: `docs/site/KONZEPT.md`):
start, So funktioniert es, Filmen, Demo-Spiel, Preise, Fragen (with the help guides), Daten und
Einwilligung, Über uns und Kontakt, Ratgeber (guides), Fakten auf einen Blick, Über uns, blog, terms, privacy, imprint; German (de-CH), French and
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
- Guides (Ratgeber): `content/ratgeber/{locale}/{slug}.mdx`, index with the question, the answer, the
  meta title, the description and the languages in `content/ratgeber/index.ts`. Every guide exists in
  German; French and English where `locales` says so (tested). An MDX file may export `faq` and
  `howto`; the page shows them and writes FAQPage and HowTo from the same data. Drawings for guides:
  `src/components/figures.tsx` (labels come from the MDX file).
- Search engines and AI assistants: `docs/site/SEO.md`. Titles and descriptions per page in
  `messages.seo`, structured data in `src/lib/schema.ts`, `/llms.txt` and `/llms-full.txt` from
  `src/lib/llms.ts`, the facts page from `messages.facts`. `PRICES_FINAL` in `src/lib/site.ts` puts
  the prices into structured data. The site describes the product as it will be at release, with
  no «noch nicht», «vorgesehen» or «geschätzt» (BEFUNDE-2 W32); only the legal drafts say they
  are drafts.
- Help articles: `content/help/{locale}/{slug}.mdx`, index with titles, summaries and search keywords in
  `content/help/index.ts`. Every article exists in all three languages (tested).
- Blog: `content/blog`, legal drafts: `content/legal` (marked as not yet legally reviewed, Q-ADD-5).
- Texts of the pages: `src/messages/{de,fr,en}.ts` (same keys and placeholders, tested).
- Prices: `@handball/plans` (`packages/plans/plans.json`), generated from the API plan table with
  `make plans`; CI fails when it is out of date.
- Demo match: `public/demo/match.json`, a fictional match from `scripts/make_demo.py` (a fixed plan,
  lost 16:18 with 9 of 18 goals conceded over the right wing, and seeded random shots, times and
  numbers; statistics from `handball_metrics`); regenerate with `make plans`. `src/lib/demo.ts` turns it
  into what the pages draw (zones, invented runs, the three things, one scene on the tactics camera);
  the page says «Erfundenes Spiel» at the top. Everything invented is handball-typical: shot spots
  and runs stay outside the goal area, the scene has a 6:0 defence in front of 6 m, the attack
  around 9 m, only the goalkeeper in the goal area, and the ball in every frame (tested in
  `src/lib/demo.test.ts`). The visitor's colour comes in with `?kit=red` (no storage).
- Product pictures: `public/product/*.webp` (1x and @2x), made by `scripts/product-shots` from the
  local app with the seeded demo club: `pnpm --filter @handball/site shots` (how:
  `scripts/product-shots/README.md`); sizes and callouts in `src/lib/product-shots.json`, the
  callout texts in `src/messages/*.ts` (`product`).
- Start page: one invented week with the demo match (BEFUNDE-2 W5, W22): hero with the team field
  and the answer from the app, Saturday 7 pm (lost, only a feeling), Saturday 10 pm (the three
  things), one goal on the tactics camera, film/upload/check, Tuesday (four scenes in the team
  chat), three matches later (3 of 22, `src/lib/story.ts`), the video in the club, price, start.
  The pieces are in `src/components/story.tsx`. Blocks marked `data-reveal` glide in once
  (`src/components/reveal.tsx`); with `prefers-reduced-motion` nothing moves.
- Help guides outside the core have `listed: false` in `content/help/index.ts`: reachable for the app's
  links, not listed, not in the sitemap, `noindex`.

## Hosting

`pnpm build` runs `next build` and then `scripts/redirects.mjs`, which adds to `out/`:

- a small page for every address without a language path (`/aufnahme/`, `/so-funktioniert-es/`,
  `/demo/`, `/preise/`, `/hilfe/` and every guide, `/ratgeber/` and every guide (German-only guides go to `/de/` in every language), `/fakten/`, `/ueber-uns/`, `/daten/`, `/kontakt/`, `/blog/` and posts, `/agb/`,
  `/datenschutz/`, `/impressum/`, `/funktionen/`): it sends the visitor to the same page in the
  browser's language (fr or en, otherwise de), keeping `?query` and `#hash`; without scripts a meta
  refresh goes to `/de/…`. The app links to `/aufnahme/` from its upload, so keep that address.
- `404.html` in the site's look with Start, Demo-Spiel and Fragen, in the language of the path or the
  browser.

Merged pages: a blog post with `movedTo` in `content/blog/index.ts` (today `spiele-filmen-mit-dem-handy`, merged into the guide «Handballspiel mit dem Handy filmen») forwards by meta refresh, is `noindex` and has its canonical on the guide; on the host answer `/{lang}/blog/spiele-filmen-mit-dem-handy/` with a 301 to `/{lang}/ratgeber/handballspiel-filmen/`.

On the real host, set this up as well (the fallback pages above only work with a script or after a
second):

- **Unknown paths** answer `404.html` with status 404 (`error_page 404 /404.html;` in nginx,
  `handle_errors` in Caddy, `404.html` is picked up by Cloudflare Pages and Netlify by default).
- **Addresses without a language** answer with a 302 to `/{lang}/…` from `Accept-Language`
  (fr, en, else de), e.g. nginx:

  ```nginx
  map $http_accept_language $site_lang { default de; ~^fr fr; ~^en en; }
  location ~ ^/(so-funktioniert-es|aufnahme|demo|preise|hilfe|ratgeber|fakten|ueber-uns|daten|kontakt|blog|agb|datenschutz|impressum|funktionen)(/.*)?$ {
    return 302 /$site_lang$request_uri;
  }
  ```

  On Cloudflare Pages a `_redirects` file can only send them to `/de/…` (no language test); then
  keep the fallback pages for fr and en.
- `/` stays `public/index.html` (language choice by script, meta refresh to `/de/`).

## Build variables
| variable | default |
|---|---|
| `NEXT_PUBLIC_SITE_URL` | `https://handball-intelligence.com` (canonical URLs, hreflang, sitemap, robots, structured data, llms.txt) |
| `NEXT_PUBLIC_APP_URL` | `https://app.handball-intelligence.com` (the team field and «Kostenlos starten» go to `/einstieg?q=…`, «Anmelden» to `/login`; `?lang=` sets the app language) |
| `NEXT_PUBLIC_SUPPORT_EMAIL` | `support@handball-intelligence.com` |
| `NEXT_PUBLIC_STATUS_URL` | empty (link hidden) |
| `NEXT_PUBLIC_COMPANY_NAME`, `_ADDRESS`, `_UID` | empty (imprint says the details follow) |

The site sets no cookies and loads nothing from third parties. Results of the last check are in
`docs/site/TEST.md`.
