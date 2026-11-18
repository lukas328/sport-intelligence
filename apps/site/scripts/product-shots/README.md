# Product pictures

The pictures of the app on the website (start page, «So funktioniert es», «Über uns») are not raw
screenshots: real screens of the app, placed into designed pictures. The four steps of «So
funktioniert es» are no pictures at all (see «The four steps» below). The computer
pictures sit in a browser window, some on the club's Keil with a soft shadow; yellow rings mark
what matters. The arrows and their labels
are drawn by the website over the picture, as real text in the visitor's language
(`src/components/product-shot.tsx`, texts in `src/messages/*.ts` under `product`). They show the
seeded demo club (HC Tannengrün, invented players, synthetic videos), never real people, and only
what the app really shows. The demo club plays in the website's own pine green (`#10684a`, seed
and synthetic footage), so the pictures sit in the site's colours (cream, green, ink); when the
visitor picks another shirt, the pictures follow (see «Club colours»).

The website tells its story with the demo match (HC Tannengrün against TSV Nachtwind, lost
27:29, 11 of 29 conceded over the right wing; `scripts/make_demo.py`), and the seeded app tells the
same: `scripts/seed.py` takes that match's shots from `public/demo/match.json` as the events of its
last analysed match, our shooters from its squad, and adds the collection of the website's Tuesday
(«Aussen rechts zumachen», 4 scenes). So the pictures show the app as it is, with no number
changed while capturing: the match (56 goals, the three things 11, 5 and 9 scenes), the search over
the last three matches (26 of 77, 34 Prozent, «Gegen Nachtwind waren es 11 von 29»), the season
(bars 6, 9, 11 and 4, 0, 9) and the collection. A screen in `capture.mjs` may only `hide` what a
visitor would not see: an empty «Noch keine Notiz», and the clock of the synthetic clip, whose
picture the hall recording covers. Change the story in `make_demo.py`, then seed again
(the tests in `src/lib/story.test.ts` keep seed and website together). The start page's head draws
its film itself (components/hero-film.tsx).

The match video in the pictures of a match is a real hall recording, blurred past recognition
(`assets/halle.webp`, made with `blur-hall.py` from one frame of a test clip; no person, face,
number, text, logo or scoreboard can be recognised, the unblurred frame is never in the repository).
The synthetic demo clip of the seeded app is covered by it (`S.video` in `stage.js`), and the
website writes «Dein Spiel» over it in the visitor's language (`lettering` in
`src/lib/product-shots.json`, drawn by `components/product-shot.tsx`). Blur only where people
would be recognisable.

## Capture or component (the rule)

A product picture shows the real app, but not everything in it has to be a picture (BEFUNDE-4
U34, Lukas, 18.11.):

- **A capture** is the proof: the whole app frame as it really is (a browser window, a phone,
  the app at work), made by `capture.mjs` and `compose.mjs`, one per language. It may be dimmed
  when something stands in front of it.
- **A live component** is everything the page's text points at, and everything that must be
  readable, translated or in the visitor's shirt colour: built on the site in its fonts and
  tokens, after the app's look at that place (`apps/web` for reference), with the app's words in
  the message files and the captures' figures (`src/lib/tour-cuts.ts`, guarded by its test). It
  stays sharp at any size, speaks the page's language and wears the kit's CSS variables.

So a new picture asks first: is this the proof, or is this what we want the visitor to read? The
app tour (below) follows the rule: the capture steps back, its places come forward as components.
The four steps of «So funktioniert es» move to the same rule (work stream R8, BEFUNDE-4), so both
look and work alike. Small labels with arrows over a capture are the older way (`callouts`, still
used on «Über uns» and «Daten»); do not add new ones.

## The app tour: «Ausriss» (U34)

«So sieht es in der App aus» (`components/app-tour.tsx`) shows `get-video`, `get-search`,
`get-season` and `share` as Lukas' variant 3: the capture steps back (grey, pale, a little
smaller and to the right, `.tour-dim`), and the one or two places that carry its message come out
of it about twice as large, as cut-out cards that break over its edge, each with a yellow label
(`product.<picture>` in the messages) and a thin ink line to its place, which is outlined on the
picture. On the phone and in the calm version the cards stack under the picture, at a size that
reads. The places are boxes in the template (`S.mark(id, screen, box)`), written to the manifest
as `marks` in per cent; the cards are `components/tour-cuts.tsx`:

| Picture | Places (cards) |
|---|---|
| `get-video` | `tap`: the scene that plays, «5:01 Tor TSV Nachtwind, läuft gerade»; `timeline`: all 56 goals of the demo match on one line, ours in the club colour, the phase in yellow |
| `get-search` | `answer`: «26 von 77 Gegentoren über aussen rechts, 34 Prozent. Gegen Nachtwind waren es 11 von 29.»; `play`: «Alle 26 abspielen» |
| `get-season` | `bars`: «Gegentore über aussen rechts», its sentence, one bar per match: 6, 9, 11 |
| `share` | `chat`: the card in the team chat in the club colour, «Aussen rechts zumachen», «HC Tannengrün Herren 1 · 4 Szenen»; `nologin`: «Link teilen» |

Where each card sits on the stage is `PLACES` in `tour-cuts.tsx` (per cent of the figure; the
picture fills 10 to 100). Because the background is grey, it needs no club colours of its own:
the cards wear the visitor's shirt.

## Club colours (U45)

The visitor picks a shirt on the demo page, and the site wears it (links carry it on as `?kit=`). The app plays in its club's
colour, so a green capture would mix with a red page. How each picture follows the shirt:

- **The tour** (`get-*`, `share` on «So funktioniert es»): its capture is grey (`.tour-dim`), and
  the live cut-outs wear the shirt through the kit's CSS variables. No colour captures needed.
- **`app-desktop`** (start page; the club mark, the tabs, the
  legend and 27 marks on the timeline) and **`share`** («Über uns», «Daten»; the whole card in
  the team chat is the club's colour) are made in each shirt of `variants.mjs`:
  `<name>-<lang>-<colour>.webp`, app-desktop as one 2x file per colour (`colourDensities: [2]`,
  at most 300 KB), share as 1x and 2x. `ProductShot` passes the files of every colour to its
  client part (`components/shot-image.tsx`), which takes the one of `useShirt()`: only that one
  loads, the browser keeps the old picture until the new one is there, and without a pick or
  without JavaScript it is the green one. The shirt «green» is the demo club's own green.
- **The rest** (`video-phone`, `app-result`) stays green: the club colour hardly shows in them,
  and the repository stays small (seven colours times three languages is 21 files per picture).

To make the colour files: `capture.mjs --colours` (or `--colours=red,blue`) sets the demo club
to each colour of `variants.mjs` (its two colours and the shirt of its matches, as the club
settings do; blue is the app's palette blue, the site's #1f4fd6 reads as «not chosen» in the app),
photographs the screens of the app pictures in each language into
`captures/colours/<colour>/<lang>/` (not in the repository, about 9 MB per colour) and sets the
club back to its green at the end. Then `compose.mjs app-desktop share` makes the files; without
those captures it keeps the colour files as they are and says so (`--no-colours` skips them).
A template asks for its colours with `S.stage(…, { colours: true })`; its Keil takes the colour.

## The four steps

The steps of «So funktioniert es» (and the upload on «Filmen») are live components on the page,
not pictures (BEFUNDE-4 U47): `src/components/step-art.tsx` draws each step as cut-outs on the
page's own ground (the court as ink line art, the yellow and paper cards with the app's words,
the camera, the bell, the ball), in HTML and SVG, sharp at any size, with the words in
`src/messages/*.ts` under `how.art` and our players and the collection's head in the visitor's
shirt colour (kit variables). `src/components/ball-run.tsx` runs one ball path through the four.
Numbers and names are the demo story's (11 of 29 from `src/lib/story.ts`, 12 % of 3.4 GB, the
collection of 4 scenes); change them with the story. Nothing to make again here.

## Make them all again

With the local stack running (web on :3000 with the seeded demo data):

```bash
pnpm --filter @handball/site shots
```

That runs both steps:

1. `capture.mjs` logs in with the demo account, opens the screens and saves them to
   `captures/*.webp` (three times the pixel density for the screens of the large pictures, so
   their 3x files are drawn, not blown up), with the boxes of what matters on each (found by role,
   text and test id) in `captures/captures.json`. The screens of the app pictures (`app: true` in
   `SHOTS`) are taken once per language of `variants.mjs`: the app in German into `captures/`, in
   French into `captures/fr/`, in English into `captures/en/` (its own setting, the `NEXT_LOCALE`
   cookie; the words it is found by are in `WORDS`, from the app's message catalogues). For the
   other languages it names the team and the collection of the website's Tuesday as a coach of
   that language would («Hommes 1», «Fermer l'aile droite»; `NAMES`, the same as the chat preview)
   and sets them back to German at the end; club, opponents, players and every number stay.
   Otherwise read-only: it opens dialogs but never answers a question, creates a link or changes
   data. The request to confirm the demo e-mail address is hidden in the picture.
2. `compose.mjs` places the captures into `templates/*.html` (one per picture, with `stage.css`
   and `stage.js`), photographs them with Chromium and writes `public/product/<name>.webp`,
   `<name>-2x.webp` and, for the pictures the page shows large (`densities: [1, 2, 3]`),
   `<name>-3x.webp`. Each density is photographed at its own density and written at the best
   quality under its budget (110 KB for 1x, 300 KB for 2x, 560 KB for 3x; app-desktop sets its own), never under quality 0.82: a lower one left visible artefacts (U44). A
   picture of the app is made once per language from the captures in that language,
   `<name>-<lang>.webp`; a drawn one with words names its languages
   (`S.stage(…, { langs: ["de", "fr", "en"] })`) and is made once per language too.
   The sizes, densities and the callouts (label point, spot, side, bend; in per cent) go to
   `src/lib/product-shots.json`. Rings and arrows follow the boxes from step 1, so a changed
   layout in the app moves them along.

The page takes the file of its language (`appShot(name, locale)` in `src/lib/product-shots.ts`)
and tells the browser how wide each picture really is (`SHOT_SIZES`: the page's column, a narrow
column, the tour's stage, with the root font that grows from 1920 px, U4), so a screen with 1, 1.5
or 2 times the density loads a file at least that sharp. Measured with Playwright from 360 to
2560 px; only the tour on a 2560 px screen at 2x gets a little less (2160 px for 2670).

Only the design changed, no new screens needed (no app, no network):

```bash
pnpm --filter @handball/site shots:compose
node apps/site/scripts/product-shots/compose.mjs --preview /tmp/shots   # plus PNGs with arrows
node apps/site/scripts/product-shots/capture.mjs video saison           # only these screens
node apps/site/scripts/product-shots/capture.mjs --langs=fr video       # only in French
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
warns. After either step, look at the pictures on the site at 390, 1280 and 1920 px, in each language.

## The pictures

The app pictures (`app-desktop`, `video-phone`, `app-result`, `get-*`, `share`) exist in each
language, `<name>-{de,fr,en}`, the app's own words in them.

| Picture | Shows | Where |
|---|---|---|
| `app-desktop` | browser, the whole app on a computer: a match with the video playing, the scenes of the phase, the three things, all goals on the timeline (no callouts, the page's caption says it) | start page, under the three things (S13) |
| `video-phone` | the same match at phone width, two cut-outs on a clear ground: the video («Dein Spiel» written by the page) and under it four goals of the phase, the one playing in yellow | start page instead of `app-desktop` under 40rem (`<ProductShot phone="video-phone">`, a `<picture>` with its own size, U22) |
| `app-result` | one cut-out of the app on its cloth: the first of the three things, «11 von 29», «Gegentore über aussen rechts», the shots on the court ringed (until U33 the picture of step 4) | «Über uns» |
| `get-video` | browser, a match: video, the scene that plays, all goals on the timeline (no rings: the tour pulls them out) | «So sieht es aus» (Ausriss, U34) |
| `get-search` | browser, «Szenen»: the search, the answer with its base, «Alle 26 abspielen» | «So sieht es aus» (Ausriss) |
| `get-season` | browser, «Saison», cut below the title: what repeats, one bar per match, the shots on the court | «So sieht es aus» (Ausriss) |
| `share` | phone, a collection: «So kommt es im Chat an» and «Link teilen» (no rings since U34) | «So sieht es aus» (Ausriss), «Über uns», «Daten» (callouts) |

## The link preview in the team chat

Tuesday's chat on the start page (`src/components/phone-chat.tsx`) shows the preview a shared
collection gets in WhatsApp and co.: `public/media/teilen-vorschau-{de,fr,en}.webp`. It is not
drawn by hand: the app's own share picture renderer (`apps/web/src/lib/share/og-image.tsx`, the
same code that answers `/s/<token>/og`) renders it for the demo collection «Aussen rechts
zumachen» of HC Tannengrün Herren 1 (4 scenes, 1 minute), with the app's translations and the
title and team in each language («Fermer l'aile droite», «Hommes 1»; «Close the right wing», «Men
1»):

```bash
node apps/site/scripts/product-shots/share-preview.mjs
```

No app, database or network: the script loads the renderer with vite (from the app's vitest) and
writes the three WebP files at 640 px. Make them again whenever the renderer's design, the demo
club or the collection changes, and keep `home.chat.previewTitle` and `previewText` in
`src/messages` saying the same. `src/lib/names.test.ts` fails when a name of the earlier demo
(Zürichsee, Thalwil …) shows up in `public/` (text or file name), the messages, the content or
the templates; it cannot read pictures, which is why every picture with
words is made by a script.

## A new picture

First the rule above (Capture or component): what the visitor should read is a component, the
capture is its proof. Add `templates/<name>.html` (copy one that is close), a screen to `SHOTS` in `capture.mjs` if it
needs one, the callout texts under `product.<name>` in all three message files, and use
`<ProductShot name="<name>" …>` on the page. Keep the style: a cut-out of the
app (`app-result`) on the app's cloth (`{ cloth: true }`, a narrow phone screen, `PHONE_STEP` in
`capture.mjs`, `S.cut`) as large as the frame allows. The
others with the same phone size (`PHONE_SCREEN` in `stage.js`) or a browser window, yellow rings with an ink edge, at most two
callouts, and each label short (it wraps at under half the picture's width). On a picture shown under 28rem wide arrows and labels
go and the words stand below it.
