import { pathOf } from "./geometry";
import { flightLayout, type FlightLabels, type ReportGoal } from "./flight-layout";

export { flowOf, type FlightLabels, type ReportGoal } from "./flight-layout";

/**
 * Flight: the run of the match in the Wurf head, the goal difference minute by minute, ours up.
 * Drawn in the ink on the club colour.
 */
export function Flight({
  goals,
  width,
  height,
  length = 60,
  labels,
  slant = 0,
  className,
}: {
  goals: readonly ReportGoal[];
  width: number;
  height: number;
  length?: number;
  labels?: FlightLabels;
  /** how far the slanted lower edge of the head rises over the width, in drawing units */
  slant?: number;
  className?: string;
}) {
  const small = width < 500;
  const pad = small ? 16 : 32;
  const L = flightLayout(goals, width, height, length, small ? undefined : labels, slant);
  const text = { font: "600 16px var(--font-sans)", fill: "var(--club-ink)" };
  return (
    <svg viewBox={`0 0 ${width} ${height}`} aria-hidden className={className}>
      <line x1={pad} x2={width - pad} y1={L.base} y2={L.base} stroke="var(--club-ink)" strokeOpacity={0.3} strokeDasharray="2 5" />
      <path d={pathOf(L.pts)} fill="none" stroke="var(--club-ink)" strokeWidth={small ? 2 : 2.6} strokeLinejoin="round" strokeOpacity={0.9} />
      <circle cx={L.end[0]} cy={L.end[1]} r={small ? 4 : 6} fill="var(--club-ink)" />
      {L.labels.map((l) => (
        <text key={l.text} x={l.x} y={l.y} textAnchor={l.anchor} style={text}>
          {l.text}
        </text>
      ))}
    </svg>
  );
}

/**
 * Rail: the timeline under the video. Goals from the report, ours up, theirs down, the marked
 * phase in yellow (with a word next to it in the page), the playhead at `at` (minutes).
 */
export function Rail({
  goals,
  phase,
  at,
  length = 60,
  label,
}: {
  goals: readonly ReportGoal[];
  phase?: readonly [number, number] | null;
  at?: number | null;
  length?: number;
  label: string;
}) {
  const W = 1000;
  const base = 36;
  const x = (m: number) => (Math.min(m, length) / length) * W;
  return (
    <svg viewBox="-10 -12 1020 92" preserveAspectRatio="none" role="img" aria-label={label} className="block h-[92px] w-full">
      {phase && <rect x={x(phase[0])} y={0} width={x(phase[1]) - x(phase[0])} height={72} fill="var(--attn)" />}
      <line x1={0} x2={W} y1={base} y2={base} stroke="var(--ink)" strokeWidth={1.5} />
      <line x1={x(length / 2)} x2={x(length / 2)} y1={2} y2={70} stroke="var(--ink)" strokeDasharray="2 4" />
      {goals.map((g, i) =>
        g.team === "own" ? (
          <rect key={i} x={x(g.minute) - 2.5} y={base - 26} width={5} height={24} fill="var(--club-line)" stroke="var(--club-pipe)" strokeWidth={1} />
        ) : (
          <rect key={i} x={x(g.minute) - 2.5} y={base + 2} width={5} height={24} fill="var(--opp-line)" stroke="var(--opp-pipe)" strokeWidth={1} />
        ),
      )}
      {at != null && (
        <>
          <line x1={x(at)} x2={x(at)} y1={-6} y2={78} stroke="var(--ink)" strokeWidth={2.5} />
          <path d={`M${x(at) - 7} -10h14l-7 9z`} fill="var(--ink)" />
        </>
      )}
    </svg>
  );
}
