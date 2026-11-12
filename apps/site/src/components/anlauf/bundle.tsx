import type { CSSProperties } from "react";
import { HalfCourtLines } from "./court";
import { HALF_BOX, pathOf, type Pt, smooth, ZONE_AT } from "./geometry";

const NS = { vectorEffect: "non-scaling-stroke" } as const;
// the site shows the whole half (runs of fast breaks start near the middle line)
const BOX = "-0.6 -1.2 21.2 21.6";

/** One goal as the analysis gives it, in half-court coordinates (goal at the top). */
export interface GoalRun {
  /** own: ours, opp: the opponent's */
  team: "own" | "opp";
  minute?: number;
  /** the scorer's way before the shot (2 to 4 s), measured; empty when the tracks have none */
  run: readonly Pt[];
  /** estimated shot spot */
  shot: Pt;
  /** where on the goal line, if known; the line to it is thin and straight, never a flight */
  aim?: Pt | null;
  /** confirmed by a coach: solid; otherwise estimated: dashed and lighter */
  confirmed: boolean;
  zone?: string | null;
}

function colours(team: GoalRun["team"]) {
  return team === "own"
    ? { line: "var(--club-line)", pipe: "var(--club-pipe)", dot: "var(--club-dot)" }
    : { line: "var(--opp-line)", pipe: "var(--opp-pipe)", dot: "var(--opp-dot)" };
}

/**
 * Bundle: every goal of one kind as the scorer's run, then a thin straight line to the goal.
 * `rest` are the other goals of the match, faint, for context. `width` is the drawn width in px
 * (line widths and dot sizes depend on it). `play` draws the lines in order.
 */
export function Bundle({
  goals,
  rest = [],
  width = 360,
  play = false,
  label,
  className,
}: {
  goals: readonly GoalRun[];
  rest?: readonly GoalRun[];
  width?: number;
  play?: boolean;
  label: string;
  className?: string;
}) {
  const kk = width / HALF_BOX[2];
  const small = width < 160;
  return (
    <svg viewBox={BOX} role="img" aria-label={label} className={[play ? "play" : "", "block w-full", className].filter(Boolean).join(" ")}>
      <HalfCourtLines />
      {rest.map((g, i) =>
        g.run.length > 1 ? <path key={`r${i}`} d={pathOf(smooth(g.run, 6))} fill="none" stroke="var(--ink)" strokeOpacity={0.13} strokeWidth={1} {...NS} /> : null,
      )}
      {goals.map((g, i) => {
        const c = colours(g.team);
        const est = !g.confirmed;
        const w = small ? 1.6 : 2.6;
        const d = g.run.length > 1 ? pathOf(smooth(g.run, 8)) : null;
        return (
          <g key={i}>
            {d && !est && <path d={d} fill="none" stroke={c.pipe} strokeWidth={w + 2.4} strokeLinecap="round" {...NS} />}
            {d && (
              <path
                className={est ? "ln-e" : "ln"}
                style={{ "--i": i } as CSSProperties}
                pathLength={est ? undefined : 1}
                d={d}
                fill="none"
                stroke={c.line}
                // the drawn line is in field units: pathLength and non-scaling strokes do not mix
                strokeWidth={est ? w : w / kk}
                strokeOpacity={est ? 0.6 : 1}
                strokeDasharray={est ? "4 3.5" : undefined}
                strokeLinecap="round"
                {...(est ? NS : {})}
              />
            )}
            {g.aim && (
              <path d={`M${g.shot[0]} ${g.shot[1]}L${g.aim[0]} ${g.aim[1]}`} stroke="var(--ink)" strokeOpacity={est ? 0.3 : 0.55} strokeWidth={1} {...NS} />
            )}
            <circle
              cx={g.shot[0]}
              cy={g.shot[1]}
              r={(small ? 2.4 : 3.6) / kk}
              fill={est ? "var(--ground)" : c.line}
              stroke={est ? c.line : c.dot}
              strokeWidth={est ? 1.5 : 1}
              {...NS}
            />
          </g>
        );
      })}
    </svg>
  );
}

/** The empty field: no video, analysis running, or nothing found yet. */
export function EmptyField({ label, className }: { label?: string; className?: string }) {
  return (
    <svg viewBox={BOX} role={label ? "img" : undefined} aria-label={label} aria-hidden={label ? undefined : true} className={["block w-full", className].filter(Boolean).join(" ")}>
      <HalfCourtLines opacity={0.3} />
    </svg>
  );
}

/** Zone names as the coach says them (de-CH, short). */
export const ZONE_NAMES: Record<string, string> = {
  la: "LA",
  ra: "RA",
  rl: "RL",
  rm: "RM",
  rr: "RR",
  kr: "Kreis",
  m7: "7 m",
  gs: "Gegenstoss",
};

/** Zones: goals by position, the count at each zone, the estimated shot spots as dots. */
export function Zones({
  goals,
  team,
  width = 340,
  label,
  zoneNames = ZONE_NAMES,
}: {
  goals: readonly GoalRun[];
  team: GoalRun["team"];
  width?: number;
  label: string;
  zoneNames?: Record<string, string>;
}) {
  const kk = width / HALF_BOX[2];
  const c = colours(team);
  const count: Record<string, number> = {};
  for (const g of goals) if (g.zone) count[g.zone] = (count[g.zone] ?? 0) + 1;
  const max = Math.max(0, ...Object.values(count));
  return (
    <svg viewBox={BOX} role="img" aria-label={label} className="block w-full">
      <HalfCourtLines />
      {goals.map((g, i) => (
        <circle key={i} cx={g.shot[0]} cy={g.shot[1]} r={3 / kk} fill={g.confirmed ? c.line : "var(--ground)"} stroke={c.dot} strokeWidth={1.2} {...NS} />
      ))}
      {Object.entries(count).map(([z, n]) => {
        const p = ZONE_AT[z];
        if (!p) return null;
        const big = n === max;
        return (
          <g key={z}>
            <text
              x={p[0]}
              y={p[1]}
              textAnchor="middle"
              className="font-num"
              fill={big && team === "own" ? "var(--club-text)" : "var(--ink)"}
              style={{ fontSize: `${(big ? 34 : 24) / kk}px` }}
            >
              {n}
            </text>
            <text x={p[0]} y={p[1] + 18 / kk} textAnchor="middle" fill="var(--ink-2)" style={{ font: `600 ${16 / kk}px var(--font-sans)` }}>
              {zoneNames[z] ?? z}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
