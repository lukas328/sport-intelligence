/**
 * The name of a row of the match sheet (Spielbericht): the player's name, else the name the paper
 * sheet gives the number, else the shirt number. A row without a number is never «#?» (UI check
 * 20.11.): a goalkeeper (saves, no shots) is «Torhüter», anybody else «Spieler».
 */
export interface LabelRow {
  side: "own" | "opponent";
  player_id: string | null;
  number: number | null;
  saves?: number;
  shots?: number;
}

export function rowLabel(
  p: LabelRow,
  names: Record<string, string>,
  words: { keeper: string; player: string },
  sheet: Record<string, string> = {},
): string {
  // the number has its own column: the name goes without it
  const name = ((p.player_id && names[p.player_id]) || "").replace(/^#\d+\s+/, "");
  if (name) return name;
  if (p.number != null) return (p.side === "own" && sheet[String(p.number)]) || `#${p.number}`;
  return (p.saves ?? 0) > 0 && !(p.shots ?? 0) ? words.keeper : words.player;
}
