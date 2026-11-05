/** Player names as the match page shows them: "#7 Lisa Zimmerli", first name first, normal case. */

/** "#7 Lisa Zimmerli"; either part may be missing. */
export function playerLabel(
  number: number | null | undefined,
  name: string | null | undefined,
): string {
  return [number != null ? `#${number}` : null, name?.trim() || null].filter(Boolean).join(" ");
}

// name particles stay lower case inside a name ("Lea von Arx")
const PARTICLES = new Set(
  "von vom zu zum zur van der den de di da du del della la le dos das".split(" "),
);

const letters = (w: string) => (w.match(/\p{L}/gu) ?? []).length;
const isCaps = (w: string) =>
  letters(w) >= 2 && w === w.toLocaleUpperCase() && w !== w.toLocaleLowerCase();
const capitalise = (w: string) =>
  w
    .toLocaleLowerCase()
    .replace(/(^|[-'’])(\p{L})/gu, (_, sep: string, c: string) => sep + c.toLocaleUpperCase());

/**
 * A name from an official report or a score overlay in display form. Reports write the surname
 * in capitals, before or after the first name ("ZIMMERLI Lisa", "Amy HOCHREUTENER"): the first
 * name comes first and the surname loses its capitals ("Lisa Zimmerli"). Names without a word in
 * capitals stay as they are. For display only; the stored name is not changed.
 */
export function reportName(name: string | null | undefined): string {
  const words = (name ?? "").trim().split(/\s+/).filter(Boolean);
  const surname = words.filter(isCaps);
  if (surname.length === 0) return words.join(" ");
  const ordered = [...words.filter((w) => !isCaps(w)), ...surname];
  return ordered
    .map((w, i) => {
      if (!isCaps(w)) return w;
      const lower = w.toLocaleLowerCase();
      return i > 0 && PARTICLES.has(lower) ? lower : capitalise(w);
    })
    .join(" ");
}
