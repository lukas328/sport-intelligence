"use client";

import { useCallback, useEffect, useImperativeHandle, useRef, useState, forwardRef, type PointerEvent as ReactPointerEvent } from "react";
import { courtPolylines } from "@/lib/court-calibration";
import { LINE_NAMES, linePolylines, type ClickRef, type Clicks, type CourtModel, type Pt } from "@/lib/court-fit";
import { snapMargin, snapToLine } from "@/lib/court-snap";
import type { Homography } from "@/lib/spotlight";

/** What is drawn over the hall image: a suggested court (orange), the live fit (cyan), a fit the
 * clicks disagree with (red, dashed). */
export type OverlayTone = "suggest" | "fit" | "draft" | "bad";
const TONE: Record<OverlayTone, string> = { suggest: "#f97316", fit: "#22d3ee", draft: "#22d3ee", bad: "#f87171" };

type View = { x: number; y: number; w: number; h: number };

export interface StageHandle {
  zoom: (factor: number) => void;
  fit: () => void;
}

const pathOf = (pts: Pt[]) => pts.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)} ${y.toFixed(1)}`).join(" ");
const sameRef = (a: ClickRef | null, b: ClickRef | null) => !!a && !!b && a.kind === b.kind && a.name === b.name && (a.kind === "point" || (b.kind === "line" && a.index === b.index));

const LOUPE = 128; // css px
const MAGNIFY = 3; // loupe pixels per screen pixel of the picture
const HIT = 16; // screen px around a click that grab it
const SLOP = 5; // screen px a press may wander and still be a tap

/**
 * The hall image with the court and the clicks on it. One finger or the mouse: press, see the
 * spot in the loupe, release to place the click (it snaps onto the painted line nearby); a press
 * on a click drags it. Two fingers or the wheel zoom and move the picture; near the edge while
 * placing, a zoomed picture follows the finger.
 */
export const CalibrationStage = forwardRef<
  StageHandle,
  {
    src: string;
    alt: string;
    label: string;
    size: [number, number];
    model: CourtModel;
    overlay: { homography: Homography; tone: OverlayTone } | null;
    clicks: Clicks;
    current: { kind: "line" | "point"; name: string } | null;
    selected: ClickRef | null;
    flagged: ClickRef[];
    interactive: boolean;
    snap: boolean;
    onPlace: (p: Pt) => void;
    onDrag: (ref: ClickRef, p: Pt) => void;
    onMove: (ref: ClickRef, p: Pt, prev: Pt) => void;
    /** a tap right on a click: it becomes the one the arrow keys move */
    onSelect: (ref: ClickRef) => void;
    onZoomChange?: (zoomed: boolean) => void;
  }
>(function CalibrationStage({ src, alt, label, size, model, overlay, clicks, current, selected, flagged, interactive, snap, onPlace, onDrag, onMove, onSelect, onZoomChange }, ref) {
  const [W, H] = size;
  const full: View = { x: 0, y: 0, w: W, h: H };
  const [view, setView] = useState<View>(full);
  const box = useRef<HTMLDivElement>(null);
  const svg = useRef<SVGSVGElement>(null);
  const loupe = useRef<HTMLCanvasElement>(null);
  const pixels = useRef<CanvasRenderingContext2D | null>(null);
  const image = useRef<HTMLImageElement | null>(null);
  const [rect, setRect] = useState({ w: 0, h: 0 });
  const pointers = useRef(new Map<number, { x: number; y: number }>());
  const gesture = useRef<
    | { kind: "place"; id: number; at: Pt; shift: boolean }
    | { kind: "drag"; id: number; ref: ClickRef; prev: Pt; at: Pt; press: Pt; sx: number; sy: number; moved: boolean; shift: boolean }
    | { kind: "pinch"; view: View; dist: number; mid: Pt }
    | null
  >(null);
  const [aim, setAim] = useState<{ p: Pt; target: Pt | null; right: boolean } | null>(null);
  const [drag, setDrag] = useState<{ ref: ClickRef; p: Pt } | null>(null);

  // the picture's pixels for the loupe and for snapping (same origin: readable)
  useEffect(() => {
    const img = new Image();
    img.onload = () => {
      image.current = img;
      const c = document.createElement("canvas");
      c.width = img.naturalWidth;
      c.height = img.naturalHeight;
      const ctx = c.getContext("2d", { willReadFrequently: true });
      if (!ctx) return;
      ctx.drawImage(img, 0, 0);
      pixels.current = ctx;
    };
    img.src = src;
    return () => {
      img.onload = null;
    };
  }, [src]);

  useEffect(() => {
    const el = box.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setRect({ w: el.clientWidth, h: el.clientHeight }));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // where the view sits in the box (letterboxed like preserveAspectRatio meet)
  const layout = useCallback(
    (v: View) => {
      const el = svg.current;
      const r = el?.getBoundingClientRect();
      const bw = r?.width ?? 1;
      const bh = r?.height ?? 1;
      const scale = Math.min(bw / v.w, bh / v.h);
      return { left: (r?.left ?? 0) + (bw - v.w * scale) / 2, top: (r?.top ?? 0) + (bh - v.h * scale) / 2, scale, bw, bh, r };
    },
    [],
  );
  const toImage = useCallback(
    (sx: number, sy: number, v: View = view): Pt => {
      const l = layout(v);
      return [v.x + (sx - l.left) / l.scale, v.y + (sy - l.top) / l.scale];
    },
    [layout, view],
  );

  const clamp = useCallback(
    (v: View): View => {
      const w = Math.min(W, Math.max(W / 10, v.w));
      const h = (w * H) / W;
      return { w, h, x: Math.min(W - w, Math.max(0, v.x)), y: Math.min(H - h, Math.max(0, v.y)) };
    },
    [W, H],
  );
  const zoomAt = useCallback((factor: number, at?: Pt) => setView((v) => {
    const c = at ?? [v.x + v.w / 2, v.y + v.h / 2];
    const w = v.w / factor;
    const h = (w * H) / W;
    return clamp({ w, h, x: c[0] - ((c[0] - v.x) * w) / v.w, y: c[1] - ((c[1] - v.y) * h) / v.h });
  }), [clamp, W, H]);
  useImperativeHandle(ref, () => ({ zoom: (f: number) => zoomAt(f), fit: () => setView({ x: 0, y: 0, w: W, h: H }) }), [zoomAt, W, H]);
  const zoomed = view.w < W - 0.5;
  useEffect(() => onZoomChange?.(zoomed), [zoomed, onZoomChange]);

  // the wheel zooms around the pointer (a passive listener cannot keep the page from scrolling)
  useEffect(() => {
    const el = svg.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      zoomAt(e.deltaY < 0 ? 1.25 : 0.8, toImage(e.clientX, e.clientY));
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, [zoomAt, toImage]);

  const scale = rect.w > 0 ? Math.min(rect.w / view.w, rect.h / view.h) : 1; // screen px per image px
  const per = 1 / scale; // image px per screen px

  function snapped(p: Pt): Pt {
    const ctx = pixels.current;
    if (!snap || !ctx) return p;
    const radius = Math.min(40, Math.max(6, 14 * per));
    const m = snapMargin(radius);
    const x0 = Math.max(0, Math.floor(p[0] - m));
    const y0 = Math.max(0, Math.floor(p[1] - m));
    const w = Math.min(W, Math.ceil(p[0] + m)) - x0;
    const h = Math.min(H, Math.ceil(p[1] + m)) - y0;
    if (w <= 2 || h <= 2) return p;
    const d = ctx.getImageData(x0, y0, w, h);
    return snapToLine({ data: d.data, width: w, height: h, x0, y0 }, p, radius);
  }

  function nearest(p: Pt): { ref: ClickRef; at: Pt } | null {
    let best: { ref: ClickRef; at: Pt } | null = null;
    let bd = HIT * per;
    for (const [name, q] of Object.entries(clicks.points)) {
      const d = Math.hypot(q[0] - p[0], q[1] - p[1]);
      if (d < bd) [bd, best] = [d, { ref: { kind: "point", name }, at: q }];
    }
    for (const [name, l] of Object.entries(clicks.lines))
      l.forEach((q, index) => {
        const d = Math.hypot(q[0] - p[0], q[1] - p[1]);
        if (d < bd) [bd, best] = [d, { ref: { kind: "line", name, index }, at: q }];
      });
    return best;
  }

  // near the edge of a zoomed picture: it follows the finger
  function follow(sx: number, sy: number) {
    if (!zoomed) return;
    const l = layout(view);
    const r = l.r;
    if (!r) return;
    const edge = 32;
    const step = view.w * 0.03;
    let dx = 0;
    let dy = 0;
    if (sx - r.left < edge) dx = -step;
    else if (r.right - sx < edge) dx = step;
    if (sy - r.top < edge) dy = -step;
    else if (r.bottom - sy < edge) dy = step;
    if (dx || dy) setView((v) => clamp({ ...v, x: v.x + dx, y: v.y + dy }));
  }

  function aimAt(p: Pt, sx: number, withSnap: boolean) {
    const l = layout(view);
    setAim({ p, target: withSnap ? snapped(p) : null, right: sx - (l.r?.left ?? 0) < (l.bw ?? 0) / 2 });
  }

  function down(e: ReactPointerEvent<SVGSVGElement>) {
    pointers.current.set(e.pointerId, { x: e.clientX, y: e.clientY });
    e.currentTarget.setPointerCapture(e.pointerId);
    if (pointers.current.size === 2) {
      // two fingers: zoom and move the picture, no click
      const [a, b] = [...pointers.current.values()] as [{ x: number; y: number }, { x: number; y: number }];
      gesture.current = { kind: "pinch", view, dist: Math.hypot(a.x - b.x, a.y - b.y), mid: toImage((a.x + b.x) / 2, (a.y + b.y) / 2) };
      setAim(null);
      setDrag(null);
      return;
    }
    if (!interactive || pointers.current.size > 1) return;
    const p = toImage(e.clientX, e.clientY);
    const hit = nearest(p);
    if (hit) {
      // a drag once the finger moves; a tap beside the click still places one
      gesture.current = { kind: "drag", id: e.pointerId, ref: hit.ref, prev: hit.at, at: hit.at, press: p, sx: e.clientX, sy: e.clientY, moved: false, shift: e.shiftKey };
      aimAt(hit.at, e.clientX, false);
      return;
    }
    gesture.current = { kind: "place", id: e.pointerId, at: p, shift: e.shiftKey };
    aimAt(p, e.clientX, !e.shiftKey);
  }

  function move(e: ReactPointerEvent<SVGSVGElement>) {
    if (pointers.current.has(e.pointerId)) pointers.current.set(e.pointerId, { x: e.clientX, y: e.clientY });
    const g = gesture.current;
    if (g?.kind === "pinch") {
      const pts = [...pointers.current.values()];
      if (pts.length < 2) return;
      const [a, b] = pts as [{ x: number; y: number }, { x: number; y: number }];
      const f = Math.hypot(a.x - b.x, a.y - b.y) / Math.max(1, g.dist);
      const w = g.view.w / f;
      const h = (w * H) / W;
      const l = layout({ ...g.view, w, h });
      const mx = (a.x + b.x) / 2;
      const my = (a.y + b.y) / 2;
      setView(clamp({ w, h, x: g.mid[0] - (mx - l.left) / l.scale, y: g.mid[1] - (my - l.top) / l.scale }));
      return;
    }
    const p = toImage(e.clientX, e.clientY);
    if (g?.kind === "drag" && g.id === e.pointerId) {
      if (!g.moved && Math.hypot(e.clientX - g.sx, e.clientY - g.sy) < SLOP) return;
      g.moved = true;
      // the click follows the finger by the finger's way (it does not jump under it)
      g.at = [g.prev[0] + p[0] - g.press[0], g.prev[1] + p[1] - g.press[1]];
      setDrag({ ref: g.ref, p: g.at });
      onDrag(g.ref, g.at);
      aimAt(g.at, e.clientX, false);
      follow(e.clientX, e.clientY);
      return;
    }
    if (g?.kind === "place" && g.id === e.pointerId) {
      g.at = p;
      aimAt(p, e.clientX, !g.shift && !e.shiftKey);
      follow(e.clientX, e.clientY);
      return;
    }
    // the mouse hovering: the loupe shows the spot before the click
    if (!g && interactive && e.pointerType === "mouse") aimAt(p, e.clientX, !e.shiftKey);
  }

  function up(e: ReactPointerEvent<SVGSVGElement>) {
    pointers.current.delete(e.pointerId);
    const g = gesture.current;
    if (g?.kind === "pinch") {
      if (pointers.current.size === 0) gesture.current = null;
      return;
    }
    if (g?.kind === "drag" && g.id === e.pointerId) {
      gesture.current = null;
      setDrag(null);
      if (g.moved) {
        if (Math.hypot(g.at[0] - g.prev[0], g.at[1] - g.prev[1]) > 0.01) onMove(g.ref, g.at, g.prev);
      } else if (Math.hypot(g.press[0] - g.prev[0], g.press[1] - g.prev[1]) * scale < SLOP + 1) onSelect(g.ref);
      else onPlace(g.shift || e.shiftKey ? g.press : snapped(g.press));
      if (e.pointerType !== "mouse") setAim(null);
      return;
    }
    if (g?.kind === "place" && g.id === e.pointerId) {
      gesture.current = null;
      const inside = g.at[0] >= 0 && g.at[1] >= 0 && g.at[0] <= W && g.at[1] <= H;
      if (inside) onPlace(g.shift || e.shiftKey ? g.at : snapped(g.at));
      if (e.pointerType !== "mouse") setAim(null);
    }
  }

  function cancel(e: ReactPointerEvent<SVGSVGElement>) {
    pointers.current.delete(e.pointerId);
    gesture.current = null;
    setAim(null);
    setDrag(null);
  }

  // the loupe: the spot under the finger, magnified, with the court and the crosshair
  useEffect(() => {
    const c = loupe.current;
    const img = image.current;
    if (!c || !aim || !img) return;
    const dpr = window.devicePixelRatio || 1;
    const px = Math.round(LOUPE * dpr);
    if (c.width !== px) [c.width, c.height] = [px, px];
    const ctx = c.getContext("2d");
    if (!ctx) return;
    const side = LOUPE / (MAGNIFY * scale); // image px shown
    const sx = aim.p[0] - side / 2;
    const sy = aim.p[1] - side / 2;
    const k = px / side;
    ctx.fillStyle = "#000";
    ctx.fillRect(0, 0, px, px);
    ctx.imageSmoothingEnabled = false;
    ctx.drawImage(img, sx, sy, side, side, 0, 0, px, px);
    const to = (q: Pt): Pt => [(q[0] - sx) * k, (q[1] - sy) * k];
    if (overlay) {
      ctx.strokeStyle = TONE[overlay.tone];
      ctx.lineWidth = 1.5 * dpr;
      for (const line of courtPolylines(overlay.homography)) {
        ctx.beginPath();
        line.map(to).forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
        ctx.stroke();
      }
    }
    ctx.strokeStyle = "#ffd23c";
    ctx.lineWidth = 2 * dpr;
    for (const q of [...Object.values(clicks.points), ...Object.values(clicks.lines).flat()]) {
      const [x, y] = to(q);
      ctx.beginPath();
      ctx.arc(x, y, 5 * dpr, 0, 7);
      ctx.stroke();
    }
    const m = px / 2;
    ctx.strokeStyle = "#fff";
    ctx.lineWidth = 1 * dpr;
    ctx.beginPath();
    ctx.moveTo(m, m - 14 * dpr);
    ctx.lineTo(m, m - 4 * dpr);
    ctx.moveTo(m, m + 4 * dpr);
    ctx.lineTo(m, m + 14 * dpr);
    ctx.moveTo(m - 14 * dpr, m);
    ctx.lineTo(m - 4 * dpr, m);
    ctx.moveTo(m + 4 * dpr, m);
    ctx.lineTo(m + 14 * dpr, m);
    ctx.stroke();
    if (aim.target) {
      const [x, y] = to(aim.target);
      ctx.strokeStyle = "#22d3ee";
      ctx.lineWidth = 2 * dpr;
      ctx.beginPath();
      ctx.arc(x, y, 4 * dpr, 0, 7);
      ctx.stroke();
    }
  }, [aim, overlay, clicks, scale]);

  const shown = drag ? (() => {
    // the dragged click where the finger is
    const c: Clicks = { points: { ...clicks.points }, lines: { ...clicks.lines } };
    if (drag.ref.kind === "point") c.points[drag.ref.name] = drag.p;
    else {
      const l = (c.lines[drag.ref.name] ?? []).slice();
      l[drag.ref.index] = drag.p;
      c.lines[drag.ref.name] = l;
    }
    return c;
  })() : clicks;

  const r = 7 * per;
  const stroke = Math.max(1, 1.5 * per);
  const tone = overlay ? TONE[overlay.tone] : "#22d3ee";
  const currentLine = overlay && current?.kind === "line" && model.lines[current.name] ? linePolylines(overlay.homography, model.lines[current.name]!.court) : [];
  const currentPoint = overlay && current?.kind === "point" ? model.points[current.name] : undefined;
  const marker = (ref: ClickRef, q: Pt, key: string, mark: string) => {
    const isFlagged = flagged.some((f) => sameRef(f, ref));
    const isCurrent = current?.kind === ref.kind && current.name === ref.name;
    return (
      <g key={key}>
        {sameRef(selected, ref) && <circle cx={q[0]} cy={q[1]} r={r * 1.9} fill="none" stroke="#fff" strokeWidth={stroke} strokeDasharray={`${3 * per} ${2 * per}`} />}
        <circle cx={q[0]} cy={q[1]} r={r} fill={isFlagged ? "#f87171" : isCurrent ? "#ffd23c" : "#ffffff"} fillOpacity={0.35} stroke="#000" strokeWidth={stroke * 2.4} />
        <circle cx={q[0]} cy={q[1]} r={r} fill="none" stroke={isFlagged ? "#f87171" : isCurrent ? "#ffd23c" : "#ffffff"} strokeWidth={stroke * 1.4} />
        <circle cx={q[0]} cy={q[1]} r={stroke * 0.9} fill="#000" />
        <text x={q[0] + r * 1.3} y={q[1] - r * 1.1} fontSize={13 * per} fontWeight={700} fill={isFlagged ? "#f87171" : isCurrent ? "#ffd23c" : "#ffffff"} stroke="#000" strokeWidth={3 * per} paintOrder="stroke">
          {mark}
        </text>
      </g>
    );
  };

  return (
    <div ref={box} className="relative size-full min-h-0 bg-[#0a0d11]">
      <svg
        ref={svg}
        viewBox={`${view.x} ${view.y} ${view.w} ${view.h}`}
        preserveAspectRatio="xMidYMid meet"
        className={`block size-full select-none ${interactive ? "cursor-crosshair" : ""}`}
        style={{ touchAction: "none" }}
        role="img"
        aria-label={label}
        onPointerDown={down}
        onPointerMove={move}
        onPointerUp={up}
        onPointerCancel={cancel}
        onPointerLeave={(e) => e.pointerType === "mouse" && !gesture.current && setAim(null)}
        data-testid="calibration-stage"
        data-zoomed={zoomed || undefined}
      >
        <image href={src} x={0} y={0} width={W} height={H} preserveAspectRatio="none">
          <title>{alt}</title>
        </image>
        {overlay && (
          <g data-testid={`overlay-${overlay.tone}`}>
            {/* a dark halo under the colour: the lines stand out on any hall floor */}
            {courtPolylines(overlay.homography).map((line, i) => (
              <path key={`h${i}`} d={pathOf(line)} fill="none" stroke="#000" strokeOpacity={0.5} strokeWidth={4.5} vectorEffect="non-scaling-stroke" />
            ))}
            {courtPolylines(overlay.homography).map((line, i) => (
              <path
                key={i}
                d={pathOf(line)}
                fill="none"
                stroke={tone}
                strokeWidth={2}
                strokeDasharray={overlay.tone === "bad" || overlay.tone === "draft" ? "8 6" : undefined}
                vectorEffect="non-scaling-stroke"
              />
            ))}
            {/* where the chosen line should be, as far as the court is known */}
            {currentLine.map((line, i) => (
              <path key={`c${i}`} d={pathOf(line)} fill="none" stroke="#ffd23c" strokeOpacity={0.9} strokeWidth={4} vectorEffect="non-scaling-stroke" />
            ))}
          </g>
        )}
        {currentPoint &&
          (() => {
            const p = overlay ? toImagePoint(overlay.homography, currentPoint) : null;
            return p ? <circle cx={p[0]} cy={p[1]} r={r * 1.4} fill="none" stroke="#ffd23c" strokeWidth={stroke * 2} /> : null;
          })()}
        {Object.entries(shown.lines).map(([name, l]) => l.map((q, index) => marker({ kind: "line", name, index }, q, `${name}-${index}`, String(LINE_NAMES.indexOf(name as (typeof LINE_NAMES)[number]) + 1))))}
        {Object.entries(shown.points).map(([name, q]) => marker({ kind: "point", name }, q, `p-${name}`, "P"))}
        {aim?.target && <circle cx={aim.target[0]} cy={aim.target[1]} r={r * 0.7} fill="none" stroke="#22d3ee" strokeWidth={stroke * 1.5} />}
      </svg>
      {/* the loupe sits in the corner away from the finger */}
      <canvas
        ref={loupe}
        aria-hidden
        hidden={!aim}
        className={`pointer-events-none absolute top-2 size-32 border-2 border-white bg-black ${aim?.right ? "right-2" : "left-2"}`}
        data-testid="calibration-loupe"
      />
    </div>
  );
});

function toImagePoint(h: Homography, p: Pt): Pt | null {
  const w = h[2]![0]! * p[0] + h[2]![1]! * p[1] + h[2]![2]!;
  if (w <= 1e-9) return null;
  return [(h[0]![0]! * p[0] + h[0]![1]! * p[1] + h[0]![2]!) / w, (h[1]![0]! * p[0] + h[1]![1]! * p[1] + h[1]![2]!) / w];
}
