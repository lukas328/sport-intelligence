import { COURT, type Point } from "@handball/court";
import { cn } from "@/lib/utils";

const path = (pts: readonly Point[]) => pts.map(([x, y], i) => `${i ? "L" : "M"}${x} ${COURT.width - y}`).join(" ");

/**
 * The right goal area of a real court (packages/court): 6 m line, dashed 9 m line, 7 m mark and
 * goal. Decorative only, drawn in the current text colour. It frames the stage; it never runs
 * through text (callers hide it where space is short).
 */
export function CourtLines({ className }: { className?: string }) {
  const L = COURT.lines;
  // a square window: 14 m deep, the middle 14 m of the width, so both arcs stay readable
  const x0 = COURT.length - 13.6;
  return (
    <svg
      aria-hidden
      viewBox={`${x0} 3 14 14`}
      preserveAspectRatio="xMaxYMid meet"
      className={cn("pointer-events-none", className)}
      fill="none"
      stroke="currentColor"
    >
      <path d={path(L.free_throw_right ?? [])} strokeWidth={2} strokeDasharray="9 8" vectorEffect="non-scaling-stroke" opacity={0.4} />
      <path d={path(L.goal_area_right ?? [])} strokeWidth={2.5} vectorEffect="non-scaling-stroke" opacity={0.55} />
      <path d={path(L.penalty_mark_right ?? [])} strokeWidth={2.5} vectorEffect="non-scaling-stroke" opacity={0.6} />
      <path d={path(L.goal_right ?? [])} strokeWidth={6} vectorEffect="non-scaling-stroke" opacity={0.7} />
    </svg>
  );
}
