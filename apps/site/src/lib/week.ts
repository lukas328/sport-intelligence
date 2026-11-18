/**
 * The demo page as one week of a coach (BEFUNDE-4 U32, «Von 27:29 zum Plan für Dienstag»): what
 * the pages draw, computed from the demo match (public/demo/match.json) so that every number is the
 * demo's own. Saturday: the run of the match and its turning point (the opponent's longest run from
 * the match report). Asking: three prepared questions, answered from the goals the way the app's
 * assistant does it (a query on the goals, never typed in). The next match: the season bar for
 * «aussen rechts», with invented follow-up matches, marked as an example on the page.
 */
import { demoGoals, type DemoGoal, clockOf } from "@/lib/demo";
import type { ScorePoint } from "@/lib/match-run";
import { laterCourt, saturday, threeMatchesLater, type StoryDot } from "@/lib/story";
import { MATCH } from "@/lib/things";
import { threeThings } from "@/lib/three-things";

export type { ScorePoint };

export interface PhaseGoal {
  id: string;
  clock: string;
  team: "own" | "opp";
  zone: DemoGoal["zone"];
  number: number | null;
}

export interface Phase {
  key: "before" | "run" | "after";
  from: number;
  to: number;
  fromClock: string;
  toClock: string;
  /** goals in the phase, ours and theirs */
  own: number;
  opp: number;
  /** the score when the phase ends */
  score: string;
  goals: PhaseGoal[];
}

const MATCH_SECONDS = 3600;

/**
 * Saturday in three phases: up to the last equaliser before the opponent's longest run, the run
 * itself (the turning point), and the rest of the match.
 */
export function matchPhases(): { score: ScorePoint[]; phases: Phase[]; half: string } {
  const score = MATCH.stats.timeline.score.map((s) => ({ clock_s: s.clock_s, own: s.own, opp: s.opp }));
  const best = (MATCH.stats.timeline as unknown as { best_run: { opponent: { from_s: number; goals: number } } }).best_run.opponent;
  const first = score.findIndex((s) => s.clock_s === best.from_s);
  const startAt = score[first - 1]!;
  const endAt = score[first + best.goals - 1]!;
  const goals = demoGoals(MATCH);
  const final = score.at(-1)!;
  const zero: ScorePoint = { clock_s: 0, own: 0, opp: 0 };
  const phase = (key: Phase["key"], a: ScorePoint, b: ScorePoint, to: number): Phase => ({
    key,
    from: a.clock_s,
    to,
    fromClock: clockOf(a.clock_s),
    toClock: clockOf(to),
    own: b.own - a.own,
    opp: b.opp - a.opp,
    score: `${b.own}:${b.opp}`,
    goals: goals
      .filter((g) => g.minute * 60 > a.clock_s && g.minute * 60 <= b.clock_s + 0.5)
      .map((g) => ({ id: g.id, clock: g.clock, team: g.team, zone: g.zone, number: g.number })),
  });
  const halfAt = score.filter((s) => s.clock_s <= MATCH_SECONDS / 2).at(-1)!;
  return {
    score,
    half: `${halfAt.own}:${halfAt.opp}`,
    phases: [phase("before", zero, startAt, startAt.clock_s), phase("run", startAt, endAt, endAt.clock_s), phase("after", endAt, final, MATCH_SECONDS)],
  };
}

export interface Answers {
  /** «Wann haben wir das Spiel verloren?»: the run and what came after */
  when: { from: string; to: string; before: string; after: string; run: string; rest: string; wing: number; n: number };
  /** «Was hat bei uns funktioniert?»: our goals from the circle, from the shots there */
  works: { n: number; of: number; shots: number; shooters: { number: number; n: number }[] };
}

/** Two of the three prepared questions (the first is the start page's, lib/story.ts sundayAnswer). */
export function preparedAnswers(): Answers {
  const { phases } = matchPhases();
  const run = phases[1]!;
  const before = phases[0]!;
  const after = phases[2]!;
  const goals = demoGoals(MATCH);
  const scored = threeThings(goals).find((t) => t.key === "scored_zone")!;
  const own = goals.filter((g) => g.team === "own");
  const circle = own.filter((g) => g.zone === scored.zone);
  const by = new Map<number, number>();
  for (const g of circle) if (g.number != null) by.set(g.number, (by.get(g.number) ?? 0) + 1);
  // the shots from the circle, from the events the way the app counts them (shot type «Kreis»)
  const shots = MATCH.events.filter((e) => e.type === "shot" && e.side === "own" && e.shot_type === "pivot").length;
  return {
    when: {
      from: run.fromClock,
      to: run.toClock,
      before: before.score,
      after: run.score,
      run: `${run.own}:${run.opp}`,
      rest: `${after.own}:${after.opp}`,
      wing: run.goals.filter((g) => g.team === "opp" && g.zone === "ra").length,
      n: run.goals.length,
    },
    works: {
      n: circle.length,
      of: own.length,
      shots,
      shooters: [...by].map(([number, n]) => ({ number, n })).sort((a, b) => b.n - a.n || a.number - b.number),
    },
  };
}

export interface SeasonMatch {
  /** the opponent; the first is the demo match, the others are invented follow-up matches */
  opp: string;
  n: number;
  of: number;
  example: boolean;
  dots: StoryDot[];
}

/** The invented matches after the demo match: opponent, goals conceded by position. */
const NEXT: [string, number, [string, number][]][] = [
  ["BSV Wirbelstern", 20261121, [["ra", 4], ["la", 3], ["rl", 4], ["rm", 4], ["rr", 4], ["kr", 3], ["rm", 3]]],
  ["TV Rotdorn", 20261128, [["ra", 4], ["la", 4], ["rl", 4], ["rm", 4], ["rr", 4], ["kr", 4], ["rm", 3]]],
];

/**
 * The season bar for «aussen rechts» (the app's Saison, «Was sich wiederholt»: one bar per match):
 * the demo match with 11 of 29, then three invented matches, the third the start page's «drei
 * Spiele später» (3 of 26). Invented and labelled as an example where it is shown.
 */
export function seasonRightWing(): SeasonMatch[] {
  const sat = saturday();
  const later = threeMatchesLater();
  return [
    { opp: MATCH.opponent, n: sat.n, of: sat.of, example: false, dots: sat.dots },
    ...NEXT.map(([opp, seed, table]) => {
      const c = laterCourt(seed, table);
      return { opp, n: c.n, of: c.of, example: true, dots: c.dots };
    }),
    { opp: "TV Silberpfeil", n: later.n, of: later.of, example: true, dots: later.dots },
  ];
}
