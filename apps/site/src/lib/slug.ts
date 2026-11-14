/** Anchor ids for headings: lower case, umlauts spelled out, everything else a hyphen. */
export function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/ä/g, "ae")
    .replace(/ö/g, "oe")
    .replace(/ü/g, "ue")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

/** The level-two headings of an MDX source («## …»), as they appear on the page. */
export function headingsOf(source: string): { id: string; text: string }[] {
  return [...source.matchAll(/^## (.+)$/gm)].map((m) => {
    const text = m[1]!.replace(/\*\*|`/g, "").trim();
    return { id: slugify(text), text };
  });
}
