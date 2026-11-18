"use client";

import { type CSSProperties, useState } from "react";
import { Court } from "@/components/story";
import { cn } from "@/lib/cn";
import type { SeasonMatch } from "@/lib/week";

export interface SeasonText {
  label: string;
  /** per match: «11 von 29» */
  of: string[];
  /** per match, for the button: «TSV Nachtwind: 11 von 29 Gegentoren über aussen rechts» */
  bars: string[];
  /** per match: what the half court shows */
  courts: string[];
  demo: string;
  example: string;
}

/**
 * The next match (BEFUNDE-4 U32): the season bar for «aussen rechts», one bar per match as in the
 * app's Saison («Was sich wiederholt»). The demo match first (11 of 29), then invented matches,
 * each marked «Beispiel». Tap a bar and the half court shows that match's goals conceded, the right
 * wing in ink. The bars rise once when seen (reduced motion: they stand).
 */
export function SeasonBars({ matches, text }: { matches: SeasonMatch[]; text: SeasonText }) {
  const [pick, setPick] = useState(1);
  const most = Math.max(...matches.map((m) => m.n));
  const m = matches[pick]!;
  return (
    <div className="grid grid-cols-1 items-end gap-10 lg:grid-cols-[minmax(0,1.25fr)_minmax(0,1fr)] lg:gap-14">
      <div role="group" aria-label={text.label} className="grid grid-cols-4 items-stretch gap-2 sm:gap-4">
        {matches.map((x, i) => {
          const on = i === pick;
          return (
            <button key={x.opp} type="button" aria-pressed={on} aria-label={text.bars[i]} onClick={() => setPick(i)} className="group flex min-w-0 cursor-pointer flex-col text-left">
              <span className="flex h-[15rem] flex-col justify-end md:h-[19rem]">
                <span aria-hidden className={cn("font-num text-[2.25rem] leading-none md:text-[3.25rem]", !on && "opacity-80")}>{x.n}</span>
                <span className="upright mb-2 text-base">{text.of[i]}</span>
                <span
                  aria-hidden
                  className={cn("bar-grow block w-full border-2 border-club-ink", on ? "bg-club-ink" : x.example ? "bg-club-ink/25 group-hover:bg-club-ink/45" : "bg-club-ink/55 group-hover:bg-club-ink/70")}
                  style={{ height: `${Math.max(6, (x.n / most) * 62)}%`, "--i": i } as CSSProperties}
                />
              </span>
              <span aria-hidden className={cn("block border-t-2 border-club-ink pt-2 text-[0.9375rem] leading-tight break-words md:text-base", on ? "font-bold" : "font-medium")}>
                {x.opp}
              </span>
              <span aria-hidden className={cn("mt-1 self-start px-1.5 text-[0.875rem] font-semibold", x.example ? "border border-dashed border-club-ink" : "bg-club-ink text-club")}>
                {x.example ? text.example : text.demo}
              </span>
            </button>
          );
        })}
      </div>
      <figure className="m-0 min-w-0">
        <div className="mx-auto max-w-[24rem] border-2 border-ink bg-paper p-2 text-ink shadow-[6px_6px_0_var(--ink)] lg:mr-0">
          <Court court={{ n: m.n, of: m.of, dots: m.dots }} label={text.courts[pick]!} />
        </div>
      </figure>
    </div>
  );
}
