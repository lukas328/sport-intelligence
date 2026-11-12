"use client";

import { useState } from "react";
import { Bundle } from "@/components/anlauf/bundle";
import { DemoLink } from "@/components/kit";
import { cn } from "@/lib/cn";
import type { ThingView } from "@/lib/things";

/** Times on a 60-minute line: what the match report says (when, not where). */
function Times({ minutes, label }: { minutes: readonly number[]; label: string }) {
  const W = 300;
  const x = (m: number) => 10 + (Math.min(60, m) / 60) * (W - 20);
  return (
    <svg viewBox={`0 0 ${W} 120`} role="img" aria-label={label} className="block w-full">
      <line x1={10} x2={W - 10} y1={70} y2={70} stroke="var(--ink)" strokeWidth={1.5} />
      <line x1={x(30)} x2={x(30)} y1={40} y2={92} stroke="var(--ink)" strokeDasharray="2 4" />
      {[0, 30, 60].map((m) => (
        <text key={m} x={x(m)} y={112} textAnchor={m === 0 ? "start" : m === 60 ? "end" : "middle"} fill="var(--ink-2)" style={{ font: "600 16px var(--font-sans)" }}>
          {m}
        </text>
      ))}
      {minutes.map((m, i) => (
        <rect key={i} x={x(m) - 3} y={44} width={6} height={26} fill="var(--club-line)" stroke="var(--club-pipe)" strokeWidth={1} />
      ))}
    </svg>
  );
}

function Picture({ thing, play }: { thing: ThingView; play: boolean }) {
  if (thing.kind === "times") return <Times minutes={thing.minutes} label={thing.label} />;
  return <Bundle goals={thing.goals} rest={thing.rest} width={300} play={play} label={thing.label} />;
}

/**
 * The three things: index, numeral, unit, sentence, sub-line and the picture. With `selectable`
 * each thing is a button; the chosen one lists its scenes underneath.
 */
export function Things({
  things,
  legend,
  selectable = false,
  pickHint,
  scenesOf,
  timesOf,
  estimated,
  noVideo,
  scenesHref,
}: {
  things: ThingView[];
  legend: { solid: string; dashed: string; thin: string };
  selectable?: boolean;
  pickHint?: string;
  scenesOf?: string;
  timesOf?: string;
  estimated?: string;
  noVideo?: string;
  /** on the start page the scene count leads to the demo, where the scenes are listed */
  scenesHref?: string;
}) {
  const [open, setOpen] = useState(0);
  const chosen = things[open]!;
  return (
    <div>
      {selectable && pickHint && <p className="mt-4 text-[1.0625rem] text-ink-2">{pickHint}</p>}
      <ol className="mt-2 grid grid-cols-1 md:grid-cols-3">
        {things.map((t, i) => {
          const body = (
            <>
              <span className={cn("grid w-full items-start gap-x-4 md:block", t.kind === "bundle" && "grid-cols-[minmax(0,1fr)_8rem] min-[480px]:grid-cols-[minmax(0,1fr)_10rem]")}>
                <span className="block min-w-0">
                  <span className="font-mono text-base font-semibold text-ink-2">{t.index}</span>
                  <span className="mt-2 flex flex-wrap items-baseline gap-x-3">
                    <b className="font-num text-[4.5rem] leading-[.85] text-club-text md:text-[6rem]">{t.numeral}</b>
                    <span className="font-slant text-[1.375rem] text-ink-2">{t.unit}</span>
                  </span>
                  <span className="mt-3 block text-[1.375rem] leading-tight font-bold">{t.text}</span>
                  <span className="mt-1 block text-[1.0625rem] text-ink-2">{t.sub}</span>
                </span>
                <span className={cn("block md:mt-5 md:max-w-[22rem]", t.kind === "bundle" ? "mt-8" : "mt-5 max-w-[22rem]")}>
                  <Picture thing={t} play />
                </span>
              </span>
              {t.note && <span className="mt-2 block text-base text-ink-2">{t.note}</span>}
              {t.scenesLabel &&
                (scenesHref ? (
                  <DemoLink href={scenesHref} className="btn btn-ink mt-4 min-h-12 px-4 text-[1.0625rem]">
                    {t.scenesLabel}
                  </DemoLink>
                ) : (
                  <span className="mt-4 inline-flex min-h-12 items-center bg-ink px-4 text-[1.0625rem] font-bold text-ground">{t.scenesLabel}</span>
                ))}
            </>
          );
          const frame = cn(
            "flex h-full w-full flex-col items-start border-b border-rule py-6 text-left md:border-b-0 md:px-6",
            i > 0 ? "md:border-l md:border-l-rule" : "md:pl-0", i === things.length - 1 && "md:pr-0",
          );
          return (
            <li key={i} className="min-w-0">
              {selectable ? (
                <button
                  type="button"
                  aria-pressed={open === i}
                  onClick={() => setOpen(i)}
                  className={cn(frame, "relative cursor-pointer hover:bg-ink/[.04]", open === i && "shadow-[inset_0_6px_0_var(--ink)]")}
                >
                  {body}
                </button>
              ) : (
                <div className={frame}>{body}</div>
              )}
            </li>
          );
        })}
      </ol>
      <p className="mt-2 flex flex-wrap gap-x-6 gap-y-2 text-base text-ink-2">
        <span className="inline-flex items-center gap-2">
          <i aria-hidden className="inline-block h-[3px] w-7 bg-ink" />
          {legend.solid}
        </span>
        <span className="inline-flex items-center gap-2">
          <i aria-hidden className="inline-block h-[3px] w-7 bg-[repeating-linear-gradient(90deg,var(--ink)_0_6px,transparent_6px_10px)]" />
          {legend.dashed}
        </span>
        <span>{legend.thin}</span>
      </p>
      {selectable && scenesOf && (
        <section aria-live="polite" className="mt-10">
          <h3 className="font-slant section-head text-[1.5rem] md:text-[1.75rem]">{(chosen.kind === "times" && timesOf ? timesOf : scenesOf).replace("{i}", String(open + 1))}</h3>
          <ul className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
            {chosen.scenes.map((s, i) => (
              <li key={i} className="flex min-h-14 items-center gap-3 border-b border-rule py-2 text-[1.0625rem]">
                <span className="font-num w-16 text-[1.375rem]">{s.clock}</span>
                <span className="min-w-0">{s.text.replace(`${s.clock} · `, "")}</span>
                {s.estimated && estimated && <span className="ml-auto border-b-2 border-dashed border-ink-2 text-base text-ink-2">{estimated}</span>}
              </li>
            ))}
          </ul>
          {noVideo && chosen.kind === "bundle" && <p className="measure mt-4 text-[1.0625rem] text-ink-2">{noVideo}</p>}
          {chosen.note && chosen.kind === "times" && <p className="measure mt-4 text-[1.0625rem] text-ink-2">{chosen.note}</p>}
        </section>
      )}
    </div>
  );
}
