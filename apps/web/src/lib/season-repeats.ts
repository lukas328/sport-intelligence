/**
 * Was sich wiederholt (SPEC 7.9): what comes back over the matches with video, as one bar per
 * match. Only measured goals count (lib/graphics.ts); a statement needs MIN_GOALS goals over the
 * season and at least two matches, as for the things of one match (lib/three-things.ts).
 */
import type { GoalRun } from "@/components/anlauf/bundle";
import { MIN_GOALS } from "./three-things";

export interface SeasonMatch<T extends GoalRun = GoalRun> {
  id: string;
  /** short opponent name under the bar */
  label: string;
  goals: T[];
  turnovers: number;
}

export interface ZoneRepeat<T extends GoalRun = GoalRun> {
  zone: string;
  team: "own" | "opp";
  /** goals of the zone per match, oldest first */
  series: number[];
  value: number;
  /** all goals of that side over the matches */
  of: number;
  /** the zone was the most frequent one in every match */
  everyMatch: boolean;
  /** rising from match to match */
  rising: boolean;
  goals: T[];
  rest: T[];
}

export interface Repeats<T extends GoalRun = GoalRun> {
  conceded: ZoneRepeat<T> | null;
  scored: ZoneRepeat<T> | null;
  turnovers: { series: number[]; total: number; median: number; outlier: number | null } | null;
  matches: number;
}

function counts<T extends GoalRun>(goals: T[], skip: string[]): Map<string, number> {
  const by = new Map<string, number>();
  for (const g of goals) if (g.zone && !skip.includes(g.zone)) by.set(g.zone, (by.get(g.zone) ?? 0) + 1);
  return by;
}

function zoneRepeat<T extends GoalRun>(matches: SeasonMatch<T>[], team: "own" | "opp", skip: string[]): ZoneRepeat<T> | null {
  const side = matches.map((m) => m.goals.filter((g) => g.team === team));
  const all = side.flat();
  const total = counts(all, skip);
  const best = [...total.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))[0];
  if (!best || best[1] < MIN_GOALS || matches.length < 2) return null;
  const [zone, value] = best;
  const series = side.map((gs) => gs.filter((g) => g.zone === zone).length);
  const everyMatch = side.every((gs) => {
    const c = counts(gs, skip);
    const top = Math.max(0, ...c.values());
    return top > 0 && (c.get(zone) ?? 0) === top;
  });
  const rising = series.length >= 3 && series.every((v, i) => i === 0 || v > series[i - 1]!);
  return { zone, team, series, value, of: all.length, everyMatch, rising, goals: all.filter((g) => g.zone === zone), rest: all.filter((g) => g.zone !== zone) };
}

export function seasonRepeats<T extends GoalRun>(matches: SeasonMatch<T>[]): Repeats<T> {
  const conceded = zoneRepeat(matches, "opp", ["m7", "gs"]);
  const scored = zoneRepeat(matches, "own", ["m7"]);
  let turnovers: Repeats<T>["turnovers"] = null;
  if (matches.length >= 2) {
    const series = matches.map((m) => m.turnovers);
    const sorted = [...series].sort((a, b) => a - b);
    const median = sorted[Math.floor((sorted.length - 1) / 2)]!;
    const max = Math.max(...series);
    // one match far above the others: name it instead of an average
    const outlier = series.filter((v) => v === max).length === 1 && max >= median * 1.3 && max - median >= 3 ? series.indexOf(max) : null;
    turnovers = { series, total: series.reduce((a, b) => a + b, 0), median, outlier };
  }
  return { conceded, scored, turnovers, matches: matches.length };
}

/** A short name for a bar: the first place name of the opponent (no club prefix, no "Au"). */
export function shortName(opponent: string): string {
  const words = opponent.split(/[\s-]+/).filter((w) => w.length > 2 && !/^(TV|TSV|BSV|SG|HC|HSG|SC|HV|TSG|KTV|SV|STV|GC|RTV|LK|FC)$/i.test(w));
  return words[0] ?? opponent;
}
