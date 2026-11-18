# Product pictures

The pictures of the app on the website (start page, «So funktioniert es», «Über uns») are not raw
screenshots: real screens of the app, placed into designed pictures. The four steps of «So
funktioniert es» are drawn instead (U33, after Lukas' design of 18.11.; see «The four steps»
below). The computer
pictures sit in a browser window, some on the club's Keil with a soft shadow; yellow rings mark
what matters. The arrows and their labels
are drawn by the website over the picture, as real text in the visitor's language
(`src/components/product-shot.tsx`, texts in `src/messages/*.ts` under `product`). They show the
seeded demo club (HC Tannengrün, invented players, synthetic videos), never real people, and only
what the app really shows. The demo club plays in the website's own pine green (`#10684a`, seed
and synthetic footage), so the pictures sit in the site's colours (cream, green, ink).

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
would be recognisable: the picture of step 3 («Passt das Spielfeld?») shows the hall drawn sharp
by `hall.js`, with the field the app proposes.

## The four steps

The steps of «So funktioniert es» share one square frame (640 x 640) and one look, after Lukas'
design: a dark court ground (the site's ink a step softer) with the club's green, big yellow
cards with heavy slanted numbers in the site's display font (Kanit), the step's word as a ghost in
the back, tilted cards with hard shadows, and one white line at the foot (Hanken Grotesk). They
are HTML and SVG, not captures, so they are sharp at 2x and carry their words in each language:
`templates/step-*.html` hold the texts for de, fr and en (`S.t`), with the app's own words for
what the app shows (its message catalogues: «Passt», «C'est bon», «Looks right» …), and compose.mjs
writes `step-<name>-<lang>.webp` and `-2x.webp`; `components/step-picture.tsx` takes the file in
the visitor's language. `steps.js` draws the courts (any projection: from above, turned, or a
camera's view through `hall.js`) and the shared pieces (`ghost`, `say`, `camera`, icons); the
styles are in `stage.css` under `#stage.steps`.

1. `step-film`: the whole court from above, a little turned, a defence 6-0 in green against the
   attack in white; the camera (yellow disc) at the centre line behind the near sideline, its
   light over the whole court and the dotted yellow line round both goals; «3m» on the big card;
   «Hoch an die Mittellinie. Beide Tore im Bild.» (Tried and set aside: the court in perspective
   from behind the camera, flat or high, and one half large; see the template's comment.)
2. `step-upload`: the sheet «Video hochladen», «Zu welchem Spiel gehört das Video?» with TSV
   Nachtwind (14. Nov., chosen, in ink) and SG Blitzfang, under the big yellow «12 %» with the bar
   and «420 MB von 3.4 GB»; a dotted ball path; the bell and «Handy weglegen. Die Glocke meldet
   sich.»
3. `step-check`: the hall from the stand (`hall.js` with the steps' palette), the light court,
   green goal areas, a few players, the proposed field in yellow with its four corner points; the
   card «Frage 1 von 1», «Passt das Spielfeld?», «Passt» and «Weiss nicht»; the tag «ein Tipp»;
   «Höchstens zehn Fragen pro Spiel.»
4. `step-result`: «11», «von 29», «Gegentore über aussen rechts», the half court with the demo
   match's 11 shot spots at the right wing (from `src/lib/story.ts`) and their way into the goal,
   the collection card «Aussen rechts zumachen», «4 Szenen», «HC Tannengrün Herren 1», «Link
   teilen».

Numbers and names are the demo story's (11 of 29, 12 % of 3.4 GB, the collection of 4 scenes);
change them with the story. No capture is needed: `pnpm --filter @handball/site shots:compose`
(or `compose.mjs step-film`) makes them again.

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
   `<name>-2x.webp`, each at the best quality under its budget (100 KB for 1x, 150 KB for 2x;
   the steps 70 and 120 KB). A template with words in the picture names its languages
   (`S.stage(…, { langs: ["de", "fr", "en"] })`) and is made once per language,
   `<name>-<lang>.webp`.
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
| `video-phone` | the same match at phone width, two cut-outs on a clear ground: the video («Dein Spiel» written by the page) and under it four goals of the phase, the one playing in yellow | start page instead of `app-desktop` under 40rem (`<ProductShot phone="video-phone">`, a `<picture>` with its own size, U22) |
| `step-film-{de,fr,en}` | drawn (see «The four steps»): the court from above, the camera at the centre line, its light over both goals, «3m» | «So funktioniert es», step 1 |
| `step-upload-{de,fr,en}` | drawn after the app: «Video hochladen» with the two matches, the yellow «12 %» with the bar, the bell | «So funktioniert es», step 2; «Filmen», «Danach: hochladen» |
| `step-check-{de,fr,en}` | drawn after the app: the hall with the proposed field in yellow, «Passt das Spielfeld?», «Passt», «Weiss nicht», «ein Tipp» | «So funktioniert es», step 3 |
| `step-result-{de,fr,en}` | drawn after the app: «11 von 29», the shot spots at the right wing, the collection «Aussen rechts zumachen» with «Link teilen» | «So funktioniert es», step 4 |
| `app-result` | one cut-out of the app on its cloth: the first of the three things, «11 von 29», «Gegentore über aussen rechts», the shots on the court ringed (until U33 the picture of step 4) | «Über uns» |
| `get-video` | browser, a match: video, the scene that plays, all goals on the timeline | «So sieht es aus» |
| `get-search` | browser, «Szenen»: the search, the answer with its base, «Alle 26 abspielen» | «So sieht es aus» |
| `get-season` | browser, «Saison», cut below the title: what repeats, one bar per match, the shots on the court | «So sieht es aus» |
| `share` | phone, a collection: «So kommt es im Chat an» and «Link teilen» | «So sieht es aus», «Über uns», «Daten» |

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
the templates (the words of the steps); it cannot read pictures, which is why every picture with
words is made by a script.

## A new picture

Add `templates/<name>.html` (copy one that is close), a screen to `SHOTS` in `capture.mjs` if it
needs one, the callout texts under `product.<name>` in all three message files, and use
`<ProductShot name="<name>" …>` on the page. Keep the style: a step at 640 x 640 on the dark
court ground (`S.stage(640, 640, { steps: true, langs: ["de", "fr", "en"] })`, `steps.js`), its
words in all three languages, one big yellow card, one white line at the foot; a cut-out of the
app (`app-result`) on the app's cloth (`{ cloth: true }`, a narrow phone screen, `PHONE_STEP` in
`capture.mjs`, `S.cut`) as large as the frame allows. The
others with the same phone size (`PHONE_SCREEN` in `stage.js`) or a browser window, yellow rings with an ink edge, at most two
callouts, and each label short (it wraps at under half the picture's width). On a picture shown under 28rem wide arrows and labels
go and the words stand below it.
