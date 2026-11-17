"use client";

import { usePathname } from "next/navigation";
import { type ReactNode, useEffect, useRef, useState } from "react";
import { nextHidden } from "@/lib/header-scroll";

/** Below this width the bar is pinned and slim (the phone and the tablet, BEFUNDE-3 U12). */
const DESKTOP = "(min-width: 1024px)";

/**
 * The top bar's frame. On the phone and the tablet it is pinned (sticky, so nothing below it jumps)
 * and slides away while you scroll down; the first scroll up brings it back at once (U12). It
 * stays while its menu is open or something in it has the focus. With reduced motion it appears
 * and goes without sliding; without JavaScript it simply stays pinned. From a laptop on the bar
 * scrolls with the page as before.
 */
export function HeaderShell({ children }: { children: ReactNode }) {
  const ref = useRef<HTMLElement>(null);
  const [hidden, setHidden] = useState(false);
  useEffect(() => {
    const desktop = window.matchMedia(DESKTOP);
    let last = window.scrollY;
    let raf = 0;
    const step = () => {
      raf = 0;
      const el = ref.current;
      if (!el) return;
      const max = document.documentElement.scrollHeight - window.innerHeight;
      // the rubber band past the top or the bottom (iOS) is no scrolling
      const y = Math.min(Math.max(0, window.scrollY), Math.max(0, max));
      const dy = y - last;
      last = y;
      const busy = el.querySelector("details[open]") !== null || el.contains(document.activeElement);
      setHidden((h) => (desktop.matches || busy ? false : nextHidden(h, y, dy, el.offsetHeight)));
    };
    const onScroll = () => {
      if (!raf) raf = requestAnimationFrame(step);
    };
    const show = () => setHidden(false);
    window.addEventListener("scroll", onScroll, { passive: true });
    desktop.addEventListener("change", show);
    const el = ref.current;
    el?.addEventListener("focusin", show);
    return () => {
      window.removeEventListener("scroll", onScroll);
      desktop.removeEventListener("change", show);
      el?.removeEventListener("focusin", show);
      cancelAnimationFrame(raf);
    };
  }, []);
  return (
    <header
      ref={ref}
      data-hidden={hidden ? "" : undefined}
      className="cloth sticky top-0 z-30 border-b-2 border-ink transition-transform duration-200 ease-out data-[hidden]:-translate-y-[calc(100%+2px)] motion-reduce:transition-none lg:relative lg:translate-y-0 lg:data-[hidden]:translate-y-0"
    >
      {children}
    </header>
  );
}

function closeMenu(d: HTMLDetailsElement | null, focus: boolean) {
  if (!d?.open) return;
  d.open = false;
  if (focus) d.querySelector("summary")?.focus();
}

/**
 * «Menü» on the phone and the tablet: a <details>, so it opens without JavaScript too. With
 * JavaScript it closes when a link in it is tapped, on every page change, on Escape and on a tap
 * outside; after a link or Escape the focus goes back to «Menü» (U10).
 */
export function MenuDisclosure({ label, className, children }: { label: string; className?: string; children: ReactNode }) {
  const ref = useRef<HTMLDetailsElement>(null);
  const path = usePathname();
  const close = (focus: boolean) => closeMenu(ref.current, focus);
  useEffect(() => {
    closeMenu(ref.current, true);
  }, [path]);
  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    const outside = (e: PointerEvent) => {
      if (d.open && !d.contains(e.target as Node)) d.open = false;
    };
    document.addEventListener("pointerdown", outside);
    return () => document.removeEventListener("pointerdown", outside);
  }, []);
  return (
    <details
      ref={ref}
      className={className}
      onClick={(e) => {
        if ((e.target as Element).closest("a")) close(true);
      }}
      onKeyDown={(e) => {
        if (e.key === "Escape" && ref.current?.open) {
          e.preventDefault();
          close(true);
        }
      }}
    >
      <summary className="btn btn-line min-h-12 list-none px-5">{label}</summary>
      {children}
    </details>
  );
}
