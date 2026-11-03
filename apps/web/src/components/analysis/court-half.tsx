"use client";

import { COURT, type Point } from "@handball/court";
import type { MouseEvent, ReactNode } from "react";

/** Attacking half (x 20..40) as SVG; the attacked goal is on the right (positions are normalised). */
const X0 = 20;
const PAD = 1;

export function CourtHalf({
  children,
  onPick,
  label,
}: {
  children?: ReactNode;
  onPick?: (x: number, y: number) => void;
  label: string;
}) {
  const w = COURT.length - X0 + 2 * PAD;
  const h = COURT.width + 2 * PAD;
  const path = (pts: readonly Point[]) =>
    pts
      .filter(([x]) => x >= X0 - 0.01)
      .map(([x, y], i) => `${i ? "L" : "M"}${x - X0 + PAD} ${COURT.width - y + PAD}`)
      .join(" ");
  function click(e: MouseEvent<SVGSVGElement>) {
    if (!onPick) return;
    const r = e.currentTarget.getBoundingClientRect();
    const x = ((e.clientX - r.left) / r.width) * w - PAD + X0;
    const y = COURT.width - (((e.clientY - r.top) / r.height) * h - PAD);
    onPick(Math.round(x * 10) / 10, Math.round(y * 10) / 10);
  }
  return (
    <svg
      viewBox={`0 0 ${w} ${h}`}
      role="img"
      aria-label={label}
      className={`w-full rounded ${onPick ? "cursor-crosshair" : ""}`}
      style={{ background: "var(--court)" }}
      onClick={click}
      data-testid="court-half"
    >
      {Object.entries(COURT.lines)
        .filter(([name]) => !name.includes("left") && !name.startsWith("substitution"))
        .map(([name, pts]) => (
          <path
            key={name}
            d={path(pts)}
            fill="none"
            stroke="var(--court-line)"
            strokeWidth={name.startsWith("goal_right") ? 0.4 : 0.08}
            strokeDasharray={COURT.dashedLines.includes(name) ? "0.3 0.3" : undefined}
          />
        ))}
      <path d={`M${PAD} ${PAD} V${h - PAD}`} stroke="var(--court-line)" strokeWidth={0.08} />
      <g transform={`translate(${PAD - X0} ${PAD}) scale(1 -1) translate(0 ${-COURT.width})`}>{children}</g>
    </svg>
  );
}

/** Marker in court coordinates (inside CourtHalf). */
export function ShotDot({ x, y, outcome, title }: { x: number; y: number; outcome: string; title?: string }) {
  const fill = { goal: "var(--ok)", save: "var(--error)", miss: "#9ca3af", post: "#f59e0b", blocked: "#6b7280" }[outcome] ?? "#6b7280";
  return (
    <circle cx={x} cy={y} r={0.45} fill={fill} stroke="#111827" strokeWidth={0.06}>
      {title && <title>{title}</title>}
    </circle>
  );
}
