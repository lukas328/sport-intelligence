"use client";

import { type CSSProperties, useState } from "react";
import { CourtLines, HalfCourtLines } from "@/components/anlauf/court";
import { HALF_BOX, type Pt } from "@/components/anlauf/geometry";
import { cn } from "@/lib/cn";
import type { Drill, DrillLang } from "@/lib/drills";
import { useHydrated } from "./events";

const NS = { vectorEffect: "non-scaling-stroke" } as const;

export interface TipText {
  tabs: string[];
  sources: string[];
  meta: string[];
  focus: string[];
  howTo: string;
  parts: { setup: string; procedure: string; coaching: string; variants: string };
  sketchLabels: string[];
  plan: string;
}

/**
 * The drill's sketch from the library (the app's DrillSketchView, drawn with the website's court):
 * players as dots with their labels, passes as lines, runs dashed, the ball white; a half court
 * with the goal at the top, or the first part of the whole court for drills over the full length.
 * The arrows come in one after the other when the card is seen (reduced motion: all at once).
 */
export function DrillSketch({ drill, label }: { drill: Drill; label: string }) {
  const s = drill.sketch;
  const half = s.court === "half";
  // half court: goal at x = 40 to the top; whole court: our goal on the left, the first 26 m
  const at = (x: number, y: number): Pt => (half ? [20 - y, 40 - x] : [x, y]);
  const box = half ? HALF_BOX.join(" ") : "-1.2 -1.2 27.6 22.4";
  const r = half ? 0.78 : 0.95;
  return (
    <svg viewBox={box} role="img" aria-label={label} className="play block w-full bg-paper">
      {half ? <HalfCourtLines opacity={0.45} /> : <CourtLines line="rgb(22 23 26 / .4)" area="rgb(22 23 26 / .05)" width={1.2} />}
      <defs>
        <marker id={`head-${drill.id}`} viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
          <path d="M0 0L10 5L0 10z" fill="var(--ink)" />
        </marker>
      </defs>
      {s.arrows.map((a, i) => {
        const pts = a.points.map(([x, y]) => at(x, y));
        const d = pts.map((p, k) => `${k ? "L" : "M"}${p[0].toFixed(2)} ${p[1].toFixed(2)}`).join("");
        return (
          <path
            key={i}
            className="ln-e"
            style={{ "--i": i + 1 } as CSSProperties}
            d={d}
            fill="none"
            stroke="var(--ink)"
            strokeWidth={a.kind === "pass" ? 2.2 : 2}
            strokeDasharray={a.kind === "run" ? "6 4" : a.kind === "dribble" ? "2 3" : undefined}
            markerEnd={`url(#head-${drill.id})`}
            {...NS}
          />
        );
      })}
      {s.tokens.map((k) => {
        const [x, y] = at(k.x, k.y);
        const own = k.side === "own";
        return (
          <g key={k.id}>
            <circle cx={x} cy={y} r={r} fill={own ? "var(--club)" : "var(--paper)"} stroke={own ? "var(--club-edge)" : "var(--ink)"} strokeWidth={1.6} {...NS} />
            <text x={x} y={y + r * 0.36} textAnchor="middle" fill={own ? "var(--club-ink)" : "var(--ink)"} style={{ font: `800 ${(k.label.length > 1 ? r * 0.85 : r * 1.05).toFixed(2)}px var(--font-sans)` }}>
              {k.label}
            </text>
          </g>
        );
      })}
      {s.ball && (() => {
        const [x, y] = at(s.ball.x, s.ball.y);
        return <circle cx={x + r * 0.95} cy={y - r * 0.95} r={r * 0.5} fill="#fff" stroke="var(--ink)" strokeWidth={1.3} {...NS} />;
      })()}
    </svg>
  );
}

/**
 * «Daraus wird das Training» (BEFUNDE-4 U32): the training card as the app shows a tip (topic,
 * drill card with sketch, facts and «So geht's»), with two tabs. For the right wing the coach picks
 * the drill from the library himself; for the fast breaks it is the app's own training tip
 * (services/training_tips.py). Each tab says which of the two it is.
 */
export function TrainingTip({ drills, lang, text }: { drills: Drill[]; lang: DrillLang; text: TipText }) {
  const [pick, setPick] = useState(0);
  const js = useHydrated();
  return (
    <div className="border-2 border-ink bg-paper shadow-[8px_8px_0_var(--ink)]">
      <div role="group" className="grid grid-cols-2 border-b-2 border-ink">
        {text.tabs.map((tab, i) => (
          <button
            key={tab}
            type="button"
            aria-pressed={i === pick}
            onClick={() => setPick(i)}
            className={cn("min-h-14 cursor-pointer px-3 py-2 text-left text-[1.0625rem] leading-tight font-bold md:px-5", i === pick ? "bg-ink text-ground" : "hover:bg-ink/5", i === 1 && "border-l-2 border-ink")}
          >
            {tab}
          </button>
        ))}
      </div>
      {(js ? [pick] : drills.map((_, i) => i)).map((i) => {
        const d = drills[i]!;
        return (
      <div key={d.id} className="grid grid-cols-1 gap-5 border-b-2 border-ink p-4 last-of-type:border-b-0 sm:grid-cols-[minmax(0,15rem)_minmax(0,1fr)] md:p-6">
        <div className="border-2 border-ink">
          <DrillSketch drill={d} label={text.sketchLabels[i]!} />
        </div>
        <div className="min-w-0">
          <p className="inline-flex items-center gap-2 bg-[color-mix(in_srgb,var(--attn)_45%,var(--paper))] px-2 py-0.5 text-base font-semibold">{text.focus[i]}</p>
          <h4 className="mt-2 text-[1.5rem] leading-tight font-bold">{d.name[lang]}</h4>
          <p className="mt-1 text-base text-ink-2">{text.meta[i]}</p>
          <p className="mt-3 text-[1.0625rem]">{d.setup[lang]}</p>
          <details className="group mt-3 border-t-2 border-ink pt-2">
            <summary className="flex min-h-12 cursor-pointer list-none items-center justify-between gap-3 font-semibold">
              {text.howTo}
              <svg viewBox="0 0 20 20" aria-hidden className="size-5 shrink-0 transition-transform group-open:rotate-180">
                <path d="M4 7l6 6 6-6" fill="none" stroke="currentColor" strokeWidth={2.4} />
              </svg>
            </summary>
            <dl className="mt-1 grid gap-2 text-[1.0625rem]">
              {(["procedure", "coaching", "variants"] as const).map((k) => (
                <div key={k}>
                  <dt className="font-semibold">{text.parts[k]}</dt>
                  <dd className="m-0">{d[k][lang]}</dd>
                </div>
              ))}
            </dl>
          </details>
        </div>
        <p className="border-t border-rule pt-3 text-base text-ink-2 sm:col-span-2">{text.sources[i]}</p>
      </div>
        );
      })}
      <p className="border-t-2 border-ink bg-ink px-4 py-3 text-[1.0625rem] font-semibold text-ground md:px-6">{text.plan}</p>
    </div>
  );
}
