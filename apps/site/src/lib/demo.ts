/**
 * The fictional demo match (public/demo/match.json, scripts/make_demo.py) in the shape the app
 * draws: goals with zone, estimated shot spot and the scorer's run; the three things; one scene
 * for the tactics camera. Everything here is invented and marked so on the page. Shot positions,
 * goals, turnovers and the figures come from match.json (computed with the app's metrics code);
 * the runs and the scene are drawn from them by a seeded generator. The ball is never placed: the
 * analysis does not find it yet (OPEN_QUESTIONS Q-UX-15).
 */
import type { GoalRun } from "@/components/anlauf/bundle";
import type { ReportGoal } from "@/components/anlauf/flight-layout";
import type { Pt } from "@/components/anlauf/geometry";
import type { CameraScene, SceneTrack } from "@/components/anlauf/tactics-camera";

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
  return pts.map(clamp);
}

/** Every goal of the match with its zone and run; about one in five is estimated (dashed). */
export function demoGoals(match: DemoMatch): DemoGoal[] {
  return match.events
    .filter((e) => e.type === "shot" && e.outcome === "goal" && e.x !== null && e.y !== null)
    .map((e, i) => {
      const R = rng(seedOf(e.id));
      const shot = clamp(halfSpot(e.x!, e.y!));
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
 * The scene of thing 1 on the tactics camera: the opponent attacks our goal (x = 0). The scorer
 * follows the run of the goal; the others hold a 6:0 defence and a set attack and shift a little
 * towards the ball side. Numbers only on some players: the analysis reads about one in four.
 * ------------------------------------------------------------------------------------------- */

/** Half court (u across, v from the goal line) to court metres with the goal at x = 0. */
const toCourt = (p: Pt): Pt => [p[1], p[0]];

function drift(start: Pt, toward: Pt, amount: number, R: () => number): Pt[] {
  const out: Pt[] = [];
  for (let i = 0; i < 5; i++) {
    const f = (i / 4) * amount;
    out.push([start[0] + (toward[0] - start[0]) * f + (R() - 0.5) * 0.25, start[1] + (toward[1] - start[1]) * f + (R() - 0.5) * 0.25]);
  }
  return out;
}

export function demoScene(goal: DemoGoal, label: string): CameraScene {
  const R = rng(seedOf(`${goal.id}-scene`));
  const ball = toCourt(goal.shot);
  const ballSide = goal.shot[0];
  const tracks: SceneTrack[] = [];
  // attackers: LA, RL, RM, RR, RA, KR in half coordinates; the scorer replaces the one of his zone
  const attack: [Zone, Pt][] = [
    ["la", [1.2, 2.2]],
    ["rl", [4.8, 10.6]],
    ["rm", [10, 11.8]],
    ["rr", [15.2, 10.6]],
    ["ra", [18.8, 2.2]],
    ["kr", [9.2, 6.6]],
  ];
  const oppNumbers = [3, 9, 14, 22, 11, 18];
  const replaced = attack.findIndex(([z]) => z === goal.zone);
  const scorerNumber = goal.number ?? 5;
  attack.forEach(([, at], i) => {
    if (i === replaced) return;
    const toward: Pt = [at[0] + (ballSide - at[0]) * 0.15, at[1] - 0.8];
    tracks.push({ team: "opp", number: i % 2 === 0 ? oppNumbers[i] : null, xy: drift(toCourt(at), toCourt(toward), 1, R) });
  });
  const run = goal.run.length > 4 ? goal.run : [...goal.run];
  tracks.push({ team: "opp", number: scorerNumber, xy: run.map(toCourt) });
  // defenders on the 6 m line, shifting towards the ball side; the goalkeeper in the goal
  const defence: Pt[] = [[2.2, 4.6], [5.2, 6.6], [8.4, 7.2], [11.6, 7.2], [14.8, 6.6], [17.8, 4.6]];
  const ownNumbers = [7, null, 13, 4, null, 10];
  defence.forEach((at, i) => {
    const toward: Pt = [at[0] + (ballSide - at[0]) * 0.22, at[1] - 0.6];
    tracks.push({ team: "own", number: ownNumbers[i], xy: drift(toCourt(at), toCourt(toward), 1, R) });
  });
  tracks.push({ team: "own", number: 1, xy: drift(toCourt([10, 0.9]), toCourt([Math.max(8.6, Math.min(11.4, ballSide)), 0.9]), 1, R) });
  tracks.push({ team: "ref", xy: drift([12.5, 1.6], [11, 1.4], 1, R) });
  return {
    clock: Math.max(0, Math.round(goal.minute * 60) - 6),
    duration: 6,
    tracks,
    ball: [],
    scorer: { team: "opp", number: scorerNumber },
    shot: ball,
    aim: toCourt(goal.aim ?? [10, 0]),
    confirmed: goal.confirmed,
    label,
  };
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
