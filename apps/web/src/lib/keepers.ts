/**
 * The own goalkeepers of a match (app review R4): only the own team, and only somebody who kept
 * goal. The match statistics credit every save to the keeper the source names (by person or by
 * shirt number) and gather the goals against without a named keeper as "unknown". A report that
 * names the wrong team can credit a save to one of our field players; while the roster marks its
 * goalkeepers (position TW), such a field player is no goalkeeper here. A number the roster does
 * not know stays a row of its own («#16, nicht im Kader»).
 */

export interface KeeperLike {
  side: "own" | "opponent";
  player_id: string | null;
  number: number | null;
  saves: number;
  faced: number;
}

export interface RosterLike {
  player_id: string;
  jersey_number: number | null;
  main_position?: string | null;
}

export function rosterOf<R extends RosterLike>(k: Pick<KeeperLike, "player_id" | "number">, roster: R[]): R | undefined {
  return k.player_id ? roster.find((r) => r.player_id === k.player_id) : k.number != null ? roster.find((r) => r.jersey_number === k.number) : undefined;
}

/** Own rows that carry only a shirt number get the roster's person of that number, so a
 * report's scorer or keeper is named like in the tables («Krause 6», not «#9 6»). */
export function withRosterIds<T extends { side: "own" | "opponent"; player_id: string | null; number: number | null }>(rows: T[], roster: RosterLike[]): T[] {
  return rows.map((r) => {
    if (r.side !== "own" || r.player_id != null || r.number == null) return r;
    const hit = roster.find((x) => x.jersey_number === r.number);
    return hit ? { ...r, player_id: hit.player_id } : r;
  });
}

/** The own goalkeepers of the match, the one with the most shots faced first. */
export function ownKeepers<T extends KeeperLike>(rows: T[], roster: RosterLike[]): T[] {
  const marked = roster.some((r) => r.main_position === "TW");
  return rows
    .filter((k) => {
      if (k.side !== "own" || (k.player_id == null && k.number == null)) return false;
      const r = rosterOf(k, roster);
      return !r || !marked || r.main_position === "TW";
    })
    .sort((a, b) => b.faced - a.faced || b.saves - a.saves);
}

/** The goals against credited to the shown keepers cover all of them: only then a column. */
export function againstCovered(keepers: { goals_against: number }[], goalsAgainst: number): boolean {
  return keepers.reduce((n, k) => n + k.goals_against, 0) === goalsAgainst;
}
