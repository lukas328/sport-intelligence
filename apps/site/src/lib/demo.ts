/**
 * The fictional demo match (public/demo/match.json, scripts/make_demo.py) in the shape the app
 * draws: goals with zone, shot spot and the scorer's run; the three things; one scene
 * for the tactics camera. Everything here is invented and marked so on the page. Shot positions,
 * goals, turnovers and the figures come from match.json (computed with the app's metrics code);
 * the runs and the scene are drawn from them by a seeded generator. Runs and positions are
 * handball-typical: no field player ever stands in a goal area (tested). The scene shows the ball
 * in every frame.
 */
import type { GoalRun } from "@/components/anlauf/bundle";
import type { ReportGoal } from "@/components/anlauf/flight-layout";
import { sampleAt, smooth, type Pt } from "@/components/anlauf/geometry";
import type { BallStretch, CameraScene, SceneTrack } from "@/components/anlauf/tactics-camera";
import { COURT } from "@handball/court";

export interface DemoEvent {
  id: string;
  type: string;
  side: "own" | "opponent";
  period: number;
  clock_s: number;
  x: number | null;
  y: number | null;
  outcome: string | null;
  shot_type: string | null;
  number: number | null;
  xg: number | null;
}

interface TeamBlock {
  goals: number;
  shots: number;
  shooting_pct: number | null;
  saves: number;
  turnovers: number;
  seven_m_goals: number;
  seven_m_shots: number;
  fast_break_goals: number;
}

export interface DemoMatch {
  fictional: boolean;
  own: string;
  opponent: string;
  events: DemoEvent[];
  stats: {
    own: TeamBlock;
    opponent: TeamBlock;
    timeline: { final: { own: number; opp: number }; score: { clock_s: number; own: number; opp: number }[] };
  };
}

export type Zone = "la" | "ra" | "rl" | "rm" | "rr" | "kr" | "m7" | "gs";

export interface DemoGoal extends GoalRun {
  id: string;
  minute: number;
  /** "39:55" */
  clock: string;
  period: number;
  number: number | null;
  zone: Zone;
}

export function clockOf(seconds: number): string {
  return `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, "0")}`;
}

/** Seeded random numbers (same sequence on server and client). */
function rng(seed: number) {
  let s = seed >>> 0 || 1;
  return () => {
    s = (Math.imul(s, 1664525) + 1013904223) >>> 0;
    return s / 4294967296;
  };
}

function seedOf(id: string): number {
  let h = 2166136261;
  for (const c of id) h = Math.imul(h ^ c.charCodeAt(0), 16777619);
  return h >>> 0;
}

/** Shot spot on the half court (goal at the top): every team attacks towards x = 40 in match.json. */
export function halfSpot(x: number, y: number): Pt {
  return [20 - y, 40 - x];
}

/** The position a goal came from, as a coach names it. */
export function zoneOf(shotType: string | null, spot: Pt): Zone {
  const u = spot[0];
  if (shotType === "penalty") return "m7";
  if (shotType === "fast_break") return "gs";
  if (shotType === "pivot") return "kr";
  if (shotType === "wing" || shotType === "empty_net") return u < 10 ? "la" : "ra";
  return u < 7.5 ? "rl" : u > 12.5 ? "rr" : "rm";
}

const clamp = (p: Pt): Pt => [Math.max(0.3, Math.min(19.7, p[0])), Math.max(0.3, Math.min(19.8, p[1]))];

/* The goal area (6 m around the goal, packages/court) belongs to the goalkeeper. Field players
 * jump into it at most when they shoot; their take-off spot and every run stay outside. */
const POST_L = COURT.width / 2 - COURT.goal.width / 2;
const POST_R = COURT.width / 2 + COURT.goal.width / 2;
/** Shot spots, runs and positions keep at least this far from the goal (metres). */
export const SHOT_MIN = COURT.goalAreaRadius + 0.3;
const FIELD_MIN = COURT.goalAreaRadius + 0.4;
const DEFENCE_MIN = COURT.goalAreaRadius + 0.5;

/** Distance of a half-court spot (u across, v from the goal line) to the goal. */
export function goalDistance(p: Pt): number {
  return Math.hypot(p[0] - Math.min(POST_R, Math.max(POST_L, p[0])), p[1]);
}

/** Push a spot straight away from the goal until it is at least `min` metres away. */
export function outsideArea(p: Pt, min: number = FIELD_MIN): Pt {
  const d = goalDistance(p);
  if (d >= min) return p;
  const g: Pt = [Math.min(POST_R, Math.max(POST_L, p[0])), 0];
  if (d < 1e-6) return [p[0], min];
  return [g[0] + ((p[0] - g[0]) * min) / d, g[1] + ((p[1] - g[1]) * min) / d];
}

/** The scorer's last metres before the shot, invented to fit the zone (as in the Zielbild demo). */
function runTo(zone: Zone, shot: Pt, R: () => number): Pt[] {
  const [u, v] = shot;
  let pts: Pt[];
  if (zone === "la" || zone === "ra") {
    const side = zone === "la" ? -1 : 1;
    pts = [[u + side * (0.2 + R() * 0.6), v + 6 + R() * 4], [u + side * (0.6 + R()), v + 3 + R() * 1.5], [u - side * R() * 0.6, v + 1.2], [u, v]];
  } else if (zone === "gs") {
    const u0 = 3 + R() * 14;
    pts = [[u0, 19.6], [u0 + (u - u0) * 0.35 + (R() - 0.5) * 2, 14 + R() * 2], [u + (R() - 0.5) * 1.5, v + 3.5], [u, v]];
  } else if (zone === "kr") {
    const s = R() < 0.5 ? -1 : 1;
    pts = [[u + s * (2.5 + R() * 2), v + 0.4 + R() * 0.6], [u + s * (1.2 + R()), v + 0.2 + R() * 0.5], [u + s * 0.4, v + 0.1], [u, v]];
  } else if (zone === "m7") {
    pts = [[u, v + 2.2], [u, v + 1.1], [u, v]];
  } else {
    const dx = (R() - 0.5) * 7;
    pts = [[u + dx, v + 4.5 + R() * 3], [u + dx * 0.55, v + 2.6 + R()], [u + dx * 0.15, v + 0.9], [u, v]];
  }
  // the scorer takes off before the 6 m line: no point of a run lies in the goal area
  return pts.map((p, i) => (i === pts.length - 1 ? p : clamp(outsideArea(clamp(p)))));
}

/** Every goal of the match with its zone and run, all confirmed: the demo shows a match after «Prüfen». */
export function demoGoals(match: DemoMatch): DemoGoal[] {
  return match.events
    .filter((e) => e.type === "shot" && e.outcome === "goal" && e.x !== null && e.y !== null)
    .map((e) => {
      const R = rng(seedOf(e.id));
      const spot = clamp(halfSpot(e.x!, e.y!));
      const shot = e.shot_type === "penalty" ? spot : outsideArea(spot, SHOT_MIN);
      const zone = zoneOf(e.shot_type, shot);
      return {
        id: e.id,
        team: e.side === "own" ? "own" : "opp",
        minute: e.clock_s / 60,
        clock: clockOf(e.clock_s),
        period: e.period,
        number: e.number,
        zone,
        run: runTo(zone, shot, R),
        shot,
        aim: [8.8 + R() * 2.4, 0] as Pt,
        confirmed: true,
      };
    });
}

/** The goal sequence of the match report: what the Wurf head and the rail draw. */
export function reportGoals(goals: readonly DemoGoal[]): ReportGoal[] {
  return goals.map((g) => ({ minute: g.minute, team: g.team }));
}

/* ---------------------------------------------------------------------------------------------
 * The scenes on the tactics camera: the attack plays towards the goal at x = 0 and scores.
 * Everything is invented, but it moves like handball, and every scene is its own play (BEFUNDE-4
 * U40), drawn from a seed taken from its time in the match, so it is the same on every visit:
 * - attack around 9 m: backs (RL, RM, RR) at 9 to 11 m, wings near the sidelines, the pivot just
 *   outside the 6 m line between two defenders; each stands a little differently in each scene;
 * - the build-up: two to four passes from one of the backs, now and then a crossing run or a
 *   block by the pivot, with its own timing; the scorer catches and takes off at his shot spot;
 * - defence 6:0 just in front of the 6 m line, shifting towards the ball a moment late, the
 *   defender at the ball steps out; for a goal from the wing the defender on that wing moves in
 *   to help before the last pass, so the wing catches free (the first thing's pattern);
 * - only the goalkeeper stands in the goal area;
 * - the ball is always shown: in an invented match we know where it is.
 * Numbers only on some players: the analysis reads about one in four (the ball carriers here).
 * ------------------------------------------------------------------------------------------- */

/** Half court (u across, v from the goal line) to court metres with the goal at x = 0. */
const toCourt = (p: Pt): Pt => [p[1], p[0]];

const SCENE_SECONDS = 6;
const SAMPLES = 25; // one point every quarter second

type Slot = "la" | "rl" | "rm" | "rr" | "ra" | "kr";
const SLOT_NAMES: Slot[] = ["la", "rl", "rm", "rr", "ra", "kr"];
/** Where the attack stands, in half-court metres: [across from, across to, depth from, depth to]. */
const SLOT_RANGE: Record<Slot, [number, number, number, number]> = {
  la: [0.5, 1.6, 2.2, 4.6],
  rl: [3.6, 5.4, 9.0, 10.8],
  rm: [8.8, 11.2, 9.9, 11.8],
  rr: [14.6, 16.4, 9.0, 10.8],
  ra: [18.4, 19.5, 2.2, 4.6],
  kr: [8.0, 12.0, 7.0, 7.7],
};
/** A 6:0 defence, each at about 7 m (outside the area), left to right as the attacker sees it. */
const DEFENCE: Pt[] = [
  [2.6, 3.8],
  [5.0, 6.2],
  [8.4, 7.0],
  [11.6, 7.0],
  [15.0, 6.2],
  [17.4, 3.8],
];
/** Who can pass to whom: neighbours on the 9 m line, the pivot from the backs. */
const NEIGHBOURS: Record<Slot, Slot[]> = {
  la: ["rl"],
  rl: ["la", "rm", "kr"],
  rm: ["rl", "rr", "kr"],
  rr: ["rm", "ra", "kr"],
  ra: ["rr"],
  kr: ["rl", "rm", "rr"],
};
/** Who plays the last pass to the scorer (a wing now and then gets the long pass from RM). */
const FEEDERS: Record<Slot, Slot[]> = {
  la: ["rl", "rl", "rl", "rm"],
  rl: ["rm", "rm", "la", "kr"],
  rm: ["rl", "rr", "kr"],
  rr: ["rm", "rm", "ra", "kr"],
  ra: ["rr", "rr", "rr", "rm"],
  kr: ["rl", "rm", "rr"],
};

const lerp = (a: Pt, b: Pt, f: number): Pt => [a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f];
const ease = (f: number) => (f <= 0 ? 0 : f >= 1 ? 1 : f * f * (3 - 2 * f));
const between = (R: () => number, a: number, b: number) => a + (b - a) * R();
const pick = <T>(R: () => number, xs: readonly T[]): T => xs[Math.floor(R() * xs.length) % xs.length]!;

/** Our squad by position (scripts/seed.py): who stands where when we attack. */
const OWN_AT: Record<Slot, number> = { la: 3, rl: 7, rm: 9, rr: 10, ra: 5, kr: 11 };
/**
 * Our 6:0, left to right as the attacker sees it: right wing, right half, two in the middle, left
 * half, left wing. Number 3 (our left wing) stands against their right wing, the first thing.
 */
const OWN_DEFENCE = [5, null, 11, 9, null, 3];
const OPP_DEFENCE = [4, null, 8, 15, null, 2];

/** The seed of a scene: its time in the match and the side that scored (U40). */
function sceneSeed(goal: DemoGoal): number {
  return seedOf(`scene-${Math.round(goal.minute * 60)}-${goal.team}`);
}

/**
 * The build-up as the holders one after the other, ending with the scorer: built backwards from
 * him, two to four passes, no pass straight back, the pivot at most once.
 */
function buildUp(scorer: Slot, R: () => number): Slot[] {
  const passes = 2 + Math.floor(R() * 3);
  const chain: Slot[] = [scorer, pick(R, FEEDERS[scorer])];
  while (chain.length < passes + 1) {
    const cur = chain[chain.length - 1]!;
    const after = chain[chain.length - 2]!;
    const options = NEIGHBOURS[cur].filter((s) => s !== after && s !== scorer && !(s === "kr" && chain.includes("kr")));
    if (options.length === 0) break;
    chain.push(pick(R, options));
  }
  const play = chain.reverse();
  // the build-up starts with a back (or the pivot playing it out), never with a wing
  while (play.length > 2 && (play[0] === "la" || play[0] === "ra")) play.shift();
  return play;
}

/**
 * One goal of the demo match on the tactics camera. The attack plays towards the goal at x = 0,
 * whoever attacks: their goals against our 6:0, ours against theirs, and a goal after a fast break
 * as a sprint from the middle line with nobody back in time.
 */
export function demoScene(goal: DemoGoal, label: string): CameraScene {
  if (goal.zone === "gs") return fastBreakScene(goal, label);
  const att = goal.team;
  const def: "own" | "opp" = att === "opp" ? "own" : "opp";
  const R = rng(sceneSeed(goal));
  const scorerSlot: Slot = goal.zone in SLOT_RANGE ? (goal.zone as Slot) : "rm";
  const slots = Object.fromEntries(SLOT_NAMES.map((s) => {
    const [u0, u1, v0, v1] = SLOT_RANGE[s];
    return [s, [between(R, u0, u1), between(R, v0, v1)] as Pt];
  })) as Record<Slot, Pt>;
  const play = buildUp(scorerSlot, R);
  const scorerNumber = goal.number ?? 5;

  // numbers: the ball carriers and one more, never the scorer's number twice
  const numberOf = new Map<Slot, number | null>(SLOT_NAMES.map((s) => [s, null]));
  const carriers = [...new Set(play.slice(0, -1))].filter((s) => s !== scorerSlot);
  const extra = (["kr", "la", "ra"] as Slot[]).find((s) => !play.includes(s));
  const numbered = [...carriers, ...(extra ? [extra] : [])];
  const spare = [13, 17, 19, 21];
  const pool = [9, 14, 22, 18, 11, 3, 7, 20].filter((n) => n !== scorerNumber);
  numbered.forEach((s, i) => {
    if (att === "own") numberOf.set(s, OWN_AT[s] !== scorerNumber ? OWN_AT[s] : spare[i % spare.length]!);
    else numberOf.set(s, pool[(i + Math.floor(R() * 2)) % pool.length]!);
  });
  // two carriers never share a number
  const seen = new Set<number>([scorerNumber]);
  for (const s of numbered) {
    let n = numberOf.get(s)!;
    while (seen.has(n)) n = spare.find((x) => !seen.has(x)) ?? n + 30;
    seen.add(n);
    numberOf.set(s, n);
  }
  numberOf.set(scorerSlot, scorerNumber);

  // ball schedule: the scorer catches between 3.4 and 4.6 s; before that each holder keeps the
  // ball a little longer or shorter, and a longer pass flies a little longer
  const receivedAt = round2(between(R, 3.4, 4.6));
  const flights = play.slice(1).map((s, i) => {
    const a = slots[play[i]!];
    const b = slots[s];
    return Math.min(0.6, Math.max(0.3, 0.22 + Math.hypot(a[0] - b[0], a[1] - b[1]) * 0.03));
  });
  const weights = play.slice(0, -1).map(() => between(R, 0.6, 1.4));
  const holdTotal = receivedAt - flights.reduce((n, f) => n + f, 0);
  const wsum = weights.reduce((n, w) => n + w, 0);
  const ball: BallStretch[] = [];
  let at = 0;
  play.forEach((s, i) => {
    const last = i === play.length - 1;
    const from = last ? receivedAt : at;
    const to = last ? SCENE_SECONDS : at + (holdTotal * weights[i]!) / wsum;
    ball.push({ from: round2(from), to: round2(to), team: att, number: numberOf.get(s)! });
    if (!last) at = to + flights[i]!;
  });
  const times = Array.from({ length: SAMPLES }, (_, i) => (i / (SAMPLES - 1)) * SCENE_SECONDS);
  const stretchAt = (sec: number) => ball.findIndex((b) => sec >= b.from && sec <= b.to);
  const holderAt = (sec: number): Slot | null => {
    const i = stretchAt(sec);
    return i < 0 ? null : play[i]!;
  };
  /** Across position of the ball from the schedule alone (holder's slot, or between two on a pass). */
  const ballSide = (sec: number): number => {
    const h = holderAt(sec);
    if (h) return slots[h][0];
    const i = ball.findIndex((b) => b.from > sec);
    if (i <= 0) return slots[play[0]!][0];
    const f = (sec - ball[i - 1]!.to) / (ball[i]!.from - ball[i - 1]!.to);
    return slots[play[i - 1]!][0] + (slots[play[i]!][0] - slots[play[i - 1]!][0]) * f;
  };

  // a crossing run now and then: a back with the ball runs diagonally towards the next receiver,
  // who comes round behind him; and now and then the pivot sets a block for the last passer
  const crosses = play.slice(0, -1).map((s, i) => s !== "kr" && play[i + 1] !== "kr" && play[i + 1] !== scorerSlot && R() < 0.35);
  const feeder = play[play.length - 2]!;
  const block = scorerSlot !== "kr" && !play.includes("kr") && R() < 0.5;
  const blockFrom = receivedAt - between(R, 1.2, 2.0);
  const blockAt: Pt = [slots[feeder][0] + (10 - slots[feeder][0]) * 0.18 + (feeder === "rm" ? between(R, -1, 1) : 0), between(R, 7.0, 7.6)];
  // the scorer's approach: a wing comes up from the corner, a back steps into the gap
  const runStart = receivedAt - between(R, 0.4, 0.9);

  const shot = outsideArea(goal.shot, SHOT_MIN);
  const wobble = () => (R() - 0.5) * 0.3;
  const attack = new Map<Slot, Pt[]>();
  for (const s of SLOT_NAMES) {
    const home = slots[s];
    const pts = times.map((sec): Pt => {
      if (s === scorerSlot && sec >= runStart) {
        const f = ease((sec - runStart) / (SCENE_SECONDS - runStart));
        return lerp(home, shot, f);
      }
      const i = stretchAt(sec);
      const holding = i >= 0 && play[i] === s;
      if (s === "kr" && !holding) {
        // the pivot stays between the two middle defenders, who shift with the ball, or blocks
        const base: Pt = [home[0] + (ballSide(sec) - home[0]) * 0.2, home[1]];
        const p = block && sec >= blockFrom ? lerp(base, blockAt, ease((sec - blockFrom) / 0.8)) : base;
        return [p[0] + wobble() * 0.5, p[1] + wobble() * 0.5];
      }
      if (holding) {
        // the holder goes at the defence during his hold: a wing up the line, a back at the gap,
        // on a crossing run diagonally towards the next receiver
        const b = ball[i]!;
        const f = ease((sec - b.from) / Math.max(0.3, b.to - b.from));
        const next = play[i + 1];
        const toward: Pt =
          s === "la" || s === "ra"
            ? [home[0] + (s === "la" ? 0.6 : -0.6), home[1] + 0.8]
            : crosses[i] && next
              ? [home[0] + (slots[next][0] - home[0]) * 0.4, home[1] - 1.6]
              : [home[0] + (10 - home[0]) * 0.08, home[1] - between(R, 1.0, 1.4)];
        const p = lerp(home, toward, f);
        return [p[0] + wobble() * 0.4, p[1] + wobble() * 0.4];
      }
      // the receiver of a crossing run comes round behind the passer
      const j = ball.findIndex((b) => b.from > sec);
      if (j > 0 && play[j] === s && crosses[j - 1]) {
        const passer = slots[play[j - 1]!];
        const f = ease(1 - (ball[j]!.from - sec) / 1.2);
        const p = lerp(home, [home[0] + (passer[0] - home[0]) * 0.3, home[1] + 0.6], f);
        return [p[0] + wobble(), p[1] + wobble()];
      }
      return [home[0] + wobble(), home[1] + wobble()];
    });
    const path = smoothSteps(pts).map((p) => outsideArea(p, FIELD_MIN));
    // the scorer ends exactly at his shot spot
    if (s === scorerSlot) path[path.length - 1] = shot;
    attack.set(s, path);
  }

  // the ball's spot at a time: at its holder, or in flight between two holders
  const attackAt = (s: Slot, sec: number): Pt => attack.get(s)![Math.round((sec / SCENE_SECONDS) * (SAMPLES - 1))]!;
  const ballSpot = (sec: number): Pt => {
    const c = Math.max(0, Math.min(SCENE_SECONDS, sec));
    const h = holderAt(c);
    if (h) return attackAt(h, c);
    const i = ball.findIndex((b) => b.from > c);
    if (i <= 0) return attackAt(play[0]!, 0);
    const a = ball[i - 1]!;
    const b = ball[i]!;
    return lerp(attackAt(play[i - 1]!, a.to), attackAt(play[i]!, b.from), (c - a.to) / (b.from - a.to));
  };

  // defence: each stands a little differently; the line shifts towards the ball a moment late,
  // the defender facing the ball steps out to it. On a goal from the wing, the defender on that
  // wing moves in to help against the last passer before the pass and is too late back out.
  const base = DEFENCE.map((p) => outsideArea([p[0] + between(R, -0.4, 0.4), p[1] + between(R, -0.4, 0.4)], DEFENCE_MIN));
  const lag = between(R, 0.2, 0.6);
  const shift = between(R, 0.15, 0.3);
  const stepOut = between(R, 0.25, 0.4);
  const wingDefender = scorerSlot === "ra" ? 5 : scorerSlot === "la" ? 0 : -1;
  const helpFrom = receivedAt - between(R, 1.0, 1.8);
  const helpDepth = between(R, 0.55, 0.8);
  const defence = base.map((home, k) =>
    times.map((sec) => {
      const b = ballSpot(sec - lag);
      let p: Pt = [home[0] + (b[0] - home[0]) * shift, home[1]];
      const nearest = base.reduce((best, d) => (Math.abs(d[0] - b[0]) < Math.abs(best[0] - b[0]) ? d : best));
      if (nearest === home && k !== wingDefender) p = lerp(p, b, stepOut);
      if (k === wingDefender && sec >= helpFrom) {
        const target: Pt = [slots[feeder][0] + (home[0] - slots[feeder][0]) * 0.15, Math.max(6.6, slots[feeder][1] - 2.4)];
        const inward = ease((sec - helpFrom) / 0.9) * helpDepth;
        const back = sec > receivedAt ? ease((sec - receivedAt) / 2.5) * 0.35 : 0;
        p = lerp(lerp(p, target, inward), p, back);
      }
      return outsideArea([p[0] + wobble() * 0.5, p[1] + wobble() * 0.5], DEFENCE_MIN);
    }),
  );
  const defNumbers = def === "own" ? OWN_DEFENCE : OPP_DEFENCE;

  const tracks: SceneTrack[] = [];
  for (const s of SLOT_NAMES) tracks.push({ team: att, number: numberOf.get(s) ?? null, xy: attack.get(s)!.map(toCourt) });
  defence.forEach((pts, i) => tracks.push({ team: def, number: defNumbers[i], xy: smoothSteps(pts).map(toCourt) }));
  // the goalkeeper, the only one in the goal area: moves with the ball between the posts
  tracks.push({
    team: def,
    number: def === "own" ? 1 : 16,
    keeper: true,
    xy: times.map((sec) => toCourt([Math.max(8.9, Math.min(11.1, 10 + (ballSpot(sec)[0] - 10) * 0.18)), 0.9])),
  });
  const refFrom = between(R, 12.5, 15);
  const refPace = between(R, 0.15, 0.35);
  tracks.push({ team: "ref", xy: times.map((sec) => [refFrom - sec * refPace, 0.9] as Pt) });

  return {
    clock: Math.max(0, Math.round(goal.minute * 60) - SCENE_SECONDS),
    duration: SCENE_SECONDS,
    tracks,
    ball,
    scorer: { team: att, number: scorerNumber },
    shot: toCourt(shot),
    aim: toCourt(goal.aim ?? [10, 0]),
    confirmed: goal.confirmed,
    label,
  };
}

/**
 * A goal after a fast break: the ball is lost in the other half, the scorer sprints from about the
 * middle line along his own run (the same run the bundle draws), a team-mate runs with him on the
 * other side, two of the side that lost the ball chase and stay behind, the goalkeeper waits alone.
 * Each scene its own (U40): the team-mate's side and depth, the chasers, the pace, and in about
 * half of them the team-mate starts with the ball and throws the long pass to the scorer.
 */
function fastBreakScene(goal: DemoGoal, label: string): CameraScene {
  const att = goal.team;
  const def: "own" | "opp" = att === "opp" ? "own" : "opp";
  const R = rng(sceneSeed(goal));
  const times = Array.from({ length: SAMPLES }, (_, i) => (i / (SAMPLES - 1)) * SCENE_SECONDS);
  const shot = outsideArea(goal.shot, SHOT_MIN);
  const scorerNumber = goal.number ?? (att === "own" ? 5 : 7);
  // the scorer: his run from the bundle, the last metres a little slower (he takes off)
  const run = smooth(goal.run, 10);
  const along = (f: number): Pt => {
    const k = Math.max(0, Math.min(1, f)) * (run.length - 1);
    const i = Math.floor(k);
    return i >= run.length - 1 ? run[run.length - 1]! : lerp(run[i]!, run[i + 1]!, k - i);
  };
  const pace = between(R, 1.1, 1.5);
  const scorer = times.map((sec, i) => (i === times.length - 1 ? shot : outsideArea(along(1 - (1 - sec / SCENE_SECONDS) ** pace), FIELD_MIN)));
  const start = scorer[0]!;
  const side = start[0] < 10 ? 1 : -1;
  // the team-mate on the other side, a few metres behind or level
  const mateFrom: Pt = [Math.max(1.5, Math.min(18.5, start[0] + side * between(R, 4, 8))), Math.min(19.6, start[1] + between(R, -0.5, 3))];
  const mateTo: Pt = [Math.max(2, Math.min(18, shot[0] + side * between(R, 4, 7.5))), between(R, 8, 11)];
  const mate = times.map((sec) => outsideArea(lerp(mateFrom, mateTo, ease(sec / SCENE_SECONDS)), FIELD_MIN));
  // two chasers who lost the ball: behind the scorer all the way, never in time
  const chasers = [between(R, -2.6, -1), between(R, 1.4, 3)].map((du, j) => {
    const lagBack = between(R, 2.4, 4);
    const from: Pt = [Math.max(1, Math.min(19, start[0] + du)), Math.min(19.8, start[1] + 1.8 + j * between(R, 0.5, 1.5))];
    return times.map((sec) => {
      const f = sec / SCENE_SECONDS;
      const at = scorer[Math.min(times.length - 1, Math.round(f * (times.length - 1)))]!;
      const p: Pt = [from[0] + (at[0] + du * 0.6 - from[0]) * ease(f), from[1] + (at[1] + lagBack + j - from[1]) * f];
      return outsideArea(p, DEFENCE_MIN);
    });
  });
  const mateNumber = att === "own" ? (OWN_AT.ra === scorerNumber ? OWN_AT.la : OWN_AT.ra) : scorerNumber === 14 ? 20 : 14;
  // about half: the team-mate has the ball first and throws it long to the scorer
  const refFrom = between(R, 15.5, 18);
  const refPace = between(R, 1.0, 1.5);
  const longPass = R() < 0.5;
  const passAt = round2(between(R, 1.0, 2.0));
  const flight = 0.5;
  const ball: BallStretch[] = longPass
    ? [
        { from: 0, to: passAt, team: att, number: mateNumber },
        { from: round2(passAt + flight), to: SCENE_SECONDS, team: att, number: scorerNumber },
      ]
    : [{ from: 0, to: SCENE_SECONDS, team: att, number: scorerNumber }];
  const tracks: SceneTrack[] = [
    { team: att, number: scorerNumber, xy: scorer.map(toCourt) },
    { team: att, number: mateNumber, xy: smoothSteps(mate).map(toCourt) },
    ...chasers.map((pts, j) => ({ team: def, number: j === 0 ? (def === "own" ? 9 : 8) : null, xy: smoothSteps(pts).map(toCourt) })),
    {
      team: def,
      number: def === "own" ? 1 : 16,
      keeper: true,
      xy: times.map((sec) => {
        const b = scorer[Math.round((sec / SCENE_SECONDS) * (SAMPLES - 1))]!;
        return toCourt([Math.max(8.9, Math.min(11.1, 10 + (b[0] - 10) * 0.18)), 0.9]);
      }),
    },
    { team: "ref", xy: times.map((sec) => [refFrom - sec * refPace, 19.2] as Pt) },
  ];
  return {
    clock: Math.max(0, Math.round(goal.minute * 60) - SCENE_SECONDS),
    duration: SCENE_SECONDS,
    tracks,
    ball,
    scorer: { team: att, number: scorerNumber },
    shot: toCourt(shot),
    aim: toCourt(goal.aim ?? [10, 0]),
    confirmed: goal.confirmed,
    label,
  };
}

/**
 * Where to look in a scene (the website marks it in yellow, with a word): the scorer at the moment
 * he gets the ball, and the nearest player of the other side then. In the half court with the goal
 * at the top (the camera's `halfB` view), metres.
 */
export function sceneGap(scene: CameraScene): { at: Pt; near: Pt | null } | null {
  if (!scene.scorer) return null;
  const sc = scene.tracks.find((x) => x.team === scene.scorer!.team && x.number === scene.scorer!.number);
  if (!sc) return null;
  const last = scene.ball.at(-1);
  // a pass to the scorer: just after it arrives; a run with the ball all the way: before the shot
  const t = last && scene.ball.length > 1 ? Math.min(0.92, Math.max(0.45, last.from / scene.duration + 0.06)) : 0.85;
  const half = (p: Pt): Pt => [p[1], p[0]];
  const at = half(sampleAt(sc.xy, t));
  const others = scene.tracks.filter((x) => x.team !== "ref" && x.team !== scene.scorer!.team && !x.keeper).map((x) => half(sampleAt(x.xy, t)));
  const near = others.reduce<Pt | null>((best, p) => (best == null || Math.hypot(p[0] - at[0], p[1] - at[1]) < Math.hypot(best[0] - at[0], best[1] - at[1]) ? p : best), null);
  return { at, near };
}

const round2 = (v: number) => Math.round(v * 100) / 100;

/** A light moving average so that a path has no corners (the camera smooths it again). */
function smoothSteps(pts: Pt[]): Pt[] {
  return pts.map((p, i) => {
    const a = pts[Math.max(0, i - 1)]!;
    const b = pts[Math.min(pts.length - 1, i + 1)]!;
    return [(a[0] + 2 * p[0] + b[0]) / 4, (a[1] + 2 * p[1] + b[1]) / 4] as Pt;
  });
}

/** Figures for the table «Zahlen», each with its source (report, marked by hand). */
export function demoFigures(match: DemoMatch) {
  const { own, opponent } = match.stats;
  const pct = (b: TeamBlock) => (b.shooting_pct == null ? null : Math.round(b.shooting_pct * 100));
  return [
    { key: "goals", source: "report", own: own.goals, opp: opponent.goals },
    { key: "sevenM", source: "report", own: `${own.seven_m_goals}/${own.seven_m_shots}`, opp: `${opponent.seven_m_goals}/${opponent.seven_m_shots}` },
    { key: "shots", source: "marked", own: own.shots, opp: opponent.shots },
    { key: "shootingPct", source: "marked", own: pct(own), opp: pct(opponent) },
    { key: "saves", source: "marked", own: own.saves, opp: opponent.saves },
  ] as const;
}
