# Pictures from the app

Screens of the real app for the website (start page, «So funktioniert es», «Über uns»). They show
the seeded demo club (HC Zürichsee, invented players, synthetic videos), never real people.

| File | Screen | Size |
|---|---|---|
| `ergebnis-phone.webp` | team start page on a phone, from the result down to the three things (taller than the screen; the site lets it scroll) | 390 px wide, 2x |
| `ergebnis.webp` | the same page on a computer | 1280 px |
| `hochladen-phone.webp` | «Video hochladen»: which match is the video from? | 390 px wide, 2x |
| `pruefen-phone.webp` | a question while checking (today «Passt das Spielfeld?») | 390 px wide, 2x |
| `video.webp` | a match, tab «Video»: video, timeline of goals, scene list | 1280 px |
| `szenen.webp` | «Szenen» with a search and its answer | 1280 px |
| `saison.webp` | «Saison», the top: what repeats | 1280 px |
| `teilen-phone.webp` | a collection: «So kommt es im Chat an» | 390 px wide, 2x |

## Make them again

After the app changed, with the local stack running (web on :3000 with seeded demo data):

```bash
node apps/site/scripts/app-screens.mjs              # all pictures
node apps/site/scripts/app-screens.mjs video saison # only these
```

Options by environment: `HB_APP_URL` (default `http://localhost:3000`), `HB_DEMO_EMAIL`,
`HB_DEMO_PASSWORD` (default the seeded demo login), `PLAYWRIGHT_CHROMIUM_PATH`. Playwright comes from
`apps/web` (`@playwright/test`), so `pnpm install` is enough.

The script only reads: it opens dialogs but never answers a question, creates a link or changes
data. It finds things by role, text and test id (`check-link`, `next-scene`), hides the Next.js dev
badge and writes WebP (quality 0.84) through the browser, so no image tool is needed. If a screen
cannot be found, that picture is left as it was and the script exits with 1, naming it.

Then look at the pictures (the alt texts in `src/messages/*.ts`, `home` and `how`, describe what they
show; adjust them if the screen changed) and build the site.
