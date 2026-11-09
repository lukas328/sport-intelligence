import type { Focus } from "@handball/tactics";
import { COURT, type Point } from "@handball/court";

const W = COURT.width;
const path = (pts: readonly Point[]) => pts.map(([x, y], i) => `${i ? "L" : "M"}${x} ${W - y}`).join(" ");

/** Where on the half court a drill works: wing corners, back court, pivot, 7 m mark, goal, or the whole half. */
function zone(f: Focus) {
  const z = { fill: "var(--accent)", fillOpacity: 0.28, stroke: "var(--accent)", strokeWidth: 0.25 };
  switch (f) {
    case "wings":
      return (
        <>
          <rect x={34.5} y={0.2} width={5.3} height={3.6} rx={0.6} {...z} />
          <rect x={34.5} y={16.2} width={5.3} height={3.6} rx={0.6} {...z} />
        </>
      );
    case "back_court":
      return <rect x={26} y={4} width={5} height={12} rx={0.8} {...z} />;
    case "pivot":
      return <rect x={32.4} y={7.2} width={2.2} height={5.6} rx={0.6} {...z} />;
    case "seven_m":
      return <circle cx={33} cy={10} r={1.3} {...z} />;
    case "goalkeeping":
      return <rect x={38.4} y={8.2} width={1.6} height={3.6} rx={0.3} {...z} />;
    case "finishing":
      return <ellipse cx={32} cy={10} rx={3.2} ry={7} {...z} />;
    default:
      // passing, transition, fast break, defence, powerplay: the whole half
      return <rect x={20.3} y={0.3} width={19.4} height={19.4} rx={0.4} fill="var(--accent)" fillOpacity={0.1} />;
  }
}

/** A small half court with the drill's area marked; decorative, the focus is also named in text. */
export function DrillCourt({ focus, className }: { focus: Focus; className?: string }) {
  const L = COURT.lines;
  return (
    <svg aria-hidden viewBox="20 0 20 20" className={className} fill="none">
      <rect x={20.1} y={0.1} width={19.8} height={19.8} rx={0.5} fill="var(--raised)" stroke="var(--border)" strokeWidth={0.2} />
      {zone(focus)}
      <g stroke="var(--foreground)" strokeOpacity={0.5} strokeWidth={0.22}>
        <path d={path(L.goal_area_right ?? [])} />
        <path d={path(L.free_throw_right ?? [])} strokeDasharray="0.6 0.5" />
        <path d={path(L.penalty_mark_right ?? [])} />
        <line x1={20.1} y1={0.1} x2={20.1} y2={19.9} strokeDasharray="0.6 0.5" strokeOpacity={0.35} />
      </g>
      <line x1={39.9} y1={8.5} x2={39.9} y2={11.5} stroke="var(--foreground)" strokeWidth={0.5} />
    </svg>
  );
}
