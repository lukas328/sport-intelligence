"use client";

import { type RefObject, useEffect } from "react";

/**
 * A player that sticks at the top of the page covers what scrolls under it, also an element that
 * takes the keyboard focus (WCAG 2.4.11, accessibility audit: 13 of 70 focus stops on a phone).
 * The page's scroll padding (globals.css) keeps the room of the tallest sticky player in
 * `--sticky-player`, so the browser scrolls a focused element into view below it.
 */
const heights = new Map<symbol, number>();

function apply(): void {
  const tallest = stickyRoom(heights.values());
  document.documentElement.style.setProperty("--sticky-player", `${tallest}px`);
  if (!heights.size) document.documentElement.style.removeProperty("--sticky-player");
}

/** The room of the tallest sticky player: the largest height (0 without any). */
export function stickyRoom(values: Iterable<number>): number {
  return Math.max(0, ...values);
}

export function useStickyFocusRoom(ref: RefObject<HTMLElement | null>, { active = true, phoneOnly = false }: { active?: boolean; phoneOnly?: boolean } = {}): void {
  useEffect(() => {
    const el = ref.current;
    if (!active || !el || typeof ResizeObserver === "undefined") return;
    const key = Symbol("sticky");
    const phone = window.matchMedia("(max-width: 1023.98px)");
    const set = () => {
      heights.set(key, !phoneOnly || phone.matches ? Math.round(el.getBoundingClientRect().height) : 0);
      apply();
    };
    const watch = new ResizeObserver(set);
    watch.observe(el);
    phone.addEventListener("change", set);
    set();
    return () => {
      watch.disconnect();
      phone.removeEventListener("change", set);
      heights.delete(key);
      apply();
    };
  }, [ref, active, phoneOnly]);
}
