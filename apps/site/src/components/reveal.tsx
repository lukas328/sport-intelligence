"use client";

import { useEffect } from "react";

/**
 * A short glide for the blocks marked `data-reveal` when they come into view (BEFUNDE-3 U19).
 * Additive only: every block is visible as rendered, without JavaScript, with reduced motion, in
 * print and for a tool that never scrolls. A block below the first screen gets `wait` (it only
 * holds its line drawings and arrows at their start) and, the moment it enters the screen, `in`,
 * which plays half a second of fade and rise. `--d` on a block delays it a little (0, 1, 2 …).
 * Mounted once per page.
 */
export function Reveal() {
  useEffect(() => {
    if (typeof IntersectionObserver === "undefined") return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const els = Array.from(document.querySelectorAll<HTMLElement>("[data-reveal]"));
    const io = new IntersectionObserver((entries) => {
      for (const e of entries) {
        if (!e.isIntersecting) continue;
        e.target.classList.remove("wait");
        e.target.classList.add("in");
        io.unobserve(e.target);
      }
    });
    for (const el of els) {
      if (el.getBoundingClientRect().top < window.innerHeight) continue;
      el.classList.add("wait");
      io.observe(el);
    }
    const done = () => {
      io.disconnect();
      for (const el of els) el.classList.remove("wait");
    };
    window.addEventListener("beforeprint", done);
    return () => {
      window.removeEventListener("beforeprint", done);
      done();
      for (const el of els) el.classList.remove("in");
    };
  }, []);
  return null;
}
