"use client";

import { useEffect, useRef, useState } from "react";
import { RunBall } from "@/components/ball-icon";
import { ballWay, ballY } from "@/lib/ball-way";

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
 * always level with the middle of the screen, and the way behind it turns yellow. Inside a drawing
 * the ball runs over the court and under the cards (each drawing holds a place for it,
 * `data-run-ball` in components/step-art.tsx); between the drawings it runs on the page.
 *
 * Calm by design: on a wide screen only (on the phone the steps stand under each other and the
 * way would run through the text), drawn once the page is measured. With reduced motion the way
 * stands still and each step keeps its own ball; without JavaScript there is no way at all and
 * every step shows its ball (`data-ball`). Place it inside the positioned element that holds the
 * steps.
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
    // the way takes the place of a step's own short way; while the ball runs, it stands for the
    // balls of the steps (globals.css)
    host.dataset.way = "";
    if (mode === "run") host.dataset.run = "";
    const frames = Array.from(host.querySelectorAll<HTMLElement>("[data-frame]")).map((el) => ({ el, slot: el.querySelector<HTMLElement>("[data-run-ball]") }));
    let raf = 0;
    let key = "";
    let total = 0;
    let shown = -1;
    let inside: HTMLElement | null | undefined;

    const tick = () => {
      raf = 0;
      const p = way.current;
      if (!p) return;
      // the balls of the steps in the host's coordinates (cheap, and follows any layout change)
      const r = host.getBoundingClientRect();
      const balls = Array.from(host.querySelectorAll<HTMLElement>("[data-ball]"));
      const pts = balls.map((el) => {
        const b = el.getBoundingClientRect();
        return [b.left + b.width / 2 - r.left, b.top + b.height / 2 - r.top] as const;
      });
      // the middle of each step's row: when it is in the middle of the screen, the ball is at its step's ball
      const rows = balls.map((el) => {
        const b = (el.closest("li") ?? el).getBoundingClientRect();
        return b.top + b.height / 2 - r.top;
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
      // the ball follows the middle of the screen: at a step's ball while its row is in the middle
      const goal = lengthAtY(p, ballY(rows, pts, window.innerHeight / 2 - r.top), total);
      const next = shown < 0 ? goal : shown + (goal - shown) * 0.18;
      shown = Math.abs(goal - next) < 0.5 ? goal : next;
      const at = p.getPointAtLength(shown);
      trail.current?.setAttribute("stroke-dasharray", `${shown.toFixed(1)} ${(total + 10).toFixed(1)}`);
      // in a drawing: its own place for the ball, under its cards; else the one on the page
      const x = at.x + r.left;
      const y = at.y + r.top;
      let where: HTMLElement | null = null;
      let ox = r.left;
      let oy = r.top;
      for (const f of frames) {
        const b = f.el.getBoundingClientRect();
        if (f.slot && x >= b.left && x <= b.right && y >= b.top && y <= b.bottom) {
          where = f.slot;
          ox = b.left;
          oy = b.top;
          break;
        }
      }
      const el = where ?? ball.current;
      if (el) el.style.translate = `${(x - ox).toFixed(1)}px ${(y - oy).toFixed(1)}px`;
      if (where !== inside) {
        for (const f of frames) f.slot?.classList.toggle("invisible", f.slot !== where);
        ball.current?.classList.toggle("invisible", where !== null);
        inside = where;
      }
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
      for (const f of frames) f.slot?.classList.add("invisible");
      delete host.dataset.way;
      delete host.dataset.run;
    };
  }, [mode]);

  if (mode === "off") return <div ref={box} hidden />;
  return (
    <>
      <div ref={box} aria-hidden className="pointer-events-none absolute inset-0">
        <svg className="absolute inset-0 block h-full w-full overflow-visible">
          {mode === "run" && <path ref={trail} fill="none" stroke="var(--attn)" strokeWidth={8} strokeLinecap="round" strokeDasharray="0 100000" />}
          <path ref={way} fill="none" stroke="var(--ink)" strokeOpacity={0.55} strokeWidth={2.6} strokeDasharray="1 9" strokeLinecap="round" />
        </svg>
      </div>
      {mode === "run" && (
        <span ref={ball} aria-hidden className="pointer-events-none invisible absolute top-0 left-0 block size-0">
          <RunBall />
        </span>
      )}
    </>
  );
}
