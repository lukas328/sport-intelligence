/**
 * Who plays a match and from whose point of view the app speaks about it (app review 19.11.,
 * BUG-01 to 07, 17, 18). The one place that decides it:
 * - a match of the team (kind match, training): our team is the own side, the screens say «Wir»,
 *   «Gegentore», «Eigene Tore»;
 * - an observed match (kind scouting, K3): our team does not play. In the data the other team takes
 *   the own side (`scouting_other`, kit_own), the observed opponent the other. Both teams go by
 *   name, nothing is «ours», and the account team never appears.
 * The order of the two teams is the same everywhere: the home team first.
 */
export type Perspective = "own" | "neutral";

export interface SidesMatch {
  kind?: string | null;
  scouting_other?: string | null;
  is_home?: boolean | null;
}

export interface MatchSides {
  perspective: Perspective;
  /** an observed match: no «Wir», no «Gegentore», no roster of the account team */
  neutral: boolean;
  /** the name of the data's own side: our team, or in an observed match the other team */
  own: string;
  /** the name of the data's opponent side */
  opp: string;
  /** the own side plays at home: it comes first in every pairing */
  ownHome: boolean;
  home: string;
  away: string;
}

export function perspectiveOf(match: SidesMatch): Perspective {
  return match.kind === "scouting" ? "neutral" : "own";
}

/**
 * The two sides of a match. `team` is our team's display name (see `ownName`), `opponent` the
 * opponent's, `otherFallback` the word for an observed match's other team while its name is
 * unknown.
 */
export function matchSides(match: SidesMatch, names: { team: string; opponent: string; otherFallback?: string }): MatchSides {
  const neutral = perspectiveOf(match) === "neutral";
  const own = neutral ? match.scouting_other?.trim() || names.otherFallback || "" : names.team;
  const opp = names.opponent;
  const ownHome = match.is_home !== false;
  return { perspective: neutral ? "neutral" : "own", neutral, own, opp, ownHome, home: ownHome ? own : opp, away: ownHome ? opp : own };
}

/** Two values of the own and the opponent side in the canonical order: the home team first. */
export function homeFirst<T>(sides: Pick<MatchSides, "ownHome">, own: T, opp: T): [T, T] {
  return sides.ownHome ? [own, opp] : [opp, own];
}

/** «Heimteam gegen Gästeteam», the pairing of heads, titles, lists and banners. */
export function pairing(sides: Pick<MatchSides, "home" | "away">, word: string): string {
  return `${sides.home} ${word} ${sides.away}`;
}

/**
 * The name of a side in a sentence such as «Tor {team}»: our side is «Wir» (`us`) in a match of
 * the team, every side goes by its name in an observed match.
 */
export function sideLabel(sides: Pick<MatchSides, "neutral" | "own" | "opp">, side: "own" | "opp" | "opponent", us: string): string {
  if (side === "own") return sides.neutral ? sides.own : us;
  return sides.opp;
}

/**
 * The result and the two names start with the opponent side: only in an observed match whose home
 * team is the data's opponent side (BUG-18, UI check 20.11.: «HSG Sturmfalke gegen SC Eisberg»
 * read 24:26 with Sturmfalke's 26 second). A match of the team keeps its own score first.
 */
export function oppFirst(sides: Pick<MatchSides, "neutral" | "ownHome"> | null | undefined): boolean {
  return Boolean(sides?.neutral && !sides.ownHome);
}
