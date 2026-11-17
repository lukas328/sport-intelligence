"use client";

import { useEffect, useState } from "react";
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

function Picture({ thing, play, from, clean, small }: { thing: ThingView; play: boolean; from: number; clean: boolean; small?: boolean }) {
  if (thing.kind === "times") return <Times minutes={thing.minutes} label={thing.label} />;
  return <Bundle goals={thing.goals} rest={thing.rest} width={small ? 150 : 340} play={play} from={from} clean={clean} label={thing.label} />;
}

/**
 * The three things: index, numeral, unit, sentence, sub-line and the picture. With `selectable`
 * each thing is a button; the chosen one lists its scenes underneath (the demo page; `?ding=2`
 * opens the second). From a tablet on the three stand side by side in exactly the same width,
 * and their words, pictures and links each share one row, so pictures and links line up.
 */
export function Things({
  things,
  legend,
  selectable = false,
  pickHint,
  scenesOf,
  timesOf,
  noVideo,
  scenesHref,
  clean = false,
}: {
  things: ThingView[];
  /** the line legend (the demo page); the start page leaves it out */
  legend?: { solid: string; thin: string };
  selectable?: boolean;
  pickHint?: string;
  scenesOf?: string;
  timesOf?: string;
  noVideo?: string;
  /** on the start page each thing leads to its scenes in the demo (`?ding=` and the list) */
  scenesHref?: string;
  /** the quiet drawing (start page): thin runs, clear dots, nothing else */
  clean?: boolean;
}) {
  const [open, setOpen] = useState(0);
  useEffect(() => {
    if (!selectable) return;
    const n = Number(new URLSearchParams(window.location.search).get("ding"));
    if (Number.isInteger(n) && n >= 1 && n <= things.length) setOpen(n - 1);
  }, [selectable, things.length]);
  const chosen = things[open]!;
  // the lines of the three things draw one after the other
  const starts = things.map((_, i) => things.slice(0, i).reduce((n, t) => n + t.goals.length, 0));
  return (
    <div>
      {selectable && pickHint && <p className="mt-4 text-[1.0625rem] text-ink-2">{pickHint}</p>}
      <ol className="mt-2 grid grid-cols-1 md:grid-cols-3 md:grid-rows-[auto_auto_auto] md:gap-x-12">
        {things.map((t, i) => {
          const body = (
            <>
              <span className="block min-w-0">
                <span className="font-mono text-base font-semibold text-ink-2">{t.index}</span>
                <span className="mt-2 flex flex-wrap items-baseline gap-x-3">
                  <b className="font-num text-[4.5rem] leading-[.85] text-club-text md:text-[6rem]">{t.numeral}</b>
                  <span className="font-slant text-[1.375rem] text-ink-2">{t.unit}</span>
                </span>
                <span className="mt-3 block text-[1.375rem] leading-tight font-bold">{t.text}</span>
                {t.sub && <span className="mt-1 block text-[1.0625rem] text-ink-2">{t.sub}</span>}
              </span>
              <span className="block w-full self-start md:mt-5">
                <span className="hidden md:block">
                  <Picture thing={t} play from={starts[i]!} clean={clean} />
                </span>
                <span className="md:hidden">
                  <Picture thing={t} play from={starts[i]!} clean={clean} small />
                </span>
              </span>
              <span className="col-span-2 block md:col-span-1">
                {t.note && <span className="mt-2 block text-base text-ink-2">{t.note}</span>}
                {t.scenesLabel &&
                  (scenesHref ? (
                    <DemoLink href={`${scenesHref}?ding=${i + 1}#szenen`} className="link mt-2 md:mt-3">
                      {t.scenesLabel}
                    </DemoLink>
                  ) : (
                    <span className="mt-4 inline-flex min-h-12 items-center bg-ink px-4 text-[1.0625rem] font-bold text-ground">{t.scenesLabel}</span>
                  ))}
              </span>
            </>
          );
          // phone: words left, the picture right, the link below; from a tablet on: one column,
          // the three parts in the rows the three things share
          const frame = cn(
            "grid h-full w-full grid-cols-[minmax(0,1fr)_8rem] items-start gap-x-4 border-b border-rule py-6 text-left min-[480px]:grid-cols-[minmax(0,1fr)_10rem]",
            "md:row-span-3 md:grid-cols-1 md:grid-rows-subgrid md:gap-y-0 md:border-b-0",
          );
          return (
            <li
              key={i}
              className={cn(
                "relative min-w-0 md:row-span-3 md:grid md:grid-rows-subgrid",
                i > 0 && "md:before:absolute md:before:inset-y-6 md:before:-left-6 md:before:w-px md:before:bg-rule md:before:content-['']",
              )}
            >
              {selectable ? (
                <button
                  type="button"
                  aria-pressed={open === i}
                  onClick={() => setOpen(i)}
                  className={cn(frame, "relative cursor-pointer hover:bg-ink/[.04] md:-mx-3 md:w-[calc(100%+1.5rem)] md:px-3", open === i && "shadow-[inset_0_6px_0_var(--ink)]")}
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
      {legend && (
        <p className="mt-2 flex flex-wrap gap-x-6 gap-y-2 text-base text-ink-2">
          <span className="inline-flex items-center gap-2">
            <i aria-hidden className="inline-block h-[3px] w-7 bg-ink" />
            {legend.solid}
          </span>
          <span>{legend.thin}</span>
        </p>
      )}
      {selectable && scenesOf && (
        <section id="szenen" aria-live="polite" className="mt-10 scroll-mt-4">
          <h3 className="section-head text-[1.375rem] md:text-[1.5rem]">{(chosen.kind === "times" && timesOf ? timesOf : scenesOf).replace("{i}", String(open + 1))}</h3>
          <ul className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
            {chosen.scenes.map((s, i) => (
              <li key={i} className="flex min-h-14 items-center gap-3 border-b border-rule py-2 text-[1.0625rem]">
                <span className="font-num w-16 text-[1.375rem]">{s.clock}</span>
                <span className="min-w-0">{s.text.replace(`${s.clock} · `, "")}</span>
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
