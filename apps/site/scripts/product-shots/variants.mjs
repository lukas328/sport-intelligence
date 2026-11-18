/**
 * The variants of the app pictures: each language of the website (BEFUNDE-4, the app pictures in
 * de, fr and en) and, for some, each club colour (U45). capture.mjs photographs the app once per
 * language (the app's own translations, with the demo data's names in that language) and per
 * colour (the demo club set to it); compose.mjs writes <name>-<lang>.webp and
 * <name>-<lang>-<colour>.webp; the website takes the file of the page's language and of the shirt
 * the visitor picked (components/product-shot.tsx).
 */

/** the website's languages, with the app's locale (its NEXT_LOCALE cookie) for each */
export const LANGS = { de: "de-CH", fr: "fr", en: "en" };

/**
 * What the coach named in the demo data, in each language: a French coach calls his team «Hommes 1»
 * and the collection of the website's Tuesday «Fermer l'aile droite», as the chat preview of the
 * website says (share-preview.mjs). Club, opponents, players and every number stay the same.
 */
export const NAMES = {
  de: { team: "Herren 1", collection: "Aussen rechts zumachen" },
  fr: { team: "Hommes 1", collection: "Fermer l'aile droite" },
  en: { team: "Men 1", collection: "Close the right wing" },
};

/**
 * The website's eight shirts (src/lib/color.ts SHIRTS), each as the demo club's colour in the app
 * (first and second colour, as the website pairs them in components/kit.tsx).
 *
 * Green is not in the list: the demo club plays in its own pine green (DEMO_COLOUR, the files
 * without a colour in the name), which the website also shows for the shirt «green» (#12804a, a
 * shade apart). Blue is the app's palette blue: #1f4fd6, the site's shirt, is the blue the old
 * onboarding gave every club, which the app reads as «not chosen» and shows in slate
 * (apps/api core/colors.py, apps/web lib/color.ts CLUB_COLOURS).
 */
export const DEMO_COLOUR = ["#10684a", "#ffffff"];

export const COLOURS = {
  blue: ["#1d4ed8", "#ffffff"],
  red: ["#d3202e", "#ffffff"],
  yellow: ["#f6c500", "#17191c"],
  black: ["#17191c", "#ffffff"],
  white: ["#ffffff", "#17191c"],
  orange: ["#e8731a", "#ffffff"],
  purple: ["#5b2d8e", "#ffffff"],
};

/**
 * Where the captures of a language and colour lie: captures/ (German, green), captures/fr/,
 * captures/en/; a colour in captures/colours/<colour>/<lang>/, which stays out of the repository
 * for its size (.gitignore).
 */
export function captureDir(root, lang, colour) {
  if (colour) return `${root}/colours/${colour}/${lang}`;
  return lang === "de" ? root : `${root}/${lang}`;
}
