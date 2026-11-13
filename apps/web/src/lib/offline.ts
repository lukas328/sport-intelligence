"use client";

/**
 * The courtside pages work without network (SPEC 7.11): the service worker keeps the page and
 * its scripts, so a reload in the hall without signal opens the page again (UX test N01).
 */
export async function precache(): Promise<void> {
  if (!("caches" in window)) return;
  const cache = await caches.open("hb-live-v1");
  const assets = performance
    .getEntriesByType("resource")
    .map((e) => e.name)
    .filter((u) => u.startsWith(`${location.origin}/_next/static/`));
  await Promise.all([cache.add(location.href), ...assets.map((u) => cache.add(u).catch(() => undefined))]);
}

/** Registers /sw.js and stores this page and the scripts it loaded. */
export function keepOffline(): void {
  if (typeof navigator === "undefined" || !("serviceWorker" in navigator)) return;
  void navigator.serviceWorker
    .register("/sw.js")
    .then(() => navigator.serviceWorker.ready)
    .then(() => precache())
    .catch(() => undefined);
}

/** A value kept in local storage: the last answer of the server, for the next start offline. */
export function remembered<T>(key: string): T | undefined {
  try {
    const raw = window.localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : undefined;
  } catch {
    return undefined;
  }
}

export function remember(key: string, value: unknown): void {
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* storage blocked: works while the page is open */
  }
}

/** The address the entry sent its sign-in link to: a new link without asking again (UX test N22). */
export const ENTRY_EMAIL = "hb.entry.email";
