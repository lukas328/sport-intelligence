"use client";

import { useEffect, useRef, useState } from "react";

/**
 * A number that counts up from 0 once it comes into view (the before and after, BEFUNDE-2 S12).
 * The page is rendered with the final number, so without script, with reduced motion and for
 * screen readers it is simply there; only a number still below the screen is set back to 0 first.
 * `minDigits` keeps the width while counting, so nothing next to it moves.
 */
export function CountUp({ value, ms = 900, className, minDigits }: { value: number; ms?: number; className?: string; minDigits?: number }) {
  const [shown, setShown] = useState(value);
  const el = useRef<HTMLSpanElement>(null);
  useEffect(() => {
    const node = el.current;
    if (!node || typeof IntersectionObserver === "undefined") return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    if (node.getBoundingClientRect().top < window.innerHeight * 0.85) return;
    setShown(0);
    let raf = 0;
    const io = new IntersectionObserver(
      ([e]) => {
        if (!e?.isIntersecting) return;
        io.disconnect();
        const t0 = performance.now();
        const tick = (t: number) => {
          const p = Math.min(1, (t - t0) / ms);
          // ease out: fast at first, settling on the number
          setShown(Math.round(value * (1 - (1 - p) ** 3)));
          if (p < 1) raf = requestAnimationFrame(tick);
        };
        raf = requestAnimationFrame(tick);
      },
      { threshold: 0.6 },
    );
    io.observe(node);
    return () => {
      io.disconnect();
      cancelAnimationFrame(raf);
    };
  }, [value, ms]);
  return (
    <span ref={el} className={className} style={minDigits ? { display: "inline-block", minWidth: `${minDigits}ch` } : undefined}>
      {/* the final number for screen readers, the counting one only for the eye */}
      <span className="sr-only">{value}</span>
      <span aria-hidden>{shown}</span>
    </span>
  );
}
