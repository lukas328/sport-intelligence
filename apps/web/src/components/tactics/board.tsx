"use client";

import { COURT, type Point } from "@handball/court";
import { TOKEN_RADIUS, clampToCourt, type Arrow, type ArrowKind, type Frame, type Token } from "@handball/tactics";
import { useTranslations } from "next-intl";
import { useEffect, useId, useRef, useState, type KeyboardEvent, type PointerEvent } from "react";
import { BOARD_THEME, distToSegment, simplify } from "./board-theme";

export { BOARD_THEME, simplify };

export type Tool = "move" | ArrowKind | "ball";
export type Orientation = "auto" | "landscape" | "portrait";

const PAD = 1.5; // margin around the court in metres: room for the goals and for tokens at the line
const R = TOKEN_RADIUS;
const MIN_HIT_PX = 22; // half of the 44 px touch target

interface Props {
  frame: Frame;
  /** animated positions override the frame's tokens and ball while playing */
  live?: { tokens: Token[]; ball: { x: number; y: number } | null } | null;
  court: "half" | "full";
  editable?: boolean;
  tool?: Tool;
  /** a token id, "ball" or "arrow:<index>" */
  selected?: string | null;
  onSelect?: (id: string | null) => void;
  onChange?: (frame: Frame) => void;
  /** called before a drag, a drawing or a key move changes the frame (the editor records undo there) */
  onGestureStart?: () => void;
  label: string;
  className?: string;
  /** half court: goal at the top; full court: across when there is room, upright on narrow screens */
  orientation?: Orientation;
  /** markers for drill sketches (court metres) */
  cones?: readonly (readonly [number, number])[];
}

type View = { portrait: boolean; x0: number; x1: number; w: number; h: number };

function viewOf(court: "half" | "full", portrait: boolean): View {
  const x0 = court === "half" ? 20 : 0;
  const x1 = COURT.length;
  const span = x1 - x0;
  return portrait ? { portrait, x0, x1, w: COURT.width + 2 * PAD, h: span + 2 * PAD } : { portrait, x0, x1, w: span + 2 * PAD, h: COURT.width + 2 * PAD };
}

/** court metres to board coordinates and back */
function project(v: View) {
  const S = (x: number, y: number): [number, number] => (v.portrait ? [COURT.width - y + PAD, v.x1 - x + PAD] : [x - v.x0 + PAD, COURT.width - y + PAD]);
  const C = (sx: number, sy: number): [number, number] => (v.portrait ? [v.x1 - (sy - PAD), COURT.width - (sx - PAD)] : [sx - PAD + v.x0, COURT.width - (sy - PAD)]);
  return { S, C };
}

/**
 * SVG tactics board in court metres, the main view of a play. Pointer events cover mouse, pen and
 * touch (drag a player like a magnet, draw a run from a player); hit targets are at least 44 px.
 * Tokens and the ball are focusable in edit mode and move with the arrow keys (0.5 m, with Shift
 * 2 m) in the direction of the screen, so the board works without a pointer.
 */
export function Board({
  frame,
  live,
  court,
  editable = false,
  tool = "move",
  selected,
  onSelect,
  onChange,
  onGestureStart,
  label,
  className,
  orientation = "auto",
  cones,
}: Props) {
  const t = useTranslations("tactics");
  const uid = useId().replace(/:/g, "");
  const svg = useRef<SVGSVGElement>(null);
  const drag = useRef<{ id: string; dx: number; dy: number } | null>(null);
  const [draft, setDraft] = useState<Arrow | null>(null);
  const [box, setBox] = useState<{ w: number; h: number } | null>(null);

  useEffect(() => {
    const el = svg.current;
    if (!el || typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(([e]) => setBox({ w: e!.contentRect.width, h: e!.contentRect.height }));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const width = box?.w ?? null;
  const portrait = orientation === "portrait" || (orientation === "auto" && (court === "half" || (width != null && width < 640)));
  const view = viewOf(court, portrait);
  const { S, C } = project(view);
  // CSS pixels per metre (the drawing keeps its aspect ratio inside the box: the smaller scale wins)
  const pxPerM = box && box.w > 0 ? Math.min(box.w / view.w, box.h > 0 ? box.h / view.h : Infinity) : 24;
  const hitR = Math.max(R * 1.15, MIN_HIT_PX / pxPerM);
  const showLabels = pxPerM * R * 2 >= 18;

  const tokens = live?.tokens ?? frame.tokens;
  const ball = live ? live.ball : frame.ball;

  function toCourt(e: PointerEvent): [number, number] {
    const el = svg.current!;
    const pt = el.createSVGPoint();
    pt.x = e.clientX;
    pt.y = e.clientY;
    const m = el.getScreenCTM();
    const p = m ? pt.matrixTransform(m.inverse()) : pt;
    const [x, y] = C(p.x, p.y);
    return clampToCourt(x, y);
  }

  /** tokens stay on the board: the centre at most a little outside the lines */
  const keepIn = (x: number, y: number): [number, number] => {
    const [cx, cy] = clampToCourt(x, y);
    return [Math.min(COURT.length + 0.4, Math.max(court === "half" ? 20.4 : -0.4, cx)), Math.min(COURT.width + 0.4, Math.max(-0.4, cy))];
  };

  function update(next: Partial<Frame>) {
    onChange?.({ ...frame, ...next });
  }

  const nearestToken = (x: number, y: number) => {
    let best: Token | null = null;
    let d = hitR;
    for (const k of frame.tokens) {
      const dk = Math.hypot(k.x - x, k.y - y);
      if (dk <= d) {
        d = dk;
        best = k;
      }
    }
    return best;
  };

  function onDown(e: PointerEvent<SVGSVGElement>) {
    if (!editable) return;
    const [x, y] = toCourt(e);
    const hit = nearestToken(x, y);
    if (tool === "ball") {
      onGestureStart?.();
      update({ ball: hit ? { x: hit.x, y: hit.y } : { x, y } });
      onSelect?.("ball");
      return;
    }
    if (tool === "move") {
      const ballHit = frame.ball && Math.hypot(frame.ball.x - x, frame.ball.y - y) <= Math.max(0.6, MIN_HIT_PX / pxPerM) && !hit;
      if (hit || ballHit) {
        const id = hit ? hit.id : "ball";
        const at = hit ?? frame.ball!;
        onSelect?.(id);
        onGestureStart?.();
        drag.current = { id, dx: at.x - x, dy: at.y - y };
        svg.current?.setPointerCapture?.(e.pointerId);
        return;
      }
      // an arrow under the finger: select it (to delete it)
      const tol = Math.max(0.5, 14 / pxPerM);
      const ai = frame.arrows.findIndex((a) => a.points.some((p, i) => i > 0 && distToSegment([x, y], a.points[i - 1]!, p) <= tol));
      onSelect?.(ai >= 0 ? `arrow:${ai}` : null);
      return;
    }
    // arrows start at the token centre when one was hit
    const start: [number, number] = hit ? [hit.x, hit.y] : [x, y];
    setDraft({ kind: tool, points: [start, start] });
    svg.current?.setPointerCapture?.(e.pointerId);
  }

  function onMove(e: PointerEvent<SVGSVGElement>) {
    if (!editable) return;
    if (drag.current) {
      const [x, y] = toCourt(e);
      const d = drag.current;
      const [nx, ny] = keepIn(x + d.dx, y + d.dy);
      if (d.id === "ball") update({ ball: { x: nx, y: ny } });
      else update({ tokens: frame.tokens.map((k) => (k.id === d.id ? { ...k, x: nx, y: ny } : k)) });
    } else if (draft) {
      const p = toCourt(e);
      const pts = draft.points;
      const last = pts[pts.length - 2]!;
      // a new bend every 0.6 m, the last point follows the finger
      const next: [number, number][] = Math.hypot(p[0] - last[0], p[1] - last[1]) > 0.6 && pts.length > 1 ? [...pts.slice(0, -1), pts[pts.length - 1]!, p] : [...pts.slice(0, -1), p];
      setDraft({ ...draft, points: next });
    }
  }

  function onUp() {
    drag.current = null;
    if (!draft) return;
    const pts = draft.points;
    const a = pts[0]!;
    let b = pts[pts.length - 1]!;
    if (Math.hypot(b[0] - a[0], b[1] - a[1]) > 0.8) {
      // a pass or run that ends on a player ends at the player
      const end = nearestToken(b[0], b[1]);
      if (end && Math.hypot(end.x - a[0], end.y - a[1]) > 0.5) b = [end.x, end.y];
      const points = simplify([...pts.slice(0, -1), b].map(([x, y]) => [Math.round(x * 100) / 100, Math.round(y * 100) / 100] as [number, number]));
      onGestureStart?.();
      update({ arrows: [...frame.arrows, { kind: draft.kind, points }] });
      onSelect?.(`arrow:${frame.arrows.length}`);
    }
    setDraft(null);
  }

  /** screen direction of an arrow key in court metres */
  function keyStep(key: string, step: number): [number, number] | null {
    const screen = ({ ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] } as Record<string, [number, number]>)[key];
    if (!screen) return null;
    const [sx, sy] = screen;
    return portrait ? [-sy * step, -sx * step] : [sx * step, -sy * step];
  }

  function onTokenKey(e: KeyboardEvent, k: Token) {
    if (!editable) return;
    const d = keyStep(e.key, e.shiftKey ? 2 : 0.5);
    if (d) {
      e.preventDefault();
      onGestureStart?.();
      const [nx, ny] = keepIn(k.x + d[0], k.y + d[1]);
      update({ tokens: frame.tokens.map((x) => (x.id === k.id ? { ...x, x: nx, y: ny } : x)) });
    } else if (e.key === "Delete" || e.key === "Backspace") {
      e.preventDefault();
      onGestureStart?.();
      update({ tokens: frame.tokens.filter((x) => x.id !== k.id) });
      onSelect?.(null);
    } else if (e.key === "Escape") onSelect?.(null);
  }

  function onBallKey(e: KeyboardEvent) {
    if (!editable || !frame.ball) return;
    const d = keyStep(e.key, e.shiftKey ? 2 : 0.5);
    if (d) {
      e.preventDefault();
      onGestureStart?.();
      const [nx, ny] = keepIn(frame.ball.x + d[0], frame.ball.y + d[1]);
      update({ ball: { x: nx, y: ny } });
    } else if (e.key === "Delete" || e.key === "Backspace") {
      e.preventDefault();
      onGestureStart?.();
      update({ ball: null });
      onSelect?.(null);
    }
  }

  const poly = (pts: readonly Point[]) => pts.map(([x, y], i) => `${i ? "L" : "M"}${S(x, y).join(" ")}`).join(" ");
  const sides = court === "half" ? (["right"] as const) : (["left", "right"] as const);
  const L = COURT.lines;
  const lineW = Math.max(0.09, 1.3 / pxPerM);
  const [bx0, by0] = S(view.x0, COURT.width);
  const [bx1, by1] = S(view.x1, 0);

  // the ball held by a player sits at the player's lower right, so it does not hide the number
  const holder = ball ? tokens.find((k) => Math.hypot(k.x - ball.x, k.y - ball.y) < R) : null;
  const ballAt = ball ? (holder ? ((([sx, sy]) => [sx + R * 0.72, sy + R * 0.72])(S(holder.x, holder.y)) as [number, number]) : S(ball.x, ball.y)) : null;

  const shownArrows = live ? frame.arrows : [...frame.arrows, ...(draft ? [draft] : [])];

  return (
    <svg
      ref={svg}
      viewBox={`0 0 ${view.w} ${view.h}`}
      role="group"
      aria-label={label}
      className={`block w-full select-none ${editable ? "touch-none" : ""} ${editable && tool !== "move" ? "cursor-crosshair" : ""} ${className ?? "h-auto"}`}
      style={{ background: BOARD_THEME.surround }}
      onPointerDown={onDown}
      onPointerMove={onMove}
      onPointerUp={onUp}
      onPointerCancel={onUp}
      data-testid="tactics-board"
      data-orientation={portrait ? "portrait" : "landscape"}
    >
      <defs>
        <marker id={`hb-arrow-${uid}`} viewBox="0 0 10 10" refX="7" refY="5" markerWidth="4" markerHeight="4" markerUnits="strokeWidth" orient="auto-start-reverse">
          <path d="M0 0 L10 5 L0 10 z" fill={BOARD_THEME.line} />
        </marker>
      </defs>

      {/* floor, goal areas, lines, goals */}
      <rect x={Math.min(bx0, bx1)} y={Math.min(by0, by1)} width={Math.abs(bx1 - bx0)} height={Math.abs(by1 - by0)} fill={BOARD_THEME.floor} />
      {sides.map((s) => (
        <path key={`ga-${s}`} d={`${poly(L[`goal_area_${s}`] ?? [])} Z`} fill={BOARD_THEME.goalArea} />
      ))}
      <g fill="none" stroke={BOARD_THEME.line} strokeWidth={lineW} strokeLinecap="round">
        <rect x={Math.min(bx0, bx1)} y={Math.min(by0, by1)} width={Math.abs(bx1 - bx0)} height={Math.abs(by1 - by0)} />
        {court === "full" && <path d={poly(L.center_line ?? [])} />}
        {sides.map((s) => (
          <g key={s}>
            <path d={poly(L[`goal_area_${s}`] ?? [])} strokeWidth={lineW * 1.4} />
            <path d={poly(L[`free_throw_${s}`] ?? [])} strokeDasharray={`${0.45} ${0.4}`} />
            <path d={poly(L[`penalty_mark_${s}`] ?? [])} strokeWidth={lineW * 1.6} />
            <path d={poly(L[`gk_line_${s}`] ?? [])} />
          </g>
        ))}
      </g>
      {sides.map((s) => {
        const gx = s === "right" ? COURT.length : 0;
        const back = s === "right" ? gx + 1 : gx - 1;
        const [ax, ay] = S(gx, 8.5);
        const [cx, cy] = S(back, 11.5);
        return (
          <g key={`goal-${s}`}>
            <rect x={Math.min(ax, cx)} y={Math.min(ay, cy)} width={Math.abs(cx - ax)} height={Math.abs(cy - ay)} fill="#ffffff" stroke={BOARD_THEME.line} strokeWidth={lineW} />
            <path d={poly([[gx, 8.5], [gx, 11.5]])} stroke={BOARD_THEME.line} strokeWidth={lineW * 3} strokeLinecap="square" />
          </g>
        );
      })}

      {cones?.map(([x, y], i) => {
        const [sx, sy] = S(x, y);
        return <path key={`cone-${i}`} d={`M${sx} ${sy - 0.42} L${sx + 0.38} ${sy + 0.3} L${sx - 0.38} ${sy + 0.3} Z`} fill={BOARD_THEME.cone} stroke={BOARD_THEME.rim} strokeWidth={0.09} strokeLinejoin="round" />;
      })}

      {/* runs, passes, dribbles, screens; faint while the phase is being played */}
      <g opacity={live ? 0.35 : 1}>
        {shownArrows.map((a, i) => (
          <ArrowPath key={i} arrow={a} S={S} tokens={tokens} markerId={`hb-arrow-${uid}`} selected={editable && selected === `arrow:${i}`} pxPerM={pxPerM} />
        ))}
      </g>

      {tokens.map((k) => {
        const isSel = editable && selected === k.id;
        const [sx, sy] = S(k.x, k.y);
        const own = k.side === "own";
        const size = k.label.length >= 3 ? 0.66 : k.label.length === 2 ? 0.8 : 0.95;
        return (
          <g
            key={k.id}
            transform={`translate(${sx} ${sy})`}
            tabIndex={editable ? 0 : -1}
            role={editable ? "button" : "img"}
            aria-label={`${own ? t("own") : t("opp")} ${k.label}`}
            aria-pressed={editable ? isSel : undefined}
            onFocus={() => editable && onSelect?.(k.id)}
            onKeyDown={(e) => onTokenKey(e, k)}
            className="outline-none [&:focus-visible>circle.ring]:opacity-100"
            data-testid={`token-${k.id}`}
          >
            {editable && <circle r={hitR} fill="transparent" />}
            <circle className="ring" r={R + 0.32} fill="none" stroke={BOARD_THEME.select} strokeWidth={0.26} opacity={isSel ? 1 : 0} />
            <circle r={R} fill={own ? BOARD_THEME.own : BOARD_THEME.opp} stroke={BOARD_THEME.rim} strokeWidth={0.1} />
            {showLabels && (
              <text y={size * 0.36} textAnchor="middle" fontSize={size} fontWeight={800} fill={own ? BOARD_THEME.ownText : BOARD_THEME.oppText} style={{ pointerEvents: "none" }}>
                {k.label}
              </text>
            )}
          </g>
        );
      })}
      {ballAt && (
        <g
          transform={`translate(${ballAt[0]} ${ballAt[1]})`}
          tabIndex={editable ? 0 : -1}
          role={editable ? "button" : "img"}
          aria-label={t("tool_ball")}
          onFocus={() => editable && onSelect?.("ball")}
          onKeyDown={onBallKey}
          className="outline-none"
          data-testid="ball"
        >
          <circle r={0.62} fill="none" stroke={BOARD_THEME.select} strokeWidth={0.2} opacity={editable && selected === "ball" ? 1 : 0} />
          <circle r={0.4} fill={BOARD_THEME.ball} stroke={BOARD_THEME.rim} strokeWidth={0.1} />
          <path d="M-0.4 0 Q0 -0.14 0.4 0 M0 -0.4 Q0.14 0 0 0.4" fill="none" stroke={BOARD_THEME.rim} strokeWidth={0.05} />
        </g>
      )}
    </svg>
  );
}

/** a smooth path through the points (Catmull-Rom as cubic Béziers) */
function smooth(pts: readonly (readonly [number, number])[]): string {
  if (pts.length < 3) return pts.map(([x, y], i) => `${i ? "L" : "M"}${x} ${y}`).join(" ");
  let d = `M${pts[0]![0]} ${pts[0]![1]}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[Math.max(0, i - 1)]!;
    const p1 = pts[i]!;
    const p2 = pts[i + 1]!;
    const p3 = pts[Math.min(pts.length - 1, i + 2)]!;
    d += ` C${p1[0] + (p2[0] - p0[0]) / 6} ${p1[1] + (p2[1] - p0[1]) / 6} ${p2[0] - (p3[0] - p1[0]) / 6} ${p2[1] - (p3[1] - p1[1]) / 6} ${p2[0]} ${p2[1]}`;
  }
  return d;
}

function ArrowPath({
  arrow,
  S,
  tokens,
  markerId,
  selected,
  pxPerM,
}: {
  arrow: Arrow;
  S: (x: number, y: number) => [number, number];
  tokens: Token[];
  markerId: string;
  selected: boolean;
  pxPerM: number;
}) {
  let pts = arrow.points.map(([x, y]) => S(x, y));
  // an arrow that ends on a player stops at the player's rim, so the head stays visible
  const endCourt = arrow.points[arrow.points.length - 1]!;
  if (pts.length >= 2 && tokens.some((k) => Math.hypot(k.x - endCourt[0], k.y - endCourt[1]) < R * 0.9)) {
    const [ex, ey] = pts[pts.length - 1]!;
    const [px, py] = pts[pts.length - 2]!;
    const len = Math.hypot(ex - px, ey - py) || 1;
    const cut = Math.min(R + 0.15, len * 0.6);
    pts = [...pts.slice(0, -1), [ex - ((ex - px) / len) * cut, ey - ((ey - py) / len) * cut]];
  }
  const w = Math.max(0.14, 2.2 / pxPerM);
  const common = { fill: "none", stroke: BOARD_THEME.line, strokeWidth: w, strokeLinecap: "round" as const, strokeLinejoin: "round" as const };
  const under = selected ? <path d={smooth(pts)} fill="none" stroke={BOARD_THEME.select} strokeWidth={w * 4} strokeLinecap="round" /> : null;
  const b = pts[pts.length - 1]!;
  if (arrow.kind === "dribble") {
    // zigzag along the polyline
    const segs: string[] = [];
    let n = 0;
    for (let i = 1; i < pts.length; i++) {
      const [x0, y0] = pts[i - 1]!;
      const [x1, y1] = pts[i]!;
      const len = Math.hypot(x1 - x0, y1 - y0);
      const steps = Math.max(2, Math.round(len / 0.55));
      const nx = -(y1 - y0) / (len || 1);
      const ny = (x1 - x0) / (len || 1);
      for (let k = i === 1 ? 0 : 1; k <= steps; k++) {
        const tt = k / steps;
        const last = i === pts.length - 1 && k === steps;
        const off = n === 0 || last ? 0 : n % 2 ? 0.28 : -0.28;
        segs.push(`${segs.length ? "L" : "M"}${x0 + (x1 - x0) * tt + nx * off} ${y0 + (y1 - y0) * tt + ny * off}`);
        n++;
      }
    }
    return (
      <g data-kind="dribble">
        {under}
        <path d={segs.join(" ")} {...common} markerEnd={`url(#${markerId})`} />
      </g>
    );
  }
  if (arrow.kind === "screen") {
    const [px, py] = pts[pts.length - 2]!;
    const dx = b[0] - px;
    const dy = b[1] - py;
    const len = Math.hypot(dx, dy) || 1;
    const qx = (-dy / len) * 0.6;
    const qy = (dx / len) * 0.6;
    return (
      <g data-kind="screen">
        {under}
        <path d={smooth(pts)} {...common} />
        <path d={`M${b[0] - qx} ${b[1] - qy} L${b[0] + qx} ${b[1] + qy}`} {...common} strokeWidth={w * 1.6} strokeLinecap="butt" />
      </g>
    );
  }
  return (
    <g data-kind={arrow.kind}>
      {under}
      <path d={smooth(pts)} {...common} strokeDasharray={arrow.kind === "pass" ? `${w * 3.2} ${w * 2.4}` : undefined} markerEnd={`url(#${markerId})`} />
    </g>
  );
}
