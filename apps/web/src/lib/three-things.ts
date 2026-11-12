/**
 * Drei Dinge (SPEC 7.1, 7.2): three statements about one match, each with its numeral, its base
 * and the goals behind it, derived only from the measured goals (lib/graphics.ts). No statement
 * without enough goals: the rule of three (MIN_GOALS) and a share (MIN_SHARE) keep chance out.
 */
import type { GoalRun } from "@/components/anlauf/bundle";

export const MIN_GOALS = 3;
export const MIN_SHARE = 0.25;

export type ThingKey = "conceded_zone" | "conceded_fast_breaks" | "scored_zone";

export interface Thing {
  key: ThingKey;
  /** the big numeral */
  value: number;
  /** the base: all goals of that side (null for a count without base) */
  of: number | null;
  /** zone of the goals (la, ra, rl, rm, rr, kr, m7, gs) */
  zone: string | null;
  team: "own" | "opp";
  /** the goals of the thing, drawn as the bundle */
  goals: (GoalRun & { eventId?: string })[];
  /** the other goals of that side, faint behind */
  rest: (GoalRun & { eventId?: string })[];
}

function topZone<T extends GoalRun>(goals: T[], skip: string[] = []): [string, T[]] | null {
  const by = new Map<string, T[]>();
  for (const g of goals) if (g.zone && !skip.includes(g.zone)) by.set(g.zone, [...(by.get(g.zone) ?? []), g]);
  const best = [...by.entries()].sort((a, b) => b[1].length - a[1].length || a[0].localeCompare(b[0]))[0];
  return best ?? null;
}

/** Up to three things, the opponent's main way to score first (that is what a coach works on). */
export function threeThings<T extends GoalRun>(goals: T[]): Thing[] {
  const opp = goals.filter((g) => g.team === "opp");
  const own = goals.filter((g) => g.team === "own");
  const out: Thing[] = [];
  const conceded = topZone(opp, ["m7", "gs"]);
  if (conceded && conceded[1].length >= MIN_GOALS && conceded[1].length / opp.length >= MIN_SHARE) {
    out.push({ key: "conceded_zone", value: conceded[1].length, of: opp.length, zone: conceded[0], team: "opp", goals: conceded[1], rest: opp.filter((g) => g.zone !== conceded[0]) });
  }
  const breaks = opp.filter((g) => g.zone === "gs");
  if (breaks.length >= MIN_GOALS) {
    out.push({ key: "conceded_fast_breaks", value: breaks.length, of: opp.length, zone: "gs", team: "opp", goals: breaks, rest: opp.filter((g) => g.zone !== "gs") });
  }
  const scored = topZone(own, ["m7"]);
  if (scored && scored[1].length >= MIN_GOALS && scored[1].length / own.length >= MIN_SHARE) {
    out.push({ key: "scored_zone", value: scored[1].length, of: own.length, zone: scored[0], team: "own", goals: scored[1], rest: own.filter((g) => g.zone !== scored[0]) });
  }
  return out.slice(0, 3);
}
