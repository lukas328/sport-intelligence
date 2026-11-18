"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Bundle, type GoalRun } from "@/components/anlauf/bundle";
import type { CameraText } from "@/components/anlauf/tactics-camera";
import { VIEWS } from "@/components/anlauf/geometry";
import { CameraLegend, DemoCamera, type CameraLegendText } from "@/components/demo-camera";
import { cn } from "@/lib/cn";
import { demoScene, sceneGap, type DemoGoal } from "@/lib/demo";
import { fmt } from "@/lib/i18n";
import { useWeek } from "./events";

export interface WhyThing {
  index: string;
  numeral: number;
  unit: string;
  text: string;
  sub: string;
  label: string;
  runs: GoalRun[];
  rest: GoalRun[];
  ids: string[];
  why: string;
  gap: string;
}

export interface WhyText {
  whyTitle: string;
  sceneList: string;
  sceneChip: string;
  sceneChipNoNumber: string;
  gapLegend: string;
  honest: string;
  askSet: string;
  /** «Tor {opp} {clock}» */
  goal: string;
  camera: Omit<CameraText, "caption">;
  legend: CameraLegendText;
}

/**
 * «Drei Dinge, jedes mit Warum» (BEFUNDE-4 U32): the three things as tabs; under the chosen one
 * its scenes as buttons, and the tactics camera plays the chosen scene from above, with the spot
 * to watch marked in yellow and named (the scorer when he gets the ball, the nearest player of the
 * other side). What it means the coach says himself (W32): the camera shows positions, not causes.
 * An answer of «Frag deine Spiele» can hand over its own scenes (components/week/events.ts).
 */
export function Why({ goals, things, own, opp, text }: { goals: DemoGoal[]; things: WhyThing[]; own: string; opp: string; text: WhyText }) {
  const [pick, setPick] = useState(0);
  const [scene, setScene] = useState(0);
  const [asked, setAsked] = useState<{ ids: string[]; title: string } | null>(null);
  const byId = useMemo(() => new Map(goals.map((g) => [g.id, g])), [goals]);

  useEffect(() => {
    const n = Number(new URLSearchParams(window.location.search).get("ding"));
    if (Number.isInteger(n) && n >= 1 && n <= things.length) setPick(n - 1);
  }, [things.length]);

  useWeek(
    useCallback(
      (d) => {
        if (!d.scenes) return;
        setScene(0);
        if (d.scenes.thing != null) {
          setAsked(null);
          setPick(d.scenes.thing);
        } else setAsked({ ids: d.scenes.ids, title: d.scenes.title });
      },
      [],
    ),
  );

  const thing = things[pick]!;
  const ids = asked ? asked.ids : thing.ids;
  const list = ids.map((id) => byId.get(id)).filter((g): g is DemoGoal => !!g);
  const goal = list[Math.min(scene, list.length - 1)] ?? list[0]!;
  const label = fmt(text.goal, { opp: goal.team === "opp" ? opp : own, clock: goal.clock });
  const cam = useMemo(() => demoScene(goal, label), [goal, label]);
  const gap = useMemo(() => sceneGap(cam), [cam]);
  const gapWord = asked ? null : thing.gap;
  const box = VIEWS.halfB.box;

  return (
    <div>
      <ol className="mt-6 grid grid-cols-1 gap-3 md:grid-cols-3 md:gap-5">
        {things.map((t, i) => {
          const on = !asked && i === pick;
          return (
            <li key={t.index} className="min-w-0">
              <button
                type="button"
                aria-pressed={on}
                onClick={() => {
                  setAsked(null);
                  setPick(i);
                  setScene(0);
                }}
                className={cn(
                  "grid h-full w-full cursor-pointer grid-cols-[minmax(0,1fr)_7.5rem] items-center gap-x-3 border-2 bg-paper p-3 text-left md:grid-cols-1 md:items-start md:p-4",
                  on ? "border-ink shadow-[6px_6px_0_var(--ink)]" : "border-ink/25 hover:border-ink",
                )}
              >
                <span className="block min-w-0">
                  <span className="font-mono text-base font-semibold text-ink-2">{t.index}</span>
                  <span className="mt-1 flex flex-wrap items-baseline gap-x-2">
                    <b className="font-num text-[3rem] leading-[.85] text-club-text md:text-[4rem]">{t.numeral}</b>
                    <span className="upright text-[1.125rem] text-ink-2">{t.unit}</span>
                  </span>
                  <span className="mt-2 block text-[1.1875rem] leading-tight font-bold">{t.text}</span>
                  <span className="mt-1 block text-base text-ink-2">{t.sub}</span>
                </span>
                <span className="block md:mt-3">
                  <Bundle goals={t.runs} rest={t.rest} width={150} clean label={t.label} />
                </span>
              </button>
            </li>
          );
        })}
      </ol>

      <div id="szenen" className="mt-8 grid scroll-mt-24 grid-cols-1 gap-x-10 gap-y-6 lg:grid-cols-[minmax(0,34rem)_minmax(0,1fr)]">
        <div className="relative min-w-0">
          <DemoCamera
            key={goal.id}
            scene={cam}
            view="halfB"
            desktopWidth={544}
            shotLabel={false}
            ballLine={false}
            text={{ ...text.camera, caption: label }}
          />
          {gap && gapWord && (
            <svg aria-hidden viewBox={box.join(" ")} className="pointer-events-none absolute top-0 left-0 block w-full">
              {gap.near && <line x1={gap.near[0]} y1={gap.near[1]} x2={gap.at[0]} y2={gap.at[1]} stroke="var(--attn)" strokeWidth={2} strokeDasharray="4 4" vectorEffect="non-scaling-stroke" />}
              <circle className="gap-pulse" cx={gap.at[0]} cy={gap.at[1]} r={1.7} fill="var(--attn)" fillOpacity={0.28} stroke="var(--attn)" strokeWidth={2.5} vectorEffect="non-scaling-stroke" />
              <GapWord at={gap.at} word={gapWord} />
            </svg>
          )}
        </div>
        <div className="min-w-0">
          <h3 className="text-[1.375rem] md:text-[1.5rem]">{asked ? `${text.askSet}: ${asked.title}` : `${text.whyTitle}: ${thing.text}`}</h3>
          {!asked && <p className="mt-2 text-[1.125rem]">{thing.why}</p>}
          {!asked && (
            <p className="mt-3 flex items-center gap-2 text-base text-ink-2">
              <i aria-hidden className="inline-block size-4 shrink-0 border-2 border-attn bg-attn/40" style={{ borderRadius: "50%" }} />
              {text.gapLegend}
            </p>
          )}
          <p className="mt-5 text-base font-semibold text-ink-2">{fmt(text.sceneList, { n: list.length })}</p>
          <ul className="mt-2 flex flex-wrap gap-2">
            {list.map((g, i) => {
              const on = g.id === goal.id;
              return (
                <li key={g.id}>
                  <button
                    type="button"
                    aria-pressed={on}
                    onClick={() => setScene(i)}
                    className={cn(
                      "inline-flex min-h-12 cursor-pointer items-center gap-2 border-2 px-3 text-[1.0625rem] font-semibold",
                      on ? "border-ink bg-ink text-ground" : "border-ink/25 bg-paper hover:border-ink",
                    )}
                  >
                    <svg viewBox="0 0 20 20" aria-hidden className="size-3.5 shrink-0">
                      <path d="M5 3l12 7-12 7z" fill="currentColor" />
                    </svg>
                    {g.number != null ? fmt(text.sceneChip, { clock: g.clock, number: g.number }) : fmt(text.sceneChipNoNumber, { clock: g.clock })}
                  </button>
                </li>
              );
            })}
          </ul>
          <div className="mt-6">
            <CameraLegend legend={text.legend} />
          </div>
          <p className="mt-6 border-l-4 border-ink bg-paper px-4 py-3 text-[1.0625rem]">{text.honest}</p>
        </div>
      </div>
    </div>
  );
}

/** The word next to the yellow ring, on the side with room (half court metres, goal at the top). */
function GapWord({ at, word }: { at: readonly [number, number]; word: string }) {
  const w = word.length * 0.52 + 0.9;
  const left = at[0] > 12;
  const x = left ? at[0] - 2.1 - w : at[0] + 2.1;
  const y = Math.max(-0.6, Math.min(14.6, at[1] - 0.65));
  return (
    <g>
      <rect x={x} y={y} width={w} height={1.3} fill="var(--attn)" />
      <text x={x + 0.45} y={y + 0.98} fill="#16171a" style={{ font: "800 0.95px var(--font-sans)" }}>
        {word}
      </text>
    </g>
  );
}
