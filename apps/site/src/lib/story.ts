/**
 * The start page tells one invented week (docs/ux-test/livegang/BEFUNDE-2.md, W22 to W28):
 * Saturday the demo match (public/demo/match.json) is lost 16:18, 9 of the 18 goals conceded come
 * over the right wing; Tuesday four scenes go to the team chat; three matches later the right
 * wing is closed: 3 of 22. Saturday comes from the demo match itself, so the numbers on the page
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

/** Saturday: the demo match's goals conceded and its first thing (9 of 18 over the right wing). */
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
  ["rl", [4.8, 9.4], 3],
  ["rm", [10, 10.4], 3],
  ["rr", [15.2, 9.4], 4],
  ["kr", [10, 6.9], 3],
  ["rm", [10, 7.3], 2],
];

/** Three matches later: 3 of 22 over the right wing (invented, seeded, the same on every build). */
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
