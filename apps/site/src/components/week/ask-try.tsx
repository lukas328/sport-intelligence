"use client";

import { useState } from "react";
import { cn } from "@/lib/cn";
import { fmt } from "@/lib/i18n";
import { sendWeek, useHydrated, type WeekDetail } from "./events";

export interface Prepared {
  question: string;
  answer: string;
  source: string;
  queries: string[];
  scenes: string;
  /** what «Die n Szenen abspielen» does on this page, and where it leads without JavaScript */
  go: WeekDetail;
  href: string;
}

/**
 * «Frag deine Spiele» to try (BEFUNDE-4 U32): three prepared questions as buttons, the answer in the
 * start page's card (components/ask-card.tsx): the question in the coach's words, the answer, its
 * source, the scenes as evidence and, folded, the queries. Nothing is asked live: the answers are
 * computed from the demo match (lib/week.ts, lib/story.ts), as the app's assistant would give them.
 */
export function AskTry({ items, bar, team, pick: pickLabel, how }: { items: Prepared[]; bar: string; team: string; pick: string; how: string }) {
  const [pick, setPick] = useState(0);
  const js = useHydrated();
  return (
    <div>
      <div role="group" aria-label={pickLabel} className="grid grid-cols-1 gap-2 sm:grid-cols-3">
        {items.map((x, i) => (
          <button
            key={x.question}
            type="button"
            aria-pressed={i === pick}
            onClick={() => setPick(i)}
            className={cn(
              "min-h-14 cursor-pointer border-2 px-4 py-2 text-left text-[1.0625rem] leading-snug font-semibold",
              i === pick ? "border-[var(--club-edge)] bg-club text-club-ink shadow-[4px_4px_0_var(--ink)]" : "border-ink/25 bg-paper hover:border-ink",
            )}
          >
            {x.question}
          </button>
        ))}
      </div>
      <div className="mt-5 border-2 border-ink bg-paper text-ink shadow-[8px_8px_0_var(--ink)]">
        <p className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 bg-ink px-4 py-2.5 font-mono text-[0.9375rem] font-semibold text-ground md:px-5">
          <span className="uppercase">{bar}</span>
          <span>{team}</span>
        </p>
        {(js ? [pick] : items.map((_, i) => i)).map((i) => {
          const q = items[i]!;
          return (
        <div key={i} aria-live="polite" className="ask-in grid gap-5 border-b-2 border-ink p-4 last:border-b-0 md:p-6">
          <p className="ml-auto max-w-[85%] bg-club px-4 py-3 text-[1.125rem] leading-snug font-semibold text-club-ink shadow-[inset_0_0_0_2px_var(--club-edge)]">{q.question}</p>
          <div>
            <p className="text-[1.125rem] leading-normal md:text-[1.1875rem]">{q.answer}</p>
            <p className="mt-3 border-t border-rule pt-3 text-base text-ink-2">{q.source}</p>
          </div>
          <a
            href={q.href}
            onClick={() => sendWeek(q.go)}
            className="btn btn-ink gap-2.5 justify-self-start"
          >
            <svg viewBox="0 0 20 20" aria-hidden className="size-4 shrink-0">
              <path d="M5 3l12 7-12 7z" fill="currentColor" />
            </svg>
            {q.scenes}
          </a>
          <details className="group border-t-2 border-ink pt-3">
            <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between gap-3 font-semibold [&::-webkit-details-marker]:hidden">
              {fmt(how, { count: q.queries.length })}
              <svg viewBox="0 0 20 20" aria-hidden className="size-5 shrink-0 transition-transform group-open:rotate-180">
                <path d="M4 7l6 6 6-6" fill="none" stroke="currentColor" strokeWidth={2.4} />
              </svg>
            </summary>
            <ol className="mt-2 grid list-decimal gap-1.5 pl-6 font-mono text-[0.9375rem] text-ink-2">
              {q.queries.map((x) => (
                <li key={x}>{x}</li>
              ))}
            </ol>
          </details>
        </div>
          );
        })}
      </div>
    </div>
  );
}
