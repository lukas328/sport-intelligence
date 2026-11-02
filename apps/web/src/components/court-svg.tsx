import { COURT, type Point } from "@handball/court";

const toPath = (pts: readonly Point[]) =>
  pts.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x} ${COURT.width - y}`).join(" ");

/** Static court drawing from the shared geometry (packages/court). y is flipped for SVG. */
export function CourtSvg({ label }: { label: string }) {
  return (
    <svg
      viewBox={`-1 -1 ${COURT.length + 2} ${COURT.width + 2}`}
      role="img"
      aria-label={label}
      className="w-full rounded-lg"
      style={{ background: "var(--court)" }}
    >
      {Object.entries(COURT.lines).map(([name, pts]) => (
        <path
          key={name}
          d={toPath(pts)}
          fill="none"
          stroke="var(--court-line)"
          strokeWidth={name.startsWith("goal_left") || name.startsWith("goal_right") ? 0.4 : 0.08}
          strokeDasharray={COURT.dashedLines.includes(name) ? "0.3 0.3" : undefined}
        />
      ))}
      <circle cx={COURT.length / 2} cy={COURT.width / 2} r={0.15} fill="var(--court-line)" />
    </svg>
  );
}
