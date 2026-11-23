"use client";

import type { MouseEvent, ReactNode } from "react";
import { HalfCourtLines } from "@/components/anlauf/court";

/**
 * The attacked half with the goal at the top, in the paper style of every other court of the app
 * (app review UI-01, UI-03: this one stood dark with the goal on the right). Positions come in
 * court metres with the attacked goal at x = 40 (they are normalised); left and right are seen
 * from the attack, as on the goal maps.
 */
const BOX = [-0.6, -1.2, 21.2, 22] as const;
/** court metres (x 20..40, y 0..20) to the half: u = 20 - y across, v = 40 - x from the goal line */
const TO_HALF = "matrix(0 -1 -1 0 20 40)";

export function CourtHalf({
  children,
  onPick,
  label,
}: {
  children?: ReactNode;
  onPick?: (x: number, y: number) => void;
  label: string;
}) {
  function click(e: MouseEvent<SVGSVGElement>) {
    if (!onPick) return;
    const r = e.currentTarget.getBoundingClientRect();
    const u = BOX[0] + ((e.clientX - r.left) / r.width) * BOX[2];
    const v = BOX[1] + ((e.clientY - r.top) / r.height) * BOX[3];
    const x = Math.min(40, Math.max(20, 40 - v));
    const y = Math.min(20, Math.max(0, 20 - u));
    onPick(Math.round(x * 10) / 10, Math.round(y * 10) / 10);
  }
  return (
    <svg
      viewBox={BOX.join(" ")}
      role="img"
      aria-label={label}
      className={`court-frame block bg-paper ${onPick ? "cursor-crosshair" : ""}`}
      onClick={click}
      data-testid="court-half"
    >
      <HalfCourtLines />
      <g transform={TO_HALF}>{children}</g>
    </svg>
  );
}

/** Marker in court coordinates (inside CourtHalf). */
export function ShotDot({ x, y, outcome, title }: { x: number; y: number; outcome: string; title?: string }) {
  const fill = { goal: "var(--ok)", save: "var(--error)", miss: "#9ca3af", post: "#f59e0b", blocked: "#6b7280" }[outcome] ?? "#6b7280";
  return (
    <circle cx={x} cy={y} r={0.45} fill={fill} stroke="var(--ink)" strokeWidth={0.06}>
      {title && <title>{title}</title>}
    </circle>
  );
}
