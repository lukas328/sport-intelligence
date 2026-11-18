"use client";

import { useEffect, useRef, useState } from "react";
import { ProductShot } from "@/components/product-shot";
import { cn } from "@/lib/cn";
import { productShot, type ShotName } from "@/lib/product-shots";

export interface TourItem {
  name: ShotName;
  alt: string;
  caption: string;
  text: string;
  /** the callout texts by id */
  labels: Record<string, string>;
  /** the word on the match video («Dein Spiel») */
  lettering?: string;
}

/**
 * «So sieht es in der App aus» (BEFUNDE-2 L13, BEFUNDE-3 U5) as one story: on a wide screen the
 * picture stays while the four steps pass by on the left (Szene antippen, Szenen suchen, Saison,
 * Link ins Team). The first step starts level with the picture, and each step becomes the one
 * shown when its first line reaches the picture's top, so text and picture always line up; a step
 * is about two thirds of the screen high, and the numbers 1 to 4 beside the picture say where you
 * are (and jump there). The labels sit half over the picture's edge so it keeps its air. On the
 * phone, on a narrower screen and with reduced motion: the calm version, step under step, each
 * with its picture large. All four pictures are in the page from the start in the same cell, so
 * nothing moves the layout when they change.
 */
export function AppTour({ items, label }: { items: TourItem[]; label: string }) {
  const [at, setAt] = useState(0);
  const steps = useRef<(HTMLLIElement | null)[]>([]);

  useEffect(() => {
    if (typeof IntersectionObserver === "undefined") return;
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (!e.isIntersecting) continue;
          const i = steps.current.indexOf(e.target as HTMLLIElement);
          if (i >= 0) setAt(i);
        }
      },
      // a thin line at the picture's top (the stage sticks at 12vh): the step crossing it is shown
      { rootMargin: "-12% 0px -87% 0px" },
    );
    for (const el of steps.current) if (el) io.observe(el);
    return () => io.disconnect();
  }, []);

  const go = (i: number) => steps.current[i]?.scrollIntoView({ behavior: "smooth", block: "start" });

  return (
    <div className="mt-8 grid grid-cols-1 motion-safe:xl:grid-cols-[minmax(0,17rem)_minmax(0,1fr)] motion-safe:xl:gap-x-8">
      <ol aria-label={label} className="grid gap-16 md:gap-20 motion-safe:xl:block">
        {items.map((s, i) => (
          <li
            key={s.name}
            ref={(el) => {
              steps.current[i] = el;
            }}
            className="motion-safe:xl:min-h-[65vh] motion-safe:xl:scroll-mt-[12vh] motion-safe:xl:last:min-h-[80vh]"
          >
            <div className="min-w-0">
              <div className={cn("max-w-[34rem] transition-opacity duration-300 motion-safe:xl:opacity-40", i === at && "motion-safe:xl:opacity-100")}>
                <p className="flex items-baseline gap-4">
                  <span aria-hidden className="font-num text-[3rem] leading-[.8] text-club-text">
                    {i + 1}
                  </span>
                  <span className="text-[1.5rem] leading-tight font-bold md:text-[1.75rem]">{s.caption}</span>
                </p>
                <p className="mt-3 text-[1.125rem]">{s.text}</p>
              </div>
              {/* the calm version: the picture right under its step, large */}
              <div className="mt-6 max-w-[52rem] motion-safe:xl:hidden">
                <ProductShot name={s.name} alt={s.alt} labels={s.labels} lettering={s.lettering} sizes="(min-width: 900px) 832px, calc(100vw - 2rem)" />
              </div>
            </div>
          </li>
        ))}
      </ol>
      {/* the stage on a wide screen: the picture of the step in view, the others faded out, each
          no taller than the screen leaves room for; beside it the four numbers, the one shown
          filled. The numbers stand in their own column, so the pictures' heights never move them */}
      <div className="hidden motion-safe:xl:block">
        <div className="sticky top-[12vh] grid grid-cols-[minmax(0,1fr)_auto] items-start gap-x-3">
          <div className="grid pl-[4.5rem] pr-[5rem]">
            {items.map((s, i) => {
              const { width, height } = productShot(s.name);
              return (
                <div key={s.name} className={cn("grid [grid-area:1/1] place-items-start transition-opacity duration-500", i === at ? "opacity-100" : "invisible opacity-0")}>
                  <div className="w-full" style={{ maxWidth: `min(100%, calc((80vh - 2.5rem) * ${(width / height).toFixed(3)}))` }}>
                    <ProductShot name={s.name} alt={s.alt} labels={s.labels} lettering={s.lettering} edge sizes="(min-width: 1280px) 720px, 50vw" />
                  </div>
                </div>
              );
            })}
          </div>
          <div role="group" aria-label={label} className="grid gap-2">
            {items.map((s, i) => (
              <button
                key={s.name}
                type="button"
                onClick={() => go(i)}
                aria-label={`${i + 1}: ${s.caption}`}
                aria-current={i === at ? "step" : undefined}
                className={cn(
                  "font-num grid size-11 cursor-pointer place-items-center border-2 border-ink text-[1.25rem] transition-colors",
                  i === at ? "bg-ink text-ground" : "bg-transparent text-ink hover:bg-ink/10",
                )}
              >
                {i + 1}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
