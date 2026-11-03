import { COURT } from "@handball/court";
import type { ReactNode } from "react";

/** Handball court 40 x 20 m from the shared geometry; children are drawn in metres. */
export function Court({ label, children }: { label: string; children?: ReactNode }) {
  const lines = Object.entries(COURT.lines);
  return (
    <svg viewBox={`-1 -1 ${COURT.length + 2} ${COURT.width + 2}`} role="img" aria-label={label} className="h-auto w-full">
      <rect x={-1} y={-1} width={COURT.length + 2} height={COURT.width + 2} fill="var(--court)" />
      {lines.map(([name, pts]) => (
        <polyline
          key={name}
          points={pts.map(([x, y]) => `${x},${y}`).join(" ")}
          fill="none"
          stroke="var(--court-line)"
          strokeWidth={0.12}
          strokeDasharray={COURT.dashedLines.includes(name) ? "0.4 0.3" : undefined}
        />
      ))}
      {children}
    </svg>
  );
}
