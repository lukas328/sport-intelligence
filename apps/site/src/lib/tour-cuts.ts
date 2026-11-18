/**
 * The figures of the live cut-outs of the app tour (BEFUNDE-4 U34, components/tour-cuts.tsx):
 * what the app shows at the places the tour pulls out of its pictures, so the cut-out and the
 * dimmed capture behind it say the same. The match comes from the demo match itself
 * (public/demo/match.json, the seeded app's last analysed match); the search and the season are
 * the seeded app's figures over its three matches with video (scripts/seed.py, README of
 * scripts/product-shots), the same the captures show. src/lib/tour-cuts.test.ts keeps them
 * together.
 */
import { demoGoals } from "@/lib/demo";
import { MATCH } from "@/lib/things";

/** «Szenen»: goals conceded over the right wing in the last three matches with video */
export const SEARCH = { n: 26, of: 77, percent: 34, last: { n: 11, of: 29 } } as const;

/** «Saison»: the same theme, one bar per match (oldest first), with the opponents' short names */
export const SEASON_BARS = [
  { name: "Rotdorn", n: 6 },
  { name: "Wirbelstern", n: 9 },
  { name: "Nachtwind", n: 11 },
] as const;

/** the collection of the website's Tuesday as the app shows it */
export const COLLECTION = { scenes: 4, length: "0:36" } as const;

export interface TourTimeline {
  /** every goal of the demo match: minute (0 to 60) and whose */
  goals: { minute: number; own: boolean }[];
  /** the scene the picture plays: the second goal conceded over the right wing */
  scene: { clock: string; minute: number };
  /** its phase, as the app groups the scenes («Minute 2 bis 9») */
  phase: [number, number];
  minutes: number;
}

/** The match of the picture «get-video»: its goals on one line and the scene that plays. */
export function tourTimeline(): TourTimeline {
  const goals = demoGoals(MATCH);
  const wing = goals.filter((g) => g.team === "opp" && g.zone === "ra").sort((a, b) => a.minute - b.minute);
  const scene = wing[1]!;
  return {
    goals: goals.map((g) => ({ minute: g.minute, own: g.team === "own" })),
    scene: { clock: scene.clock, minute: scene.minute },
    phase: [2, 9],
    minutes: 60,
  };
}
