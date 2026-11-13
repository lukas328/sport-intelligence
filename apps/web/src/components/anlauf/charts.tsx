import { pathOf } from "./geometry";
import { flightLayout, signed, type FlightLabels, type ReportGoal } from "./flight-layout";

export { flightLayout, flowOf, floorAt, type FlightLabels, type ReportGoal } from "./flight-layout";

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
  const text = { font: "600 14px var(--font-sans)", fill: "var(--club-ink)" };
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

/** Series: one bar per match with video, the last one in the team's colour. */
export function Series({ values, team, label }: { values: readonly number[]; team: "own" | "opp"; label: string }) {
  const W = 132;
  const H = 64;
  const n = values.length;
  const bw = n > 4 ? 18 : 30;
  const gap = n > 1 ? (W - n * bw) / (n - 1) : 0;
  const max = Math.max(1, ...values);
  const col = team === "own" ? "var(--club-line)" : "var(--opp-line)";
  const pipe = team === "own" ? "var(--club-pipe)" : "var(--opp-pipe)";
  return (
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={label} className="block w-[132px]">
      {values.map((v, i) => {
        const h = (40 * v) / max;
        const x = i * (bw + gap);
        const last = i === n - 1;
        return (
          <g key={i}>
            <rect x={x} y={H - 4 - h} width={bw} height={h} fill={last ? col : "var(--ink)"} fillOpacity={last ? 1 : 0.18} stroke={last ? pipe : "none"} strokeWidth={1.5} />
            <text x={x + bw / 2} y={H - 10 - h} textAnchor="middle" className="font-num" fill="var(--ink)" style={{ fontSize: 17 }}>
              {v}
            </text>
          </g>
        );
      })}
      <line x1={0} x2={W} y1={H - 3} y2={H - 3} stroke="var(--ink)" strokeWidth={1.5} />
    </svg>
  );
}

/** Goal difference per match: wins up in the club colour, losses down as a dashed ink outline. */
export function DiffBars({ matches, width = 700, label }: { matches: readonly { label: string; diff: number }[]; width?: number; label: string }) {
  // the scale fits the biggest difference, the height the bars and their numbers on both sides:
  // a −20 keeps its bar and its number inside the picture (UX test A10)
  const most = Math.max(0, ...matches.map((m) => m.diff));
  const least = Math.max(0, ...matches.map((m) => -m.diff));
  const U = Math.min(7, 84 / Math.max(1, most, least));
  const mid = Math.max(30, most * U + 32);
  const H = mid + Math.max(30, least * U + 32);
  const step = width / Math.max(1, matches.length);
  const bw = Math.min(64, step - 22);
  // a name never runs into its neighbour (UX test H14): cut to the slot, with a point
  const fit = (s: string) => {
    const room = Math.floor((step - 8) / 8);
    return s.length <= room ? s : `${s.slice(0, Math.max(3, room - 1))}.`;
  };
  return (
    <svg viewBox={`0 0 ${width} ${H}`} role="img" aria-label={label} className="block w-full">
      <line x1={0} x2={width} y1={mid} y2={mid} stroke="var(--ink)" strokeWidth={1.5} />
      {matches.map((m, i) => {
        const v = m.diff;
        const x = i * step + (step - bw) / 2;
        const h = Math.abs(v) * U;
        const up = v > 0;
        return (
          <g key={i}>
            <rect
              x={x}
              y={up ? mid - h : mid}
              width={bw}
              height={Math.max(h, 1)}
              fill={up ? "var(--club-line)" : "none"}
              stroke={up ? "var(--club-dot)" : "var(--ink)"}
              strokeWidth={1.5}
              strokeDasharray={up ? undefined : "4 3"}
            />
            <text x={x + bw / 2} y={up ? mid - h - 8 : mid + h + 22} textAnchor="middle" className="font-num" fill="var(--ink)" style={{ fontSize: 20 }}>
              {signed(v)}
            </text>
            <text x={x + bw / 2} y={up ? mid + 20 : mid - 10} textAnchor="middle" fill="var(--ink-2)" style={{ font: "600 14px var(--font-sans)" }}>
              <title>{m.label}</title>
              {fit(m.label)}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
