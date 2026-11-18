"use client";

import { useEffect, useState } from "react";

/**
 * The demo week's parts talk to each other through one window event: an answer of «Frag deine
 * Spiele» plays its scenes in «Drei Dinge» (a set of goal ids) or opens a phase of Saturday. Each
 * such button is also a plain link to the section, so it works without JavaScript.
 */
export const WEEK_EVENT = "hb-week";

export interface WeekDetail {
  /** play these goals on the tactics camera, under this title */
  scenes?: { ids: string[]; title: string; thing?: number };
  /** open this phase of Saturday (0, 1, 2) */
  phase?: number;
}

export function sendWeek(detail: WeekDetail) {
  window.dispatchEvent(new CustomEvent<WeekDetail>(WEEK_EVENT, { detail }));
}

export function useWeek(on: (d: WeekDetail) => void) {
  useEffect(() => {
    const h = (e: Event) => on((e as CustomEvent<WeekDetail>).detail);
    window.addEventListener(WEEK_EVENT, h);
    return () => window.removeEventListener(WEEK_EVENT, h);
  }, [on]);
}

/**
 * false until the page runs scripts: tabs and switches then show every panel one under the other,
 * so the whole page reads without JavaScript; once hydrated only the chosen one stays.
 */
export function useHydrated(): boolean {
  const [on, setOn] = useState(false);
  useEffect(() => setOn(true), []);
  return on;
}

export function reducedMotion(): boolean {
  return typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}
