# Product pictures

The pictures of the app on the website (start page, «So funktioniert es», «Über uns») are not raw
screenshots: real screens of the app, placed into designed pictures. The steps are flat cut-outs
of the phone in one shape and look (no device, no Keil; BEFUNDE-2 S11), the computer pictures sit
in a browser window, some on the club's Keil with a soft shadow; yellow rings mark what matters. The arrows and their labels
are drawn by the website over the picture, as real text in the visitor's language
(`src/components/product-shot.tsx`, texts in `src/messages/*.ts` under `product`). They show the
seeded demo club (HC Zürichsee, invented players, synthetic videos), never real people, and only
what the app really shows. The demo club plays in the website's own pine green (`#10684a`, seed
and synthetic footage), so the pictures sit in the site's colours (cream, green, ink).

The website tells its own story with the demo match (a defeat, 16:18; `scripts/make_demo.py`),
while the seeded club in the app won its match 26:18. So no picture shows a score or the match's
headline («Gewonnen.»), and none shows the season's sentence: the pictures are cut-outs of what
matters, in the app's own brightness (no darkened surroundings), and the numbers the story needs
(9 von 18 über aussen rechts) are in them. `captures/ergebnis-*.webp` are no longer used. The start page's head draws the three things itself
(components/hero-things.tsx), so there is no `hero-thing` picture any more.

## Make them all again

With the local stack running (web on :3000 with the seeded demo data):

```bash
pnpm --filter @handball/site shots
```

That runs both steps:

1. `capture.mjs` logs in with the demo account, opens the screens and saves them at twice the
   pixel density to `captures/*.webp`, with the boxes of what matters on each (found by role, text
   and test id) in `captures/captures.json`. Read-only: it opens dialogs but never answers a
   question, creates a link or changes data. The request to confirm the demo e-mail address is
   hidden in the picture.
2. `compose.mjs` places the captures into `templates/*.html` (one per picture, with `stage.css`
   and `stage.js`), photographs them with Chromium and writes `public/product/<name>.webp` and
   `<name>-2x.webp`, each at the best quality under its budget (100 KB for 1x, 150 KB for 2x).
   The sizes and the callouts (label point, spot, side, bend; in per cent) go to
   `src/lib/product-shots.json`. Rings and arrows follow the boxes from step 1, so a changed
   layout in the app moves them along.

Only the design changed, no new screens needed (no app, no network):

```bash
pnpm --filter @handball/site shots:compose
node apps/site/scripts/product-shots/compose.mjs --preview /tmp/shots   # plus PNGs with arrows
node apps/site/scripts/product-shots/capture.mjs video saison           # only these screens
```

Options by environment: `HB_APP_URL` (default `http://localhost:3000`), `HB_DEMO_EMAIL`,
`HB_DEMO_PASSWORD` (default the seeded demo login), `PLAYWRIGHT_CHROMIUM_PATH`, and
`HB_DEMO_HLS_DIR`: a folder with the match video as HLS, laid out like the video's media folder
(`hls/master.m3u8`, `hls/720p/index.m3u8`, `init.mp4`, `seg_*.m4s`, as the worker writes it), which
the capture plays instead of the app's. It is for a stack seeded before the demo footage changed:
render the match with `uv run python -m handball_vision.synthetic spiel.mp4 --seconds 60 --seed 13
--demo` (the third match of `scripts/seed.py`, the one «Spiel öffnen» leads to) and package it with
ffmpeg like `apps/worker` (`-f hls -hls_segment_type fmp4 -master_pl_name master.m3u8`). Running the app on
a second dev server (another port)? The API takes writes only from the origin it knows, so add
`HB_API_ORIGIN=http://localhost:3000`. Playwright comes from `apps/web` (`@playwright/test`), so
`pnpm install` is enough.

If a screen cannot be opened, capture.mjs keeps the old capture and exits with 1, naming it. A box
it cannot find is listed as «not found»; the template then uses a fallback spot and compose.mjs
warns. After either step, look at the pictures on the site at 390 and 1280 px.

## The pictures

| Picture | Shows | Where |
|---|---|---|
| `app-desktop` | browser, the whole app on a computer: a match with the video playing, the scenes of the phase, the three things, all goals on the timeline (no callouts, the page's caption says it) | start page, under the three things (S13) |
| `step-upload` | flat cut-out, «Video hochladen»: which match is the video from? first match ringed | step 2 (start page, «So funktioniert es», «Filmen») |
| `step-check` | flat pieces on the app's cloth: the picture with the four yellow points, «Passt das Spielfeld?» and «Passt» (ringed) | step 3 |
| `step-result` | flat cut-out, the first of the three things with its shots on the half court, ring on the shots | «So funktioniert es», step 4; «Über uns» |
| `get-video` | browser, a match: video, the scene that plays, all goals on the timeline | «So sieht es aus» |
| `get-search` | browser, «Szenen»: the search, the answer with its base, «Alle 24 abspielen» | «So sieht es aus» |
| `get-season` | browser, «Saison», cut below the title: what repeats, one bar per match, the shots on the court | «So sieht es aus» |
| `share` | phone, a collection: «So kommt es im Chat an» and «Link teilen» | «So sieht es aus», «Über uns», «Daten» |

## A new picture

Add `templates/<name>.html` (copy one that is close), a screen to `SHOTS` in `capture.mjs` if it
needs one, the callout texts under `product.<name>` in all three message files, and use
`<ProductShot name="<name>" …>` on the page. Keep the style: the steps as flat cut-outs at 640 x 620
(`S.piece`, `S.stage(…, { paper: true })` or `{ cloth: true }`), the others with the same phone size
(`PHONE_SCREEN` in `stage.js`) or a browser window, yellow rings with an ink edge, at most two
callouts, and each label short (it wraps at under half the picture's width). On a picture shown under 28rem wide arrows and labels
go and the words stand below it.
