"use client";

import { deviceOf, domHint, isHydration, marksOf, reportOf, takeSlot, type ClientErrorReport } from "@/lib/client-errors";

const HINT_AFTER_MS = 2500;

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
  const post = (report: ClientErrorReport) => {
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
  // a hydration mismatch is told a little later: React first shows the route's loading frame
  // and renders its part again, then the parts that are the same cancel out and the one that
  // differs stays (first reports: the whole match page out, the skeleton in); sent at once
  // when the page is left before
  const later: ClientErrorReport[] = [];
  const flush = () => {
    if (watch) absorb(watch.takeRecords());
    for (const r of later.splice(0)) post({ ...r, dom: domHint(removed, added) });
  };
  window.addEventListener("pagehide", flush);
  const send = (error: unknown, kind: "error" | "rejection") => {
    const device = deviceOf(window.innerWidth, window.matchMedia?.("(pointer: coarse)").matches ?? false);
    const report = reportOf(error, kind, window.location.pathname, device, process.env.NEXT_PUBLIC_BUILD ?? null);
    if (!report) return;
    if (!isHydration(report)) return post(report);
    later.push(report);
    window.setTimeout(flush, HINT_AFTER_MS);
  };
  window.addEventListener("error", (e) => send(e.error ?? e.message, "error"));
  window.addEventListener("unhandledrejection", (e) => send(e.reason, "rejection"));
}

if (typeof window !== "undefined") install();

/** Rendered once (Providers) so the module is part of every page. */
export function ClientErrorReporter() {
  return null;
}
