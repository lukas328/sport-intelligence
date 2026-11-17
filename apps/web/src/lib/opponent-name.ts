/**
 * One opponent, several spellings (review R7): handball.ch writes the same team as
 * «SG Felsegg/Lärchenwil 1» in the league and «SG Felsegg/Lärchenwil (M2)» in the cup, and a coach
 * may type «sg felsegg-lärchenwil». The key drops case, accents, punctuation, a bracketed
 * addition and the «1» of a club's first team; a second team («… 2») stays a team of its own.
 * Same rule as `opponent_key` in the API (integrations/handball_ch.py).
 */
export function opponentKey(name: string | null | undefined): string {
  return (name ?? "")
    .replace(/ß/g, "ss")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/\([^)]*\)/g, " ")
    .replace(/[^a-z0-9]+/g, " ")
    .trim()
    .replace(/\s+1$/, "")
    .replace(/\s+/g, "");
}

/** The same opponent under two spellings; never true for two empty names. */
export function sameOpponent(a: string | null | undefined, b: string | null | undefined): boolean {
  const x = opponentKey(a);
  return x !== "" && x === opponentKey(b);
}

/**
 * The row of a team in a league table: the same key first; otherwise one row whose name contains
 * the other (tables sometimes shorten names). Two such rows are no answer: «HC Farnwil» must not
 * pick «HC Farnwil 2» over «HC Farnwil».
 */
export function findTeamRow<R extends { name?: string | null }>(
  rows: R[],
  name: string | null | undefined,
): R | undefined {
  const key = opponentKey(name);
  if (!key) return undefined;
  const exact = rows.find((r) => opponentKey(r.name) === key);
  if (exact) return exact;
  const near = rows.filter((r) => {
    const k = opponentKey(r.name);
    return k !== "" && (k.includes(key) || key.includes(k));
  });
  return near.length === 1 ? near[0] : undefined;
}
