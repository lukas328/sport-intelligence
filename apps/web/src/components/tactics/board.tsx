"use client";

import { COURT, type Point } from "@handball/court";
import { clampToCourt, type Arrow, type ArrowKind, type Frame, type Token } from "@handball/tactics";
import { useRef, useState, type KeyboardEvent, type PointerEvent } from "react";

export type Tool = "move" | ArrowKind | "ball";

const PAD = 1;
const R = 0.6; // token radius in metres

interface Props {
  frame: Frame;
  /** animated positions override the frame's tokens and ball while playing */
  live?: { tokens: Token[]; ball: { x: number; y: number } | null } | null;
  court: "half" | "full";
  editable?: boolean;
  tool?: Tool;
  selected?: string | null;
  onSelect?: (id: string | null) => void;
  onChange?: (frame: Frame) => void;
  label: string;
  className?: string;
}

/**
 * SVG tactics board in court metres. Pointer events cover mouse, pen and touch; tokens are focusable and
 * move with the arrow keys (0.5 m, with Shift 2 m) so the board works without a pointer.
 */
export function Board({ frame, live, court, editable = false, tool = "move", selected, onSelect, onChange, label, className }: Props) {
  const svg = useRef<SVGSVGElement>(null);
  const drag = useRef<{ id: string; dx: number; dy: number } | null>(null);
  const [draft, setDraft] = useState<Arrow | null>(null);
  const x0 = court === "half" ? 20 : 0;
  const w = COURT.length - x0 + 2 * PAD;
  const h = COURT.width + 2 * PAD;
  const X = (x: number) => x - x0 + PAD;
  const Y = (y: number) => COURT.width - y + PAD;
  const tokens = live?.tokens ?? frame.tokens;
  const ball = live ? live.ball : frame.ball;

  function toCourt(e: PointerEvent): [number, number] {
    const el = svg.current!;
    const pt = el.createSVGPoint();
    pt.x = e.clientX;
    pt.y = e.clientY;
    const m = el.getScreenCTM();
    const p = m ? pt.matrixTransform(m.inverse()) : pt;
    return clampToCourt(p.x - PAD + x0, COURT.width - (p.y - PAD));
  }

  function update(next: Partial<Frame>) {
    onChange?.({ ...frame, ...next });
  }

  function onDown(e: PointerEvent<SVGSVGElement>) {
    if (!editable) return;
    const [x, y] = toCourt(e);
    const hit = [...frame.tokens].reverse().find((t) => Math.hypot(t.x - x, t.y - y) < R * 1.4);
    if (tool === "ball") {
      update({ ball: { x, y } });
      return;
    }
    if (tool === "move") {
      if (hit) {
        onSelect?.(hit.id);
        drag.current = { id: hit.id, dx: hit.x - x, dy: hit.y - y };
        svg.current?.setPointerCapture(e.pointerId);
      } else onSelect?.(null);
      return;
    }
    // arrows start at the token centre when one was hit
    const start: [number, number] = hit ? [hit.x, hit.y] : [x, y];
    setDraft({ kind: tool, points: [start, start] });
    svg.current?.setPointerCapture(e.pointerId);
  }

  function onMove(e: PointerEvent<SVGSVGElement>) {
    if (!editable) return;
    if (drag.current) {
      const [x, y] = toCourt(e);
      const d = drag.current;
      const [nx, ny] = clampToCourt(x + d.dx, y + d.dy);
      update({ tokens: frame.tokens.map((t) => (t.id === d.id ? { ...t, x: nx, y: ny } : t)) });
    } else if (draft) {
      setDraft({ ...draft, points: [draft.points[0]!, toCourt(e)] });
    }
  }

  function onUp() {
    drag.current = null;
    if (draft) {
      const [a, b] = draft.points as [[number, number], [number, number]];
      if (Math.hypot(b[0] - a[0], b[1] - a[1]) > 0.8) update({ arrows: [...frame.arrows, draft] });
      setDraft(null);
    }
  }

  function onTokenKey(e: KeyboardEvent, t: Token) {
    if (!editable) return;
    const step = e.shiftKey ? 2 : 0.5;
    const d = ({ ArrowLeft: [-step, 0], ArrowRight: [step, 0], ArrowUp: [0, step], ArrowDown: [0, -step] } as Record<string, [number, number]>)[e.key];
    if (d) {
      e.preventDefault();
      const [nx, ny] = clampToCourt(t.x + d[0], t.y + d[1]);
      update({ tokens: frame.tokens.map((k) => (k.id === t.id ? { ...k, x: nx, y: ny } : k)) });
    } else if (e.key === "Delete" || e.key === "Backspace") {
      e.preventDefault();
      update({ tokens: frame.tokens.filter((k) => k.id !== t.id) });
      onSelect?.(null);
    }
  }

  const path = (pts: readonly Point[]) =>
    pts
      .filter(([x]) => x >= x0 - 0.01)
      .map(([x, y], i) => `${i ? "L" : "M"}${X(x)} ${Y(y)}`)
      .join(" ");

  return (
    <svg
      ref={svg}
      viewBox={`0 0 ${w} ${h}`}
      role="group"
      aria-label={label}
      className={`max-h-[70vh] w-full touch-none select-none ${editable && tool !=="move"?"cursor-crosshair":""} ${className ??""}`}
      style={{ background: "var(--court)" }}
      onPointerDown={onDown}
      onPointerMove={onMove}
      onPointerUp={onUp}
      onPointerCancel={onUp}
      data-testid="tactics-board"
    >
      <defs>
        <marker id="hb-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
          <path d="M0 0 L10 5 L0 10 z" fill="var(--foreground)" />
        </marker>
      </defs>
      {Object.entries(COURT.lines)
        .filter(([name]) => !name.startsWith("substitution") && (court === "full" || !name.includes("left")))
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
      {court === "half" && <path d={`M${PAD} ${PAD} V${h - PAD}`} stroke="var(--court-line)" strokeWidth={0.08} />}

      {!live &&
        [...frame.arrows, ...(draft ? [draft] : [])].map((a, i) => <ArrowPath key={i} arrow={a} X={X} Y={Y} />)}

      {tokens.map((t) => {
        const isSel = editable && selected === t.id;
        return (
          <g
            key={t.id}
            transform={`translate(${X(t.x)} ${Y(t.y)})`}
            tabIndex={editable ? 0 : -1}
            role={editable ? "button" : "img"}
            aria-label={`${t.side === "own" ? "+" : "-"} ${t.label} (${t.x.toFixed(1)} m, ${t.y.toFixed(1)} m)`}
            aria-pressed={editable ? isSel : undefined}
            onFocus={() => editable && onSelect?.(t.id)}
            onKeyDown={(e) => onTokenKey(e, t)}
            className="outline-none"
            data-testid={`token-${t.id}`}
          >
            <circle
              r={R}
              fill={t.side === "own" ? "var(--accent)" : "#ffffff"}
              stroke={isSel ? "var(--foreground)" : t.side === "own" ? "var(--accent-contrast)" : "#111827"}
              strokeWidth={isSel ? 0.18 : 0.08}
            />
            <text
              y={0.22}
              textAnchor="middle"
              fontSize={0.62}
              fontWeight={700}
              fill={t.side === "own" ? "var(--accent-contrast)" : "#111827"}
              style={{ pointerEvents: "none" }}
            >
              {t.label}
            </text>
          </g>
        );
      })}
      {ball && <circle cx={X(ball.x)} cy={Y(ball.y)} r={0.3} fill="#f97316" stroke="#111827" strokeWidth={0.06} data-testid="ball" />}
    </svg>
  );
}

function ArrowPath({ arrow, X, Y }: { arrow: Arrow; X: (x: number) => number; Y: (y: number) => number }) {
  const pts = arrow.points.map(([x, y]) => [X(x), Y(y)] as const);
  const [a, b] = [pts[0]!, pts[pts.length - 1]!];
  const common = { fill: "none", stroke: "var(--foreground)", strokeWidth: 0.12, strokeLinecap: "round" as const };
  if (arrow.kind === "dribble") {
    // zigzag along the line
    const n = Math.max(4, Math.round(Math.hypot(b[0] - a[0], b[1] - a[1]) / 0.6));
    const nx = -(b[1] - a[1]);
    const ny = b[0] - a[0];
    const len = Math.hypot(nx, ny) || 1;
    const d = Array.from({ length: n + 1 }, (_, i) => {
      const t = i / n;
      const off = i === 0 || i === n ? 0 : (i % 2 ? 0.25 : -0.25);
      return `${i ? "L" : "M"}${a[0] + (b[0] - a[0]) * t + (nx / len) * off} ${a[1] + (b[1] - a[1]) * t + (ny / len) * off}`;
    }).join(" ");
    return <path d={d} {...common} markerEnd="url(#hb-arrow)" />;
  }
  if (arrow.kind === "screen") {
    const dx = b[0] - a[0];
    const dy = b[1] - a[1];
    const len = Math.hypot(dx, dy) || 1;
    const px = (-dy / len) * 0.5;
    const py = (dx / len) * 0.5;
    return (
      <g>
        <path d={`M${a[0]} ${a[1]} L${b[0]} ${b[1]}`} {...common} />
        <path d={`M${b[0] - px} ${b[1] - py} L${b[0] + px} ${b[1] + py}`} {...common} strokeWidth={0.18} />
      </g>
    );
  }
  return (
    <path
      d={pts.map(([x, y], i) => `${i ? "L" : "M"}${x} ${y}`).join(" ")}
      {...common}
      strokeDasharray={arrow.kind === "pass" ? "0.35 0.25" : undefined}
      markerEnd="url(#hb-arrow)"
    />
  );
}
