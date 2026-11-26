"use client";

import { deviceOf, domHint, isHydration, marksOf, reportOf, takeSlot } from "@/lib/client-errors";

/**
 * Sends errors of the app to our API (lib/client-errors): no cookies, nothing personal. Set up
 * when this module loads, before the page hydrates: React reports a hydration mismatch as the
 * first render commits, before any effect would have added the listeners.
 */
function install(): void {
  const w = window as Window & { __hbClientErrors?: boolean };
  if (w.__hbClientErrors) return;
  w.__hbClientErrors = true;
  // what React takes out of the page and puts in while it hydrates, as tags and test ids only:
  // after a mismatch it swaps the server's part for its own; watched for the first 15 s
  const removed: string[] = [];
  const added: string[] = [];
  const absorb = (records: MutationRecord[]) => {
    for (const r of records) {
      for (const n of Array.from(r.removedNodes)) removed.push(...marksOf(n));
      for (const n of Array.from(r.addedNodes)) added.push(...marksOf(n));
    }
    removed.splice(0, Math.max(0, removed.length - 600));
    added.splice(0, Math.max(0, added.length - 600));
  };
  const watch = typeof MutationObserver === "function" ? new MutationObserver(absorb) : null;
  watch?.observe(document.documentElement, { childList: true, subtree: true });
  window.setTimeout(() => watch?.disconnect(), 15_000);
  const send = (error: unknown, kind: "error" | "rejection") => {
    const device = deviceOf(window.innerWidth, window.matchMedia?.("(pointer: coarse)").matches ?? false);
    const report = reportOf(error, kind, window.location.pathname, device, process.env.NEXT_PUBLIC_BUILD ?? null);
    if (!report) return;
    // a hydration mismatch: React has put its client render in place by now
    if (isHydration(report)) {
      if (watch) absorb(watch.takeRecords()); // the swap has happened, its records may still wait
      report.dom = domHint(removed, added);
    }
    let storage: Storage | null = null;
    try {
      storage = window.sessionStorage;
    } catch {
      storage = null;
    }
    if (!takeSlot(storage)) return;
    void fetch("/v1/client-errors", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(report),
      credentials: "omit",
      keepalive: true,
    }).catch(() => undefined);
  };
  window.addEventListener("error", (e) => send(e.error ?? e.message, "error"));
  window.addEventListener("unhandledrejection", (e) => send(e.reason, "rejection"));
}

if (typeof window !== "undefined") install();

/** Rendered once (Providers) so the module is part of every page. */
export function ClientErrorReporter() {
  return null;
}
