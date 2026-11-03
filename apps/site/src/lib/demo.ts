/** Types and pure helpers for the demo analysis (data: public/demo/match.json, scripts/make_demo.py). */
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

export interface DemoShot extends DemoEvent {
  x: number;
  y: number;
  outcome: string;
  shot_type: string;
  xg: number;
}

interface TeamBlock {
  goals: number;
  shooting_pct: number | null;
  xg: number;
  saves: number;
  turnovers: number;
  seven_m_goals: number;
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

export interface ShotFilter {
  side: "own" | "opponent" | "both";
  outcome: string; // "all" or a shot outcome
  period: number; // 0 = both halves
}

export function isShot(e: DemoEvent): e is DemoShot {
  return e.type === "shot" && e.x !== null && e.y !== null && e.outcome !== null && e.xg !== null;
}

/** Shots matching the filter; positions are normalised so that every team attacks towards x = 40. */
export function filterShots(match: DemoMatch, f: ShotFilter): DemoShot[] {
  return match.events
    .filter(isShot)
    .filter((e) => (f.side === "both" || e.side === f.side) && (f.outcome === "all" || e.outcome === f.outcome))
    .filter((e) => !f.period || e.period === f.period);
}

export type FigureKey = "goals" | "shootingPct" | "xg" | "saves" | "turnovers" | "sevenM" | "fastBreak";

export function demoFigures(match: DemoMatch): [FigureKey, number | null, number | null][] {
  const { own, opponent } = match.stats;
  const row = (key: FigureKey, pick: (b: TeamBlock) => number | null): [FigureKey, number | null, number | null] => [
    key,
    pick(own),
    pick(opponent),
  ];
  return [
    row("goals", (b) => b.goals),
    row("shootingPct", (b) => b.shooting_pct),
    row("xg", (b) => b.xg),
    row("saves", (b) => b.saves),
    row("turnovers", (b) => b.turnovers),
    row("sevenM", (b) => b.seven_m_goals),
    row("fastBreak", (b) => b.fast_break_goals),
  ];
}
