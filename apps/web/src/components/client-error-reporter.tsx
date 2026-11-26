"use client";

import { deviceOf, reportOf, takeSlot } from "@/lib/client-errors";

/**
 * Sends errors of the app to our API (lib/client-errors): no cookies, nothing personal. Set up
 * when this module loads, before the page hydrates: React reports a hydration mismatch as the
 * first render commits, before any effect would have added the listeners.
 */
function install(): void {
  const w = window as Window & { __hbClientErrors?: boolean };
  if (w.__hbClientErrors) return;
  w.__hbClientErrors = true;
  const send = (error: unknown, kind: "error" | "rejection") => {
    const device = deviceOf(window.innerWidth, window.matchMedia?.("(pointer: coarse)").matches ?? false);
    const report = reportOf(error, kind, window.location.pathname, device, process.env.NEXT_PUBLIC_BUILD ?? null);
    if (!report) return;
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
