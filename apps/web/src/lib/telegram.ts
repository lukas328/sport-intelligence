/**
 * The facts of the match telegram (SPEC 7.2): only what the sources carry. A score sequence and
 * the half-time score need goals with a time; scorers and the keeper need the report's players.
 */

export interface ScorePoint {
  clock_s: number;
  own: number;
  opp: number;
}

/** The score at half time, or null when the goals have no times. */
export function halfScore(points: ScorePoint[], periodS: number, timed = true): [number, number] | null {
  if (!timed || points.length < 2 || !periodS) return null;
  let at: ScorePoint = points[0]!;
  for (const p of points) if (p.clock_s <= periodS) at = p;
  return [at.own, at.opp];
}

/** The score every `stepMin` minutes of play (as a report's «Torfolge»), each change once, the
 * final score last; empty without times. */
export function scoreSequence(points: ScorePoint[], periodS: number, periods = 2, timed = true, stepMin = 5): [number, number][] {
  if (!timed || points.length < 2) return [];
  const end = Math.max(periodS * periods, points.at(-1)!.clock_s);
  const out: [number, number][] = [];
  for (let s = stepMin * 60; s < end + stepMin * 60; s += stepMin * 60) {
    let at: ScorePoint = points[0]!;
    for (const p of points) if (p.clock_s <= s) at = p;
    const last = out.at(-1);
    if ((at.own || at.opp) && (!last || last[0] !== at.own || last[1] !== at.opp)) out.push([at.own, at.opp]);
  }
  const fin = points.at(-1)!;
  const last = out.at(-1);
  if (!last || last[0] !== fin.own || last[1] !== fin.opp) out.push([fin.own, fin.opp]);
  return out;
}

/** The surname of a full name, or the number. */
export function shortName(name: string | undefined, number: number | null): string {
  if (name?.trim()) return name.trim().split(/\s+/).at(-1)!;
  return number != null ? `#${number}` : "?";
}

interface ScorerRow {
  side: "own" | "opponent";
  player_id: string | null;
  number: number | null;
  goals: number;
  seven_m_goals: number;
}

/** Our best scorers, «Brunner 7» or «Graf 5 (2 vom 7-m)»: the seven metres in words, «5/2» read
 * as a fraction (UX test N25). */
export function topScorers(players: ScorerRow[], names: Record<string, string>, n = 3, seven: (k: number) => string = (k) => `/${k}`): string[] {
  return players
    .filter((p) => p.side === "own" && p.goals > 0)
    .sort((a, b) => b.goals - a.goals || (a.number ?? 99) - (b.number ?? 99))
    .slice(0, n)
    .map((p) => `${shortName(p.player_id ? names[p.player_id] : undefined, p.number)} ${p.goals}${p.seven_m_goals ? seven(p.seven_m_goals) : ""}`);
}

interface KeeperRow {
  side: "own" | "opponent";
  player_id: string | null;
  number: number | null;
  saves: number;
}

/** Our keeper with the most saves, or null when no save was recorded. */
export function mainKeeper(keepers: KeeperRow[], names: Record<string, string>): { name: string; saves: number } | null {
  const k = keepers.filter((x) => x.side === "own" && x.saves > 0).sort((a, b) => b.saves - a.saves)[0];
  return k ? { name: shortName(k.player_id ? names[k.player_id] : undefined, k.number), saves: k.saves } : null;
}

/** Where most events of the match come from: the report, the coach's marks, or the video. */
export function mainSource(sources: Record<string, number>): "report" | "marked" | "video" {
  const top = Object.entries(sources).sort((a, b) => b[1] - a[1])[0]?.[0] ?? "";
  if (["paper_report", "official_report", "official_feed"].includes(top)) return "report";
  if (top === "user_correction") return "marked";
  return "video";
}
