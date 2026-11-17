"use client";

import { useEffect } from "react";

/**
 * Lets the blocks marked `data-reveal` glide in when they come into view. Only blocks below the
 * first screen are hidden first (never what is already visible, so nothing flickers), nothing
 * is hidden without JavaScript, and with reduced motion the CSS shows everything as it is.
 * Mounted once per page; `--d` on a block delays it a little (0, 1, 2 …).
 */
export function Reveal() {
  useEffect(() => {
    if (typeof IntersectionObserver === "undefined") return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const els = Array.from(document.querySelectorAll<HTMLElement>("[data-reveal]"));
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (!e.isIntersecting) continue;
          e.target.classList.remove("pre");
          io.unobserve(e.target);
        }
      },
      { rootMargin: "0px 0px -8% 0px", threshold: 0.12 },
    );
    for (const el of els) {
      if (el.getBoundingClientRect().top < window.innerHeight * 0.92) continue;
      el.classList.add("pre");
      io.observe(el);
    }
    return () => {
      io.disconnect();
      for (const el of els) el.classList.remove("pre");
    };
  }, []);
  return null;
}
