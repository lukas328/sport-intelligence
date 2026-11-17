"use client";

import { useEffect, useRef, useState } from "react";
import { Bundle } from "@/components/anlauf/bundle";
import { cn } from "@/lib/cn";
import type { ThingView } from "@/lib/things";

/** how long one thing stays before the next (BEFUNDE-2 S3) */
const TURN_MS = 6000;
/** the part of the half court the card shows: goal to about 13 m, the rest fades out (S6) */
const HERO_BOX = "-0.6 -1.2 21.2 15.4";

/**
 * The hero's card: the demo match's three things, one at a time, as the app shows them after the
 * match. It turns by itself every six seconds, holds while the pointer is on it or the focus is in
 * it, and stops for good once the visitor picks one with the dots. With reduced motion it never
 * turns and nothing draws: the dots alone. All three cards sit in the same cell, so the card keeps
 * its height whichever is shown (no layout shift).
 */
export function HeroThings({ things, label, note }: { things: ThingView[]; label: string; note: string }) {
  const [at, setAt] = useState(0);
  // counts the turns, so the shown card draws its lines again each time it comes back
  const [round, setRound] = useState(0);
  const [held, setHeld] = useState(false);
  const [stopped, setStopped] = useState(false);
  // the drawing is CSS (no motion under reduced motion anyway); the turning waits for the check
  const [still, setStill] = useState(false);
  const [ready, setReady] = useState(false);
  const box = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const set = () => setStill(mq.matches);
    set();
    setReady(true);
    mq.addEventListener("change", set);
    return () => mq.removeEventListener("change", set);
  }, []);

  useEffect(() => {
    if (!ready || still || held || stopped || things.length < 2) return;
    const id = window.setTimeout(() => {
      setAt((a) => (a + 1) % things.length);
      setRound((r) => r + 1);
    }, TURN_MS);
    return () => window.clearTimeout(id);
  }, [at, ready, still, held, stopped, things.length]);

  const pick = (i: number) => {
    setStopped(true);
    if (i !== at) {
      setAt(i);
      setRound((r) => r + 1);
    }
  };

  return (
    <figure className="m-0">
      <div
        ref={box}
        role="group"
        aria-roledescription="carousel"
        aria-label={label}
        onPointerEnter={() => setHeld(true)}
        onPointerLeave={() => setHeld(false)}
        onFocus={() => setHeld(true)}
        onBlur={(e) => {
          if (!box.current?.contains(e.relatedTarget as Node | null)) setHeld(false);
        }}
        className="border-2 border-ink bg-paper text-ink shadow-[8px_8px_0_var(--ink)]"
      >
        <div className="grid">
          {things.map((t, i) => {
            const on = i === at;
            return (
              <div
                key={i}
                aria-hidden={!on}
                className={cn(
                  "min-w-0 px-5 pt-5 [grid-area:1/1] motion-safe:transition-[opacity,visibility] motion-safe:duration-500 md:px-7 md:pt-6",
                  on ? "visible opacity-100" : "invisible opacity-0",
                )}
              >
                <p className="font-mono text-base font-semibold text-ink-2">{t.index}</p>
                <p className="mt-1 flex flex-wrap items-baseline gap-x-3">
                  <b className="font-num text-[4.25rem] leading-[.9] text-club-text md:text-[5.5rem]">{t.numeral}</b>
                  <span className="font-slant text-[1.375rem] text-ink-2">{t.unit}</span>
                </p>
                <p className="mt-2 text-[1.3125rem] leading-tight font-bold md:text-[1.5rem]">{t.text}</p>
                <p className="mt-1 text-base text-ink-2 md:text-[1.0625rem]">{t.sub}</p>
                <div className="mt-4 [mask-image:linear-gradient(to_bottom,#000_72%,transparent)]">
                  <Bundle key={`${i}-${on ? round : "off"}`} goals={t.goals} width={440} play={on} clean box={HERO_BOX} label={t.label} />
                </div>
              </div>
            );
          })}
        </div>
        {things.length > 1 && (
          <div className="flex items-center gap-1 border-t border-rule px-3 py-1 md:px-5">
            {things.map((t, i) => (
              <button
                key={i}
                type="button"
                aria-pressed={i === at}
                aria-label={`${t.index}: ${t.text}`}
                onClick={() => pick(i)}
                className="group grid size-12 cursor-pointer place-items-center"
              >
                <i
                  aria-hidden
                  className={cn(
                    "block h-2.5 border-2 border-ink motion-safe:transition-[width,background-color] motion-safe:duration-300",
                    i === at ? "w-9 bg-ink" : "w-2.5 bg-transparent group-hover:bg-ink/30",
                  )}
                />
              </button>
            ))}
          </div>
        )}
      </div>
      <figcaption className="mt-4 text-base font-medium lg:text-right">{note}</figcaption>
    </figure>
  );
}
