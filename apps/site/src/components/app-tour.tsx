"use client";

import { type CSSProperties, useCallback, useEffect, useRef, useState } from "react";
import { HalfCourtLines } from "@/components/anlauf/court";
import { ProductShot } from "@/components/product-shot";
import { cn } from "@/lib/cn";
import { productShot, type ShotName } from "@/lib/product-shots";
import { DEFENCE, PLAY_BOX, PLAYERS, ballPath, passPath, percent, progressFor, stepAt } from "@/lib/tour-play";

export interface TourItem {
  name: ShotName;
  alt: string;
  caption: string;
  text: string;
  /** the callout texts by id */
  labels: Record<string, string>;
  /** the word on the match video («Dein Spiel») */
  lettering?: string;
  /** the player's name in the play: the app's place the picture shows (Spiele, Szenen, Saison, Team) */
  player: string;
}

/** each step gets this much scrolling on the stage */
const STEP_VH = 75;

/**
 * «So sieht es in der App aus» (BEFUNDE-2 L13, BEFUNDE-3 U5, BEFUNDE-4 U31) as one story. On a wide
 * and tall enough screen a stage fills the screen and stays while you scroll through it: on the
 * left a play on the half court (four players, the ball goes from one to the next) with the text of
 * the step under it, on the right the picture, large. Text, picture and play follow one number,
 * worked out from how far the stage has travelled through its track, so the text always belongs to
 * the picture. A tap on a player jumps to his step. With reduced motion nothing flies or fades: the
 * ball and the step simply change. On the phone and on smaller screens the calm version: step under
 * step, each with its picture large.
 */
export function AppTour({ items, label, hint }: { items: TourItem[]; label: string; hint: string }) {
  const [at, setAt] = useState(0);
  const track = useRef<HTMLDivElement>(null);
  const stage = useRef<HTMLDivElement>(null);
  const n = items.length;

  useEffect(() => {
    let raf = 0;
    const measure = () => {
      raf = 0;
      const t = track.current;
      const s = stage.current;
      if (!t || !s || !s.offsetParent) return;
      const run = t.offsetHeight - s.offsetHeight;
      const moved = s.getBoundingClientRect().top - t.getBoundingClientRect().top;
      setAt(stepAt(run > 0 ? moved / run : 0, n));
    };
    const onScroll = () => {
      if (!raf) raf = requestAnimationFrame(measure);
    };
    measure();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => {
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
      cancelAnimationFrame(raf);
    };
  }, [n]);

  const go = useCallback(
    (i: number) => {
      const t = track.current;
      const s = stage.current;
      if (!t || !s) return;
      const top = parseFloat(getComputedStyle(s).top) || 0;
      const run = t.offsetHeight - s.offsetHeight;
      const y = window.scrollY + t.getBoundingClientRect().top - top + progressFor(i, n) * run;
      const calm = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      window.scrollTo({ top: Math.round(y) + 1, behavior: calm ? "auto" : "smooth" });
    },
    [n],
  );

  return (
    <div className="mt-8">
      {/* the calm version: step under step, the picture right under its text */}
      <ol aria-label={label} className="grid gap-16 md:gap-20 stage:hidden">
        {items.map((s, i) => (
          <li key={s.name} className="min-w-0 print:break-inside-avoid">
            <div className="max-w-[34rem]">
              <p className="flex items-baseline gap-4">
                <span aria-hidden className="font-num text-[3rem] leading-[.8] text-club-text">
                  {i + 1}
                </span>
                <span className="text-[1.5rem] leading-tight font-bold md:text-[1.75rem]">{s.caption}</span>
              </p>
              <p className="mt-3 text-[1.125rem]">{s.text}</p>
            </div>
            <div className="mt-6 max-w-[52rem]">
              <ProductShot name={s.name} alt={s.alt} labels={s.labels} lettering={s.lettering} sizes="(min-width: 900px) 832px, calc(100vw - 2rem)" />
            </div>
          </li>
        ))}
      </ol>

      {/* the stage: wider than the page's column (94 per cent of the screen, up to 120 rem, never narrower than the column), a track
          with one stretch of scrolling per step, and in it the part that stays */}
      <div
        ref={track}
        data-tour-track
        className="relative hidden stage:block stage:ml-[calc((100%-max(100%,min(100vw-4rem,94vw,120rem)))/2)] stage:w-[max(100%,min(100vw-4rem,94vw,120rem))]"
        style={{ height: `calc(90vh + ${n * STEP_VH}vh)` }}
      >
        <div
          ref={stage}
          className="sticky top-[5vh] grid h-[90vh] grid-cols-[clamp(21rem,25vw,34rem)_minmax(0,1fr)] items-center gap-x-6"
        >
          <div className="grid content-center gap-8">
            <Play items={items} at={at} go={go} label={label} hint={hint} />
            <ol aria-label={label} className="grid">
              {items.map((s, i) => (
                <li
                  key={s.name}
                  aria-current={i === at ? "step" : undefined}
                  className={cn(
                    "[grid-area:1/1] transition-[opacity,translate] ease-out motion-reduce:transition-none",
                    i === at ? "opacity-100 delay-150 duration-500" : "pointer-events-none translate-y-3 opacity-0 duration-200 motion-reduce:translate-y-0",
                  )}
                >
                  <p className="flex items-baseline gap-4">
                    <span aria-hidden className="font-num text-[3.5rem] leading-[.8] text-club-text">
                      {i + 1}
                    </span>
                    <span className="text-[1.625rem] leading-tight font-bold min-[100rem]:text-[1.875rem]">{s.caption}</span>
                  </p>
                  <p className="mt-4 text-[1.1875rem]">{s.text}</p>
                </li>
              ))}
            </ol>
          </div>
          {/* the pictures in one cell, the one of the step shown; each no taller than the stage
              leaves room for, with air on both sides for the labels over its edges */}
          <div className="grid h-full items-center px-[5rem]">
            {items.map((s, i) => {
              const { width, height } = productShot(s.name);
              return (
                <div
                  key={s.name}
                  className={cn(
                    "grid [grid-area:1/1] justify-items-center transition-[opacity,scale] ease-out motion-reduce:transition-none",
                    i === at ? "scale-100 opacity-100 delay-100 duration-500" : "pointer-events-none scale-[.985] opacity-0 duration-300 motion-reduce:scale-100",
                  )}
                >
                  <div className="w-full" style={{ maxWidth: `min(100%, calc((90vh - 4rem) * ${(width / height).toFixed(3)}))` }}>
                    <ProductShot name={s.name} alt={s.alt} labels={s.labels} lettering={s.lettering} edge sizes="(min-width: 1280px) 1200px, 60vw" />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * The play: the half court in the tactics camera's colours (ink, cream lines), the four players as
 * buttons (number and the app's place), the passes played so far as lines, the next ones dashed,
 * and the ball (yellow) with the player of the step shown. When the step changes the ball flies
 * along the passing lines and the player who gets it lights up.
 */
function Play({ items, at, go, label, hint }: { items: TourItem[]; at: number; go: (i: number) => void; label: string; hint: string }) {
  const ball = useRef<HTMLSpanElement>(null);
  const last = useRef(at);
  const flight = useRef<Animation | null>(null);

  useEffect(() => {
    const from = last.current;
    last.current = at;
    const el = ball.current;
    if (from === at || !el || typeof el.animate !== "function") return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const frames: Keyframe[] = ballPath(from, at).map(({ at: p, offset }) => ({ ...percent(p), offset }));
    // still in the air (a fast scroll): go on from where the ball is, not from the last player
    const prev = flight.current;
    if (prev && prev.playState === "running") {
      const { left, top } = getComputedStyle(el);
      prev.cancel();
      frames[0] = { left, top, offset: 0 };
    }
    const legs = Math.abs(at - from);
    flight.current = el.animate(frames, { duration: Math.min(560 + (legs - 1) * 300, 1300), easing: "cubic-bezier(.45,.05,.3,1)" });
  }, [at]);

  useEffect(() => () => flight.current?.cancel(), []);

  const [x0, y0, w, h] = PLAY_BOX;
  return (
    <div className="on-court border-2 border-ink bg-court shadow-[6px_6px_0_var(--ink)]">
      <div role="group" aria-label={label} className="relative [container-type:inline-size]" style={{ aspectRatio: `${w} / ${h}` }}>
        <svg aria-hidden viewBox={`${x0} ${y0} ${w} ${h}`} className="absolute inset-0 block h-full w-full">
          <HalfCourtLines ink="var(--court-text)" opacity={0.42} />
          {DEFENCE.map(([x, y], i) => (
            <circle key={i} cx={x} cy={y} r={0.42} fill="none" stroke="var(--court-text)" strokeWidth={0.13} opacity={0.4} />
          ))}
          {PLAYERS.slice(0, -1).map((_, i) => {
            const done = i < at;
            return (
              <g key={i} fill="none" strokeLinecap="round">
                <path d={passPath(i)} stroke="var(--court-text)" strokeWidth={0.12} strokeDasharray="0.45 0.4" opacity={0.45} />
                <path
                  d={passPath(i)}
                  pathLength={1}
                  stroke="var(--attn)"
                  strokeWidth={0.2}
                  strokeDasharray="1"
                  strokeLinecap="butt"
                  className="transition-[stroke-dashoffset] duration-500 ease-out motion-reduce:transition-none"
                  style={{ strokeDashoffset: done ? 0 : 1 }}
                />
              </g>
            );
          })}
        </svg>

        {items.map((s, i) => {
          const on = i === at;
          return (
            <button
              key={s.name}
              type="button"
              onClick={() => go(i)}
              aria-label={`${i + 1} ${s.player}: ${s.caption}`}
              aria-current={on ? "step" : undefined}
              className="group absolute z-[1] flex -translate-x-1/2 -translate-y-6 cursor-pointer flex-col items-center px-1 pb-1 outline-offset-0"
              style={percent(PLAYERS[i]!)}
            >
              <span className="relative grid size-12 place-items-center">
                {/* the next pass: a soft yellow pulse says «tap me» (still with reduced motion) */}
                {i === at + 1 && (
                  <span
                    aria-hidden
                    style={{ borderRadius: "50%" }}
                    className="pointer-events-none absolute size-[2.125rem] border-2 border-attn opacity-70 motion-safe:animate-ping"
                  />
                )}
                <span
                  aria-hidden
                  key={on ? "on" : "off"}
                  style={{ borderRadius: "50%" } as CSSProperties}
                  className={cn(
                    "upright grid size-[2.125rem] place-items-center border-2 text-[1.0625rem] leading-none transition-[background-color,scale] duration-300 motion-reduce:transition-none",
                    on
                      ? "scale-110 border-court-text bg-club text-club-ink motion-safe:animate-[catch_1.1s_ease-out_both]"
                      : "border-attn bg-court text-court-text group-hover:scale-110 group-hover:bg-attn group-hover:text-ink group-focus-visible:bg-attn group-focus-visible:text-ink",
                  )}
                >
                  {i + 1}
                </span>
              </span>
              <span
                className={cn(
                  "upright -mt-1 bg-court/85 px-1 text-[1rem] leading-tight whitespace-nowrap transition-colors duration-300 motion-reduce:transition-none",
                  on
                    ? "text-attn motion-safe:delay-500"
                    : "text-court-text underline decoration-attn/70 decoration-2 underline-offset-4 group-hover:text-attn",
                )}
              >
                {s.player}
              </span>
            </button>
          );
        })}

        {/* the ball, with the player of the step shown (a little above and right of him) */}
        <span aria-hidden className="pointer-events-none absolute z-[2] block size-0" style={percent(PLAYERS[at]!)} ref={ball}>
          <span
            style={{ borderRadius: "50%" }}
            className="absolute top-[-1.55rem] left-[0.55rem] block size-[1.0625rem] border-2 border-ink bg-attn shadow-[0_0_0_2px_var(--court)]"
          />
        </span>
      </div>
      <p className="flex items-center gap-2.5 border-t-2 border-court-bar bg-court-bar px-4 py-2 text-[1rem] text-court-text">
        {/* a tapping hand: the numbers are buttons */}
        <svg aria-hidden viewBox="0 0 24 24" className="size-5 shrink-0 text-attn" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
          <path d="M9 11V5.5a1.5 1.5 0 0 1 3 0V11" />
          <path d="M12 10.5V9a1.5 1.5 0 0 1 3 0v2" />
          <path d="M15 10.5a1.5 1.5 0 0 1 3 0V15a6 6 0 0 1-6 6h-.5a6 6 0 0 1-4.6-2.2L4.6 16a1.5 1.5 0 0 1 2.3-1.9L9 16" />
          <path d="M5 4.5 3.5 3M9 2V1M13 4.5 14.5 3" />
        </svg>
        <span>{hint}</span>
      </p>
    </div>
  );
}
