/**
 * The fictional demo match (public/demo/match.json, scripts/make_demo.py) in the shape the app
 * draws: goals with zone, estimated shot spot and the scorer's run; the three things; one scene
 * for the tactics camera. Everything here is invented and marked so on the page. Shot positions,
 * goals, turnovers and the figures come from match.json (computed with the app's metrics code);
 * the runs and the scene are drawn from them by a seeded generator. Runs and positions are
 * handball-typical: no field player ever stands in a goal area (tested). The scene shows the ball
 * in every frame, because the match is invented; the page says that the analysis does not find
 * the ball in real video yet (OPEN_QUESTIONS Q-UX-15).
 */
import type { GoalRun } from "@/components/anlauf/bundle";
import type { ReportGoal } from "@/components/anlauf/flight-layout";
import type { Pt } from "@/components/anlauf/geometry";
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

/** Every goal of the match with its zone and run; about one in five is estimated (dashed). */
export function demoGoals(match: DemoMatch): DemoGoal[] {
  return match.events
    .filter((e) => e.type === "shot" && e.outcome === "goal" && e.x !== null && e.y !== null)
    .map((e, i) => {
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
        confirmed: i % 5 !== 3,
      };
    });
}

/** The goal sequence of the match report: what the Wurf head and the rail draw. */
export function reportGoals(goals: readonly DemoGoal[]): ReportGoal[] {
  return goals.map((g) => ({ minute: g.minute, team: g.team }));
}

/* ---------------------------------------------------------------------------------------------
 * The scene of thing 1 on the tactics camera: the opponent attacks our goal (x = 0) in a set
 * attack and scores. Everything is invented, but it moves like handball:
 * - attack around 9 m: backs (RL, RM, RR) at 9 to 11 m, wings near the sidelines, the pivot just
 *   outside the 6 m line between two defenders;
 * - defence 6:0 just in front of the 6 m line, shifting towards the ball, the defender at the
 *   ball steps out;
 * - only the goalkeeper stands in the goal area;
 * - the ball is always shown: in an invented match we know where it is. Two or three passes
 *   lead to the scorer, who takes off at his shot spot when the scene ends.
 * Numbers only on some players: the analysis reads about one in four (the ball carriers here).
 * ------------------------------------------------------------------------------------------- */

/** Half court (u across, v from the goal line) to court metres with the goal at x = 0. */
const toCourt = (p: Pt): Pt => [p[1], p[0]];

const SCENE_SECONDS = 6;
const SAMPLES = 25; // one point every quarter second
const PASS_SECONDS = 0.4;

type Slot = "la" | "rl" | "rm" | "rr" | "ra" | "kr";
/** Where the attack stands, in half-court metres. */
const SLOTS: Record<Slot, Pt> = {
  la: [1.0, 3.0],
  rl: [4.6, 9.6],
  rm: [10.0, 10.8],
  rr: [15.4, 9.6],
  ra: [19.0, 3.0],
  kr: [10.0, 7.4],
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
/** Who passes to whom before the goal, by the scorer's position. */
const PLAYS: Record<Slot, Slot[]> = {
  la: ["rm", "rl", "la"],
  rl: ["rr", "rm", "rl"],
  rm: ["la", "rl", "rm"],
  rr: ["rl", "rm", "rr"],
  ra: ["rm", "rr", "ra"],
  kr: ["rl", "rm", "kr"],
};

const lerp = (a: Pt, b: Pt, f: number): Pt => [a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f];
const ease = (f: number) => (f <= 0 ? 0 : f >= 1 ? 1 : f * f * (3 - 2 * f));

export function demoScene(goal: DemoGoal, label: string): CameraScene {
  const R = rng(seedOf(`${goal.id}-scene`));
  const scorerSlot: Slot = goal.zone in SLOTS ? (goal.zone as Slot) : "rm";
  const play = PLAYS[scorerSlot];
  const scorerNumber = goal.number ?? 5;
  // numbers for the ball carriers, never the scorer's number twice
  const pool = [9, 14, 22, 3, 11, 18, 7, 20].filter((n) => n !== scorerNumber);
  const numberOf = new Map<Slot, number | null>();
  for (const s of Object.keys(SLOTS) as Slot[]) numberOf.set(s, null);
  numberOf.set(scorerSlot, scorerNumber);
  play.slice(0, -1).forEach((s, i) => numberOf.set(s, pool[i]!));
  const extra = (["kr", "la", "ra"] as Slot[]).find((s) => !play.includes(s));
  if (extra) numberOf.set(extra, pool[3]!);

  // ball schedule: the holders one after the other, a short flight in between
  const hold = (SCENE_SECONDS - PASS_SECONDS * (play.length - 1)) / play.length;
  const ball: BallStretch[] = play.map((s, i) => {
    const from = i * (hold + PASS_SECONDS);
    return { from: round2(from), to: round2(i === play.length - 1 ? SCENE_SECONDS : from + hold), team: "opp", number: numberOf.get(s)! };
  });
  const holderAt = (sec: number): Slot | null => {
    const i = ball.findIndex((b) => sec >= b.from && sec <= b.to);
    return i < 0 ? null : play[i]!;
  };
  const times = Array.from({ length: SAMPLES }, (_, i) => (i / (SAMPLES - 1)) * SCENE_SECONDS);
  const receivedAt = ball[ball.length - 1]!.from;
  /** Across position of the ball from the schedule alone (holder's slot, or between two on a pass). */
  const ballSide = (sec: number): number => {
    const h = holderAt(sec);
    if (h) return SLOTS[h][0];
    const i = ball.findIndex((b) => b.from > sec);
    const f = (sec - ball[i - 1]!.to) / (ball[i]!.from - ball[i - 1]!.to);
    return SLOTS[play[i - 1]!][0] + (SLOTS[play[i]!][0] - SLOTS[play[i - 1]!][0]) * f;
  };

  // attackers: the one with the ball goes at the defence (a step towards the goal), the others
  // wait in their slot and move a little; the scorer runs from his slot to his shot spot
  const shot = outsideArea(goal.shot, SHOT_MIN);
  const wobble = () => (R() - 0.5) * 0.3;
  const attack = new Map<Slot, Pt[]>();
  for (const s of Object.keys(SLOTS) as Slot[]) {
    const at = SLOTS[s];
    const pts = times.map((sec) => {
      if (s === scorerSlot && sec >= receivedAt - 0.6) {
        const f = ease((sec - (receivedAt - 0.6)) / (SCENE_SECONDS - receivedAt + 0.6));
        return lerp(at, shot, f);
      }
      const h = holderAt(sec) === s;
      // the pivot stays between the two middle defenders, who shift with the ball
      if (s === "kr" && !h) return [at[0] + (ballSide(sec) - at[0]) * 0.2 + wobble() * 0.5, at[1] + wobble() * 0.5] as Pt;
      const toward: Pt = s === "la" || s === "ra" ? [at[0] + (s === "la" ? 0.5 : -0.5), at[1] + 0.6] : [at[0] + (10 - at[0]) * 0.08, at[1] - 1.3];
      const p = h ? toward : at;
      return [p[0] + wobble(), p[1] + wobble()] as Pt;
    });
    const path = smoothSteps(pts).map((p) => outsideArea(p, FIELD_MIN));
    // the scorer ends exactly at his shot spot
    if (s === scorerSlot) path[path.length - 1] = shot;
    attack.set(s, path);
  }

  // the ball's spot at a time: at its holder, or in flight between two holders
  const attackAt = (s: Slot, sec: number): Pt => attack.get(s)![Math.round((sec / SCENE_SECONDS) * (SAMPLES - 1))]!;
  const ballSpot = (sec: number): Pt => {
    const h = holderAt(sec);
    if (h) return attackAt(h, sec);
    const i = ball.findIndex((b) => b.from > sec);
    const a = ball[i - 1]!;
    const b = ball[i]!;
    return lerp(attackAt(play[i - 1]!, a.to), attackAt(play[i]!, b.from), (sec - a.to) / (b.from - a.to));
  };

  // defence: the line shifts towards the ball, the defender facing the ball steps out to it
  const defence = DEFENCE.map((at) =>
    times.map((sec) => {
      const b = ballSpot(sec);
      let p: Pt = [at[0] + (b[0] - at[0]) * 0.2, at[1]];
      const nearest = DEFENCE.reduce((best, d) => (Math.abs(d[0] - b[0]) < Math.abs(best[0] - b[0]) ? d : best));
      if (nearest === at) p = lerp(p, b, 0.32);
      return outsideArea([p[0] + wobble() * 0.5, p[1] + wobble() * 0.5], DEFENCE_MIN);
    }),
  );
  const ownNumbers = [7, null, 13, 4, null, 10];

  const tracks: SceneTrack[] = [];
  for (const s of Object.keys(SLOTS) as Slot[]) tracks.push({ team: "opp", number: numberOf.get(s) ?? null, xy: attack.get(s)!.map(toCourt) });
  defence.forEach((pts, i) => tracks.push({ team: "own", number: ownNumbers[i], xy: smoothSteps(pts).map(toCourt) }));
  // the goalkeeper, the only one in the goal area: moves with the ball between the posts
  tracks.push({
    team: "own",
    number: 1,
    keeper: true,
    xy: times.map((sec) => toCourt([Math.max(8.9, Math.min(11.1, 10 + (ballSpot(sec)[0] - 10) * 0.18)), 0.9])),
  });
  tracks.push({ team: "ref", xy: times.map((sec) => [13.5 - sec * 0.25, 0.9] as Pt) });

  return {
    clock: Math.max(0, Math.round(goal.minute * 60) - SCENE_SECONDS),
    duration: SCENE_SECONDS,
    tracks,
    ball,
    scorer: { team: "opp", number: scorerNumber },
    shot: toCourt(shot),
    aim: toCourt(goal.aim ?? [10, 0]),
    confirmed: goal.confirmed,
    label,
  };
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
