"use client";

import type { Schemas } from "@handball/api-client";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/client";
import { localEta, type LocalUpload } from "@/lib/upload-store";

/**
 * The progress of uploads and processing (K6, K13, B4), as the API reports it per file and step
 * (services/progress), with the uploads of this tab laid over (their bytes are known here first).
 * The words stay honest: a time only when it can be estimated, else the step that runs.
 */
export type MatchProgress = Schemas["MatchProgressOut"];
export type FileProgress = Schemas["FileProgressOut"];
export type Stage = FileProgress["stage"];
export type State = FileProgress["state"];

export const STEPS = ["upload", "ingest", "analysis", "done"] as const;
const ACTIVE: State[] = ["running", "queued", "waiting", "stalled", "interrupted"];
const UPLOAD_WEIGHT = { main: 0.1, other: 0.25 };

export const isActive = (p: { state: State }) => ACTIVE.includes(p.state);

export const progressKey = (orgId: string) => ["progress", orgId];

/** The progress of the club's matches: often while something runs, rarely when nothing does. */
export function useProgress(orgId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: progressKey(orgId ?? ""),
    enabled: Boolean(orgId) && enabled,
    retry: false,
    staleTime: 5_000,
    refetchInterval: (q) => {
      const data = q.state.data as MatchProgress[] | undefined;
      return data?.some(isActive) ? 10_000 : 60_000;
    },
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/progress", { params: { path: { org_id: orgId! } } })).data ?? [],
  });
}

function fileWithLocal(f: FileProgress, u: LocalUpload, now: number): FileProgress {
  if (f.stage !== "upload") return f;
  const fraction = u.total ? Math.min(1, u.done / u.total) : (f.fraction ?? 0);
  const weight = f.role === "main" ? UPLOAD_WEIGHT.main : UPLOAD_WEIGHT.other;
  const running = u.state === "uploading";
  const eta = running ? localEta(u, now) : null;
  return {
    ...f,
    state: running ? "running" : "interrupted",
    uploaded_bytes: u.done,
    fraction,
    overall: Math.round(weight * fraction * 10_000) / 10_000,
    eta_s: eta,
    finish_s: null,
    eta_basis: eta != null ? "measured" : null,
    idle_s: running ? null : Math.round((now - u.movedAt) / 1000),
    last_activity_at: new Date(u.movedAt).toISOString(),
  };
}

function summarise(p: MatchProgress, files: FileProgress[]): MatchProgress {
  const active = files.filter(isActive);
  const state: State = active.some((f) => f.state === "stalled")
    ? "stalled"
    : active.some((f) => f.state === "interrupted")
      ? "interrupted"
      : active.length
        ? "running"
        : files.some((f) => f.state === "failed")
          ? "failed"
          : "done";
  const order = (s: Stage) => STEPS.indexOf(s);
  const stage = active.length ? active.map((f) => f.stage).sort((a, b) => order(a) - order(b))[0]! : "done";
  const overall = files.length ? files.reduce((s, f) => s + f.overall, 0) / files.length : p.overall;
  // a stage of the upload in this tab: its own time left (the later steps cannot be known yet)
  const eta = stage === "upload" ? (active.find((f) => f.stage === "upload")?.eta_s ?? null) : p.eta_s;
  return { ...p, files, state, stage, overall, eta_s: state === "running" ? eta : null };
}

/** The API's progress with the uploads of this tab laid over (same video id). `stored`: the
 * unfinished uploads this browser started; one of them not running in this tab has stopped (a
 * reload after a failure), even while the storage's last part is only a minute old (L4). */
export function withLocal(list: MatchProgress[], local: LocalUpload[], now = Date.now(), stored: ReadonlySet<string> = new Set()): MatchProgress[] {
  if (!local.length && !stored.size) return list;
  return list.map((p) => {
    const mine = local.filter((u) => u.matchId === p.match_id && u.videoId);
    const stopped = (f: FileProgress) => f.stage === "upload" && f.state === "running" && f.step !== "link" && stored.has(f.video_id) && !mine.some((u) => u.videoId === f.video_id);
    if (!mine.length && !p.files.some(stopped)) return p;
    const files = p.files.map((f) => {
      const u = mine.find((x) => x.videoId === f.video_id);
      if (u) return fileWithLocal(f, u, now);
      if (stopped(f)) {
        const idle = f.last_activity_at ? Math.max(0, Math.round((now - Date.parse(f.last_activity_at)) / 1000)) : null;
        return { ...f, state: "interrupted" as const, eta_s: null, finish_s: null, eta_basis: null, idle_s: idle };
      }
      return f;
    });
    return summarise(p, files);
  });
}

/** A duration as people say it: minutes (in fives above twenty), from an hour on hours and
 * minutes. Rounded up, so «etwa 5 Min.» never runs out at 4. */
export function durationParts(seconds: number): { h: number; m: number } {
  let m = Math.max(1, Math.ceil(seconds / 60));
  if (m > 20) m = Math.ceil(m / 5) * 5;
  return { h: Math.floor(m / 60), m: m % 60 };
}

/** The clock time something is probably done. */
export function finishAt(etaS: number, now = Date.now()): Date {
  return new Date(now + etaS * 1000);
}

/** The key of the headline in the namespace «progress» for a match's state and step. */
export function headlineKey(p: Pick<MatchProgress, "state" | "stage" | "files">): string {
  if (p.state === "stalled") return p.stage === "ingest" ? "headStalledIngest" : "headStalled";
  if (p.state === "interrupted") return "headInterrupted";
  if (p.state === "failed") return "headFailed";
  if (p.state === "done") return "headDone";
  if (p.stage === "upload") return "headUpload";
  // nothing runs yet, everything waits for a worker: said so, not «wird eingelesen»
  const active = p.files.filter(isActive);
  if (active.length && active.every((f) => f.state === "queued")) return "headQueued";
  if (p.stage === "ingest") return "headIngest";
  return "headAnalysis";
}

/** The words of a file's state for the summary line of several files (second round A2). */
export type FileWord = "done" | "failed" | "interrupted" | "stalled" | "upload" | "ingest" | "analysis" | "waiting";

export function fileWord(f: Pick<FileProgress, "state" | "stage">): FileWord {
  if (f.state === "done") return "done";
  if (f.state === "failed") return "failed";
  if (f.state === "interrupted") return "interrupted";
  if (f.state === "stalled") return "stalled";
  if (f.state === "queued" || f.state === "waiting") return "waiting";
  return f.stage === "done" ? "done" : f.stage;
}

/** Several files in one line: how many do what, in a fixed order («1 fertig, 1 Upload
 * unterbrochen»). */
export function filesLine(files: Pick<FileProgress, "state" | "stage">[]): { word: FileWord; n: number }[] {
  const order: FileWord[] = ["upload", "ingest", "analysis", "waiting", "interrupted", "stalled", "failed", "done"];
  const counts = new Map<FileWord, number>();
  for (const f of files) counts.set(fileWord(f), (counts.get(fileWord(f)) ?? 0) + 1);
  return order.filter((w) => counts.has(w)).map((word) => ({ word, n: counts.get(word)! }));
}

/** The bar of the progress block: while uploading how far the uploads are (what the time beside
 * it says), else the whole way; null while a file holds (stopped, silent, failed), when a bar
 * would promise progress that does not happen (second round A2). */
export function barValue(p: Pick<MatchProgress, "stage" | "state" | "overall" | "files">): number | null {
  if (p.files.some((f) => f.state === "interrupted" || f.state === "stalled" || f.state === "failed")) return null;
  if (p.stage === "upload") {
    const up = p.files.filter((f) => f.stage === "upload");
    return up.length ? up.reduce((s, f) => s + (f.fraction ?? 0), 0) / up.length : p.overall;
  }
  return p.overall;
}

/** What a file offers in the progress block (second round A1): «Upload abbrechen» while it is
 * uploaded or stuck (its uploader or the staff), «Datei entfernen» once it arrived or failed (the
 * staff who may delete), nothing while a worker has it. */
export function fileActions(f: Pick<FileProgress, "stage" | "state" | "step">, who: { staff: boolean; canDelete: boolean; own: boolean }): "cancel" | "remove" | null {
  if (f.stage === "upload" && f.state !== "failed") return f.step !== "link" && (who.staff || who.own) ? "cancel" : null;
  if (f.state === "failed" || f.state === "done") return who.canDelete ? "remove" : null;
  return null;
}

/** The tone of the progress: running, needs a look (stalled, stopped), done, failed. */
export function tone(p: { state: State }): "run" | "attn" | "done" | "fail" {
  if (p.state === "stalled" || p.state === "interrupted") return "attn";
  if (p.state === "failed") return "fail";
  if (p.state === "done") return "done";
  return "run";
}

/** The step a file is in for the row of steps: done, running (or its trouble), next. */
export function stepState(f: FileProgress, step: (typeof STEPS)[number]): "done" | "now" | "next" {
  const at = STEPS.indexOf(f.stage);
  const i = STEPS.indexOf(step);
  if (f.stage === "done" || i < at) return "done";
  return i === at ? "now" : "next";
}

/** A finished match's progress the coach closed in the head stays closed (per match). */
const SEEN = "hb-progress-seen";

export function seenDone(): Set<string> {
  try {
    return new Set(JSON.parse(window.localStorage.getItem(SEEN) ?? "[]") as string[]);
  } catch {
    return new Set();
  }
}

export function markSeen(matchId: string): void {
  try {
    const all = [...seenDone(), matchId].slice(-50);
    window.localStorage.setItem(SEEN, JSON.stringify(all));
  } catch {
    /* private mode: shown again until it ages out */
  }
}

/** Stopped uploads whose yellow line the coach dismissed («Verwerfen», second round A9), by
 * video; the line goes for good once the server gives the upload up (after 6 hours). */
const DISMISSED = "hb-upload-dismissed";

export function dismissedUploads(): Set<string> {
  try {
    return new Set(JSON.parse(window.localStorage.getItem(DISMISSED) ?? "[]") as string[]);
  } catch {
    return new Set();
  }
}

export function dismissUploads(ids: string[]): void {
  try {
    const all = [...new Set([...dismissedUploads(), ...ids])].slice(-50);
    window.localStorage.setItem(DISMISSED, JSON.stringify(all));
  } catch {
    /* private mode: the line stays until the upload is given up */
  }
}

/** A match whose only trouble is stopped uploads the coach dismissed: the line in the head stays
 * away (its own page still shows the files). */
export function onlyDismissed(p: Pick<MatchProgress, "files">, dismissed: ReadonlySet<string>): boolean {
  const active = p.files.filter(isActive);
  return active.length > 0 && active.every((f) => f.state === "interrupted" && dismissed.has(f.video_id));
}
