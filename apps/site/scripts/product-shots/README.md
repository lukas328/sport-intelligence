# Product pictures

The pictures of the app on the website (start page, «So funktioniert es», «Über uns») are not raw
screenshots: real screens of the app, placed into designed pictures with a device frame, the club
blue Keil behind it, a soft shadow and yellow rings on what matters. The arrows and their labels
are drawn by the website over the picture, as real text in the visitor's language
(`src/components/product-shot.tsx`, texts in `src/messages/*.ts` under `product`). They show the
seeded demo club (HC Zürichsee, invented players, synthetic videos), never real people, and only
what the app really shows.

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
`HB_DEMO_PASSWORD` (default the seeded demo login), `PLAYWRIGHT_CHROMIUM_PATH`. Running the app on
a second dev server (another port)? The API takes writes only from the origin it knows, so add
`HB_API_ORIGIN=http://localhost:3000`. Playwright comes from `apps/web` (`@playwright/test`), so
`pnpm install` is enough.

If a screen cannot be opened, capture.mjs keeps the old capture and exits with 1, naming it. A box
it cannot find is listed as «not found»; the template then uses a fallback spot and compose.mjs
warns. After either step, look at the pictures on the site at 390 and 1280 px.

## The pictures

| Picture | Shows | Where |
|---|---|---|
| `hero-laptop` | the team's start page after a match on a laptop (transparent around), ring on the shots of the first thing | start page, head (from 1024 px) |
| `hero-phone` | the same page on a phone, taller than the screen; the site runs it slowly down and back in its phone frame | start page head, «Über uns» |
| `step-upload` | phone, «Video hochladen»: which match is the video from? | step 2 (start page, «So funktioniert es») |
| `step-check` | phone, «Passt das Spielfeld?» with the four yellow points and «Passt» | step 3 |
| `step-result` | phone, the first of the three things with its shots on the half court | «So funktioniert es», step 4 |
| `get-video` | browser, a match: video, the scene that plays, all goals on the timeline | «Was du bekommst» 1, «So sieht es aus» |
| `get-search` | browser, «Szenen»: the search, the answer with its base, «Alle 24 abspielen» | «Was du bekommst» 2, «So sieht es aus» |
| `get-season` | browser, «Saison»: what repeats, one bar per match, the shots on the court | «Was du bekommst» 3, «So sieht es aus» |
| `share` | phone, a collection: «So kommt es im Chat an» and «Link teilen» | start page «Fürs Team», «So sieht es aus» |

## A new picture

Add `templates/<name>.html` (copy one that is close), a screen to `SHOTS` in `capture.mjs` if it
needs one, the callout texts under `product.<name>` in all three message files, and use
`<ProductShot name="<name>" …>` on the page. Keep the style: the same phone size (`PHONE_SCREEN`
in `stage.js`), the Keil, yellow rings with an ink edge, at most two callouts, and each label
short (it wraps at under half the picture's width). On a picture shown under 28rem wide the labels
turn into numbers with the words below it.
