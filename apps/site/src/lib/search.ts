import type { HelpEntry, HelpLocale } from "../../content/help";

/** Lower-case, accents removed: "Präsentation" and "praesentation" both match "prasentation". */
export function normalise(text: string): string {
  return text
    .toLowerCase()
    .replace(/ä/g, "ae")
    .replace(/ö/g, "oe")
    .replace(/ü/g, "ue")
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "");
}

/** Help articles matching every word of the query, title hits first. */
export function searchHelp(entries: HelpEntry[], locale: HelpLocale, query: string): HelpEntry[] {
  const words = normalise(query).split(/\s+/).filter(Boolean);
  if (!words.length) return entries;
  const scored = entries
    .map((e) => {
      const title = normalise(e.title[locale]);
      const text = normalise(`${e.title[locale]} ${e.summary[locale]} ${e.keywords[locale]} ${e.slug}`);
      if (!words.every((w) => text.includes(w))) return null;
      return { e, score: words.filter((w) => title.includes(w)).length };
    })
    .filter((x): x is { e: HelpEntry; score: number } => x !== null);
  return scored.sort((a, b) => b.score - a.score).map((x) => x.e);
}
