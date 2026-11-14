"use client";

import { useTranslations } from "next-intl";
import { useEffect, useRef, useState, type KeyboardEvent, type PointerEvent } from "react";
import { courtPolylines, fitHomography, type Pt } from "@/lib/court-calibration";
import { CORNER_NAMES as NAMES, CORNERS, handleAt } from "@/lib/field-corners";

export { CORNERS, cornersOf } from "@/lib/field-corners";

const pathOf = (pts: Pt[]) =>
  pts.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)} ${y.toFixed(1)}`).join(" ");

/**
 * Prüfen, the court (UX test B13, B14): the hall image with the recognised court drawn on it and
 * four handles on the corners. Dragging a corner redraws the court at once; the keyboard moves a
 * focused handle with the arrow keys. The image may be smaller than the court: the area around
 * it stays reachable.
 */
export function FieldCheck({
  src,
  alt,
  size,
  corners,
  onChange,
}: {
  src: string;
  alt: string;
  size: [number, number];
  corners: Pt[];
  onChange: (c: Pt[]) => void;
}) {
  const t = useTranslations("check");
  const tc = useTranslations("calibrate");
  const svg = useRef<SVGSVGElement>(null);
  // a drag moves the corner by the finger's way, so a corner outside the picture stays there
  // until it is pulled in (E03, E04)
  const drag = useRef<{ i: number; from: Pt; start: Pt } | null>(null);
  const [zoom, setZoom] = useState(1);
  const [w, h] = size;
  const pad = Math.round(Math.max(w, h) * 0.06);
  const fit = fitHomography([...CORNERS], corners);
  const lines = fit ? courtPolylines(fit) : [];
  // handles in screen pixels, whatever the image's size: 44 px to touch, 16 px to see (UX test N17)
  const [shown, setShown] = useState(0);
  useEffect(() => {
    const el = svg.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setShown(el.getBoundingClientRect().width));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  const perPx = shown > 0 ? (w + 2 * pad) / shown : Math.max(w, h) / 900;
  const r = 8 * perPx;
  const touch = 22 * perPx;
  const [active, setActive] = useState<number | null>(null);

  function at(e: PointerEvent): Pt | null {
    const el = svg.current;
    const m = el?.getScreenCTM();
    if (!el || !m) return null;
    const p = new DOMPoint(e.clientX, e.clientY).matrixTransform(m.inverse());
    return [p.x, p.y];
  }
  const move = (i: number, p: Pt) => onChange(corners.map((c, k) => (k === i ? p : c)));
  function key(i: number, e: KeyboardEvent) {
    const step = (e.shiftKey ? 20 : 4) * (w / 1000);
    const d: Record<string, Pt> = {
      ArrowLeft: [-step, 0],
      ArrowRight: [step, 0],
      ArrowUp: [0, -step],
      ArrowDown: [0, step],
    };
    const v = d[e.key];
    if (!v) return;
    e.preventDefault();
    move(i, [corners[i]![0] + v[0], corners[i]![1] + v[1]]);
  }

  return (
    <div className="relative" data-testid="field-check">
      {/* on a phone the picture can be enlarged and moved with a finger; only the handles take
          the finger for themselves (touch-action on them), so a swipe beside them moves the
          picture and never loses a corner (fourth real-video test, G9) */}
      <div className="overflow-auto overscroll-x-contain" data-testid="field-frame">
        <svg
          ref={svg}
          viewBox={`${-pad} ${-pad} ${w + 2 * pad} ${h + 2 * pad}`}
          style={{ width: `${zoom * 100}%` }}
          className="block max-w-none touch-pan-x touch-pan-y select-none"
          role="group"
          aria-label={t("fieldHandles")}
          onPointerMove={(e) => {
            const d = drag.current;
            if (d == null) return;
            const p = at(e);
            if (p) move(d.i, [d.start[0] + p[0] - d.from[0], d.start[1] + p[1] - d.from[1]]);
          }}
          onPointerUp={() => ((drag.current = null), setActive(null))}
          onPointerLeave={() => ((drag.current = null), setActive(null))}
        >
          <image href={src} x={0} y={0} width={w} height={h} preserveAspectRatio="none">
            <title>{alt}</title>
          </image>
          {lines.map((l, i) => (
            // thin and half see-through: the hall's own lines stay visible underneath (E04)
            <path
              key={i}
              d={pathOf(l)}
              fill="none"
              stroke="white"
              strokeOpacity={0.6}
              strokeWidth={2}
              vectorEffect="non-scaling-stroke"
            />
          ))}
          <path
            d={`${pathOf(corners)} Z`}
            fill="rgb(246 197 0 / 0.08)"
            stroke="var(--attn)"
            strokeOpacity={0.8}
            strokeWidth={2}
            strokeDasharray="10 6"
            vectorEffect="non-scaling-stroke"
          />
          {corners.map((c, i) => {
            const [x, y] = handleAt(c, corners, w, h);
            const outside = x !== c[0] || y !== c[1];
            return (
              <g
                key={NAMES[i]}
                role="slider"
                tabIndex={0}
                aria-label={
                  outside
                    ? `${tc(`landmarks.${NAMES[i]}`)}. ${t("cornerOutside")}`
                    : tc(`landmarks.${NAMES[i]}`)
                }
                aria-valuetext={`${Math.round(x)}, ${Math.round(y)}`}
                aria-valuenow={Math.round(x)}
                style={{ touchAction: "none" }}
                className="cursor-grab outline-none focus-visible:[&>circle:last-child]:stroke-ink"
                onPointerDown={(e) => {
                  const p = at(e);
                  if (p) drag.current = { i, from: p, start: corners[i]! };
                  setActive(i);
                  (e.currentTarget as Element).closest("svg")?.setPointerCapture(e.pointerId);
                }}
                onKeyDown={(e) => key(i, e)}
                data-testid={`corner-${i}`}
              >
                {/* the touch target is larger than the drawn handle */}
                <circle cx={x} cy={y} r={touch} fill="transparent" />
                {/* while dragging: lines through the corner, visible beside the finger */}
                {active === i && (
                  <>
                    <line
                      x1={x - 6 * touch}
                      y1={y}
                      x2={x + 6 * touch}
                      y2={y}
                      stroke="var(--attn)"
                      strokeWidth={2}
                      vectorEffect="non-scaling-stroke"
                    />
                    <line
                      x1={x}
                      y1={y - 6 * touch}
                      x2={x}
                      y2={y + 6 * touch}
                      stroke="var(--attn)"
                      strokeWidth={2}
                      vectorEffect="non-scaling-stroke"
                    />
                  </>
                )}
                <circle
                  cx={x}
                  cy={y}
                  r={r}
                  fill="var(--attn)"
                  stroke="var(--ink)"
                  strokeWidth={3}
                  strokeDasharray={outside ? "3 2" : undefined}
                  vectorEffect="non-scaling-stroke"
                />
              </g>
            );
          })}
        </svg>
      </div>
      {/* under the picture, never over it: a button on the picture hid a corner's handle on a
          phone (fourth real-video test, G9) */}
      <div className="flex justify-end bg-[rgb(10_13_17/0.9)] px-3 pt-2">
        <button
          type="button"
          onClick={() => setZoom((z) => (z === 1 ? 2 : 1))}
          className="min-h-11 cursor-pointer border-2 border-ink bg-ground px-3 text-[15px] font-bold text-ink"
          data-testid="field-zoom"
        >
          {zoom === 1 ? t("zoomIn") : t("zoomOut")}
        </button>
      </div>
    </div>
  );
}
