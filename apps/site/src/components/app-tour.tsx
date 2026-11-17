"use client";

import { useEffect, useRef, useState } from "react";
import { ProductShot } from "@/components/product-shot";
import { cn } from "@/lib/cn";
import type { ShotName } from "@/lib/product-shots";

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
 * «So sieht es in der App aus» (BEFUNDE-2 L13) as one story: on a wide screen the picture stays
 * while the four steps pass by on the left (Szene antippen, Szenen suchen, Saison, Link ins Team);
 * the one in view shows its picture, the labels sit half over the picture's edge so it keeps its
 * air. On the phone, on a narrower screen and with reduced motion: the calm version, step under
 * step, each with its picture large. All four pictures are in the page from the start in the same
 * cell, so nothing moves the layout when they change.
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
      // the step crossing the middle of the screen is the one shown
      { rootMargin: "-45% 0px -45% 0px" },
    );
    for (const el of steps.current) if (el) io.observe(el);
    return () => io.disconnect();
  }, []);

  return (
    <div className="mt-8 grid grid-cols-1 motion-safe:xl:grid-cols-[minmax(0,21rem)_minmax(0,1fr)] motion-safe:xl:gap-x-10">
      <ol aria-label={label} className="grid gap-16 md:gap-20 motion-safe:xl:gap-0">
        {items.map((s, i) => (
          <li
            key={s.name}
            ref={(el) => {
              steps.current[i] = el;
            }}
            className="motion-safe:xl:flex motion-safe:xl:min-h-[78vh] motion-safe:xl:items-center"
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
      {/* the stage on a wide screen: the picture of the step in view, the others faded out */}
      <div className="hidden motion-safe:xl:block">
        <div className="sticky top-[max(1.5rem,calc(50vh-17rem))] grid px-[5.5rem]">
          {items.map((s, i) => (
            <div key={s.name} className={cn("grid [grid-area:1/1] place-items-center transition-opacity duration-500", i === at ? "opacity-100" : "invisible opacity-0")}>
              <ProductShot name={s.name} alt={s.alt} labels={s.labels} lettering={s.lettering} edge sizes="(min-width: 1280px) 600px, 50vw" className="w-full" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
