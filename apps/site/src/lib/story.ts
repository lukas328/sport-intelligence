/**
 * The start page tells one invented week (docs/ux-test/livegang/BEFUNDE-2.md, W22 to W28):
 * Saturday the demo match (public/demo/match.json) is lost 27:29, 11 of the 29 goals conceded come
 * over the right wing; Tuesday four scenes go to the team chat; three matches later the right
 * wing is closed: 3 of 26. Saturday comes from the demo match itself, so the numbers on the page
 * are the demo's; «three matches later» is drawn here, invented and marked so on the page.
 */
import type { Pt } from "@/components/anlauf/geometry";
import { demoGoals, outsideArea, SHOT_MIN, type Zone } from "@/lib/demo";
import { MATCH } from "@/lib/things";
import { threeThings } from "@/lib/three-things";

export interface StoryDot {
  at: Pt;
  /** one of the goals over the right wing */
  ra: boolean;
}

export interface StoryCourt {
  n: number;
  of: number;
  dots: StoryDot[];
}

/** Saturday: the demo match's goals conceded and its first thing (11 of 29 over the right wing). */
export function saturday(): StoryCourt & { score: string; zone: string } {
  const goals = demoGoals(MATCH);
  const first = threeThings(goals)[0]!;
  const conceded = goals.filter((g) => g.team === "opp");
  const { own, opp } = MATCH.stats.timeline.final;
  return {
    n: first.value,
    of: first.of ?? conceded.length,
    zone: first.zone ?? "ra",
    score: `${own}:${opp}`,
    dots: conceded.map((g) => ({ at: g.shot, ra: g.zone === first.zone })),
  };
}

/** Where goals come from, in half-court metres (goal at the top), and how many three matches later. */
const LATER: [Zone, Pt, number][] = [
  ["ra", [18.6, 2.6], 3],
  ["la", [1.4, 2.6], 4],
  ["rl", [4.8, 9.4], 4],
  ["rm", [10, 10.4], 4],
  ["rr", [15.2, 9.4], 4],
  ["kr", [10, 6.9], 4],
  ["rm", [10, 7.3], 3],
];

/** Three matches later: 3 of 26 over the right wing (invented, seeded, the same on every build). */
export function threeMatchesLater(): StoryCourt {
  let s = 20261117;
  const r = () => {
    s = (Math.imul(s, 1664525) + 1013904223) >>> 0;
    return s / 4294967296 - 0.5;
  };
  const dots: StoryDot[] = [];
  for (const [zone, [u, v], n] of LATER) {
    for (let i = 0; i < n; i++) {
      const wing = zone === "la" || zone === "ra";
      const p: Pt = [u + r() * (wing ? 1.4 : 3), v + r() * (wing ? 2.2 : 1.6)];
      const at = outsideArea([Math.max(0.4, Math.min(19.6, p[0])), Math.max(0.4, p[1])], SHOT_MIN);
      dots.push({ at, ra: zone === "ra" });
    }
  }
  return { n: dots.filter((d) => d.ra).length, of: dots.length, dots };
}

export interface StoryAnswer {
  /** goals conceded over the zone of the first thing, and all goals conceded */
  n: number;
  of: number;
  first: number;
  second: number;
  /** who scored them, most first: shirt number and goals */
  shooters: { number: number; n: number }[];
  /** goals conceded after a fast break (the training tip of the week) */
  fast: number;
}

/**
 * Sunday: the question to the assistant («Kamen die wirklich immer über rechts?») answered from
 * the demo match the way the app's assistant does it: the figures come from a query on the goals
 * conceded with their shot spot (apps/api services/assistant.py), never typed in by hand.
 */
export function sundayAnswer(): StoryAnswer {
  const goals = demoGoals(MATCH);
  const zone = threeThings(goals)[0]!.zone;
  const conceded = goals.filter((g) => g.team === "opp");
  const wing = conceded.filter((g) => g.zone === zone);
  const by = new Map<number, number>();
  for (const g of wing) if (g.number != null) by.set(g.number, (by.get(g.number) ?? 0) + 1);
  return {
    n: wing.length,
    of: conceded.length,
    first: wing.filter((g) => g.period === 1).length,
    second: wing.filter((g) => g.period !== 1).length,
    shooters: [...by].map(([number, n]) => ({ number, n })).sort((a, b) => b.n - a.n || a.number - b.number),
    fast: conceded.filter((g) => g.zone === "gs").length,
  };
}
