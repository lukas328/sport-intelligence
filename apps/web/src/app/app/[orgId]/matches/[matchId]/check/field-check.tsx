"use client";

import { useTranslations } from "next-intl";
import { useEffect, useRef, useState, type KeyboardEvent, type PointerEvent } from "react";
import { courtPolylines, fitHomography, type Pt } from "@/lib/court-calibration";
import { CORNER_NAMES as NAMES, CORNERS } from "@/lib/field-corners";

export { CORNERS, cornersOf } from "@/lib/field-corners";

const pathOf = (pts: Pt[]) => pts.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)} ${y.toFixed(1)}`).join(" ");

/**
 * Prüfen, the court (UX test B13, B14): the hall image with the recognised court drawn on it and
 * four handles on the corners. Dragging a corner redraws the court at once; the keyboard moves a
 * focused handle with the arrow keys. The image may be smaller than the court: the area around
 * it stays reachable.
 */
export function FieldCheck({ src, alt, size, corners, onChange }: { src: string; alt: string; size: [number, number]; corners: Pt[]; onChange: (c: Pt[]) => void }) {
  const t = useTranslations("check");
  const tc = useTranslations("calibrate");
  const svg = useRef<SVGSVGElement>(null);
  const drag = useRef<number | null>(null);
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
    return [Math.min(w + pad, Math.max(-pad, p.x)), Math.min(h + pad, Math.max(-pad, p.y))];
  }
  const move = (i: number, p: Pt) => onChange(corners.map((c, k) => (k === i ? p : c)));
  function key(i: number, e: KeyboardEvent) {
    const step = (e.shiftKey ? 20 : 4) * (w / 1000);
    const d: Record<string, Pt> = { ArrowLeft: [-step, 0], ArrowRight: [step, 0], ArrowUp: [0, -step], ArrowDown: [0, step] };
    const v = d[e.key];
    if (!v) return;
    e.preventDefault();
    move(i, [corners[i]![0] + v[0], corners[i]![1] + v[1]]);
  }

  return (
    <div className="relative" data-testid="field-check">
      <svg
        ref={svg}
        viewBox={`${-pad} ${-pad} ${w + 2 * pad} ${h + 2 * pad}`}
        className="block w-full touch-none select-none"
        role="group"
        aria-label={t("fieldHandles")}
        onPointerMove={(e) => {
          if (drag.current == null) return;
          const p = at(e);
          if (p) move(drag.current, p);
        }}
        onPointerUp={() => ((drag.current = null), setActive(null))}
        onPointerLeave={() => ((drag.current = null), setActive(null))}
      >
        <image href={src} x={0} y={0} width={w} height={h} preserveAspectRatio="none">
          <title>{alt}</title>
        </image>
        {lines.map((l, i) => (
          <path key={i} d={pathOf(l)} fill="none" stroke="white" strokeOpacity={0.85} strokeWidth={r / 3} vectorEffect="non-scaling-stroke" />
        ))}
        <path d={`${pathOf(corners)} Z`} fill="rgb(246 197 0 / 0.12)" stroke="var(--attn)" strokeWidth={3} strokeDasharray="10 6" vectorEffect="non-scaling-stroke" />
        {corners.map(([x, y], i) => (
          <g
            key={NAMES[i]}
            role="slider"
            tabIndex={0}
            aria-label={tc(`landmarks.${NAMES[i]}`)}
            aria-valuetext={`${Math.round(x)}, ${Math.round(y)}`}
            aria-valuenow={Math.round(x)}
            className="cursor-grab outline-none focus-visible:[&>circle:last-child]:stroke-ink"
            onPointerDown={(e) => {
              drag.current = i;
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
                <line x1={x - 6 * touch} y1={y} x2={x + 6 * touch} y2={y} stroke="var(--attn)" strokeWidth={2} vectorEffect="non-scaling-stroke" />
                <line x1={x} y1={y - 6 * touch} x2={x} y2={y + 6 * touch} stroke="var(--attn)" strokeWidth={2} vectorEffect="non-scaling-stroke" />
              </>
            )}
            <circle cx={x} cy={y} r={r} fill="var(--attn)" stroke="var(--ink)" strokeWidth={3} vectorEffect="non-scaling-stroke" />
          </g>
        ))}
      </svg>
    </div>
  );
}
