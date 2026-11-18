"use client";

import { useEffect, useRef, useState } from "react";
import { BallIcon } from "@/components/ball-icon";
import { ballWay } from "@/lib/ball-way";

/** the length along `p` where it is level with `y` (the way runs down, so y grows with the length) */
function lengthAtY(p: SVGPathElement, y: number, total: number): number {
  let lo = 0;
  let hi = total;
  for (let i = 0; i < 22; i++) {
    const mid = (lo + hi) / 2;
    if (p.getPointAtLength(mid).y < y) lo = mid;
    else hi = mid;
  }
  return (lo + hi) / 2;
}

/**
 * One ball path through the four steps of «So funktioniert es» (BEFUNDE-4 U47), the handball theme
 * of the app tour: a dashed way from the ball of step 1 (with the attack the camera films) through
 * the ball of each step to the ball in the goal of step 4. While you scroll, the ball runs along it,
 * always level with the middle of the screen, and the way behind it turns yellow.
 *
 * Calm by design: on a wide screen only (on the phone the steps stand under each other and the
 * way would run through the text), drawn once the page is measured. With reduced motion the way
 * stands still and each step keeps its own ball; without JavaScript there is no way at all and
 * every step shows its ball (components/step-art.tsx, `data-ball`). Place it inside the
 * positioned element that holds the steps.
 */
export function BallRun() {
  const box = useRef<HTMLDivElement>(null);
  const way = useRef<SVGPathElement>(null);
  const trail = useRef<SVGPathElement>(null);
  const ball = useRef<HTMLSpanElement>(null);
  const [mode, setMode] = useState<"off" | "still" | "run">("off");

  useEffect(() => {
    const wide = window.matchMedia("(min-width: 64rem)");
    const calm = window.matchMedia("(prefers-reduced-motion: reduce)");
    const pick = () => setMode(wide.matches ? (calm.matches ? "still" : "run") : "off");
    pick();
    wide.addEventListener("change", pick);
    calm.addEventListener("change", pick);
    return () => {
      wide.removeEventListener("change", pick);
      calm.removeEventListener("change", pick);
    };
  }, []);

  useEffect(() => {
    const host = box.current?.parentElement;
    if (mode === "off" || !host) return;
    // while the ball runs, it stands for the balls of the steps (globals.css, «[data-run]»)
    if (mode === "run") host.dataset.run = "";
    let raf = 0;
    let key = "";
    let total = 0;
    let shown = -1;

    const tick = () => {
      raf = 0;
      const p = way.current;
      if (!p) return;
      // the balls of the steps in the host's coordinates (cheap, and follows any layout change)
      const r = host.getBoundingClientRect();
      const pts = Array.from(host.querySelectorAll<HTMLElement>("[data-ball]")).map((el) => {
        const b = el.getBoundingClientRect();
        return [b.left + b.width / 2 - r.left, b.top + b.height / 2 - r.top] as const;
      });
      if (pts.length < 2) return;
      const k = pts.map((q) => q.map(Math.round).join(",")).join(" ");
      if (k !== key) {
        key = k;
        const d = ballWay(pts);
        p.setAttribute("d", d);
        trail.current?.setAttribute("d", d);
        total = p.getTotalLength();
        shown = -1;
      }
      if (mode !== "run") return;
      // the ball stays level with the middle of the screen, from the first step's ball to the last
      const goal = lengthAtY(p, window.innerHeight / 2 - r.top, total);
      const next = shown < 0 ? goal : shown + (goal - shown) * 0.18;
      shown = Math.abs(goal - next) < 0.5 ? goal : next;
      const at = p.getPointAtLength(shown);
      if (ball.current) ball.current.style.translate = `${at.x.toFixed(1)}px ${at.y.toFixed(1)}px`;
      trail.current?.setAttribute("stroke-dasharray", `${shown.toFixed(1)} ${(total + 10).toFixed(1)}`);
      if (shown !== goal) raf = requestAnimationFrame(tick);
    };
    const kick = () => {
      if (!raf) raf = requestAnimationFrame(tick);
    };
    kick();
    // web fonts and the glide-in of the blocks move the balls a little after the first frame
    const late = window.setTimeout(kick, 900);
    const ro = new ResizeObserver(kick);
    ro.observe(host);
    window.addEventListener("scroll", kick, { passive: true });
    window.addEventListener("resize", kick);
    return () => {
      cancelAnimationFrame(raf);
      window.clearTimeout(late);
      ro.disconnect();
      window.removeEventListener("scroll", kick);
      window.removeEventListener("resize", kick);
      delete host.dataset.run;
    };
  }, [mode]);

  if (mode === "off") return <div ref={box} hidden />;
  return (
    <>
      <div ref={box} aria-hidden className="pointer-events-none absolute inset-0 z-0">
        <svg className="absolute inset-0 block h-full w-full overflow-visible">
          {mode === "run" && <path ref={trail} fill="none" stroke="var(--attn)" strokeWidth={8} strokeLinecap="round" strokeDasharray="0 100000" />}
          <path ref={way} fill="none" stroke="var(--ink)" strokeOpacity={0.55} strokeWidth={2.6} strokeDasharray="1 9" strokeLinecap="round" />
        </svg>
      </div>
      {mode === "run" && (
        <span ref={ball} aria-hidden className="pointer-events-none absolute top-0 left-0 z-[5] block size-0">
          <span className="absolute -top-[1.0625rem] -left-[1.0625rem] block size-[2.125rem] drop-shadow-[3px_3px_0_var(--ink)]">
            <BallIcon />
          </span>
        </span>
      )}
    </>
  );
}
