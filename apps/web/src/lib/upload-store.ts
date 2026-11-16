"use client";

import { useSyncExternalStore } from "react";

/**
 * The uploads running in this tab, for the progress in the head of every page (K6): an upload
 * goes on while the coach opens other pages (the browser keeps the requests), and the bytes sent
 * are known here at once, before the API's view of the parts catches up.
 */
export type LocalUpload = {
  key: string;
  matchId: string;
  videoId: string | null;
  filename: string;
  done: number;
  total: number;
  startedAt: number;
  /** the moment `done` last grew: the pace and «läuft noch» */
  movedAt: number;
  state: "uploading" | "paused" | "offline" | "failed";
};

let uploads: LocalUpload[] = [];
const listeners = new Set<() => void>();

function emit() {
  for (const l of listeners) l();
}

export function putUpload(next: Omit<LocalUpload, "startedAt" | "movedAt"> & Partial<Pick<LocalUpload, "startedAt" | "movedAt">>): void {
  const now = Date.now();
  const before = uploads.find((u) => u.key === next.key);
  const moved = !before || next.done > before.done ? now : before.movedAt;
  const item: LocalUpload = { ...next, startedAt: before?.startedAt ?? next.startedAt ?? now, movedAt: next.movedAt ?? moved };
  uploads = before ? uploads.map((u) => (u.key === next.key ? item : u)) : [...uploads, item];
  emit();
}

export function dropUpload(key: string): void {
  if (!uploads.some((u) => u.key === key)) return;
  uploads = uploads.filter((u) => u.key !== key);
  emit();
}

export function localUploads(): LocalUpload[] {
  return uploads;
}

function subscribe(l: () => void) {
  listeners.add(l);
  return () => listeners.delete(l);
}

const EMPTY: LocalUpload[] = [];

export function useLocalUploads(): LocalUpload[] {
  return useSyncExternalStore(subscribe, () => uploads, () => EMPTY);
}

/** Seconds left from the pace so far (only after a little way: an early pace misleads). */
export function localEta(u: LocalUpload, now = Date.now()): number | null {
  const took = (u.movedAt - u.startedAt) / 1000;
  if (u.state !== "uploading" || u.done <= 0 || took < 10 || u.done / u.total < 0.01) return null;
  return Math.max(0, Math.round((u.total - u.done) / (u.done / took) - (now - u.movedAt) / 1000));
}
