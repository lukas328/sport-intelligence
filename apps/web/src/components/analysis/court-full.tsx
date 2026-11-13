"use client";

import { COURT, type Point } from "@handball/court";

const PAD = 1;

/** Whole court with an optional heatmap grid (rows over y, columns over x, values = share of time). */
export function CourtHeatmap({ grid, label }: { grid?: number[][]; label: string }) {
  const w = COURT.length + 2 * PAD;
  const h = COURT.width + 2 * PAD;
  const path = (pts: readonly Point[]) => pts.map(([x, y], i) => `${i ? "L" : "M"}${x + PAD} ${COURT.width - y + PAD}`).join(" ");
  const rows = grid?.length ?? 0;
  const cols = grid?.[0]?.length ?? 0;
  const max = Math.max(0.0001, ...(grid ?? []).flat());
  return (
    <svg viewBox={`0 0 ${w} ${h}`} role="img" aria-label={label} className="w-full" style={{ background: "var(--court)" }} data-testid="court-heatmap">
      {grid &&
        grid.map((row, r) =>
          row.map((v, c) =>
            v > 0 ? (
              <rect
                key={`${r}-${c}`}
                x={PAD + (c * COURT.length) / cols}
                y={PAD + COURT.width - ((r + 1) * COURT.width) / rows}
                width={COURT.length / cols}
                height={COURT.width / rows}
                fill="var(--foreground)"
                opacity={0.12 + 0.68 * (v / max)}
              >
                <title>{`${Math.round(v * 100)} %`}</title>
              </rect>
            ) : null,
          ),
        )}
      {Object.entries(COURT.lines)
        .filter(([name]) => !name.startsWith("substitution"))
        .map(([name, pts]) => (
          <path
            key={name}
            d={path(pts)}
            fill="none"
            stroke="var(--court-line)"
            strokeWidth={name.startsWith("goal_") ? 0.4 : 0.08}
            strokeDasharray={COURT.dashedLines.includes(name) ? "0.3 0.3" : undefined}
          />
        ))}
    </svg>
  );
}
