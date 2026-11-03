"use client";

import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";

/**
 * The score as the loudest element. On first view it counts up briefly (about half a second),
 * then stands still; with reduced motion it is shown at once. Screen readers get the final score.
 */
export function MatchScore({ own, opp, className, animate = true }: { own: number; opp: number; className?: string; animate?: boolean }) {
  const [shown, setShown] = useState<[number, number]>(animate ? [0, 0] : [own, opp]);
  const done = useRef(!animate);
  useEffect(() => {
    if (done.current) return setShown([own, opp]);
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      done.current = true;
      return setShown([own, opp]);
    }
    const start = performance.now();
    const ms = 520;
    let raf = 0;
    const tick = (now: number) => {
      const k = Math.min(1, (now - start) / ms);
      const e = 1 - (1 - k) ** 3;
      setShown([Math.round(own * e), Math.round(opp * e)]);
      if (k < 1) raf = requestAnimationFrame(tick);
      else done.current = true;
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [own, opp]);
  return (
    <span className={cn("block font-score", className)}>
      <span aria-hidden>
        {shown[0]}:{shown[1]}
      </span>
      <span className="sr-only">
        {own}:{opp}
      </span>
    </span>
  );
}
