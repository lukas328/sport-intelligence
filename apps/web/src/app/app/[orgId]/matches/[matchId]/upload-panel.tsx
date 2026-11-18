"use client";

import type { Schemas } from "@handball/api-client";
import { useQueryClient } from "@tanstack/react-query";
import { track } from "@/lib/analytics";
import { useLocale, useTranslations } from "next-intl";
import { looksLikeVideo } from "@/lib/video-file";
import { useEarlyFiles } from "@/lib/early-files";
import { sitePage, useSiteConfig } from "@/lib/site-config";
import { useEffect, useRef, useState, type DragEvent, type FormEvent, type ReactNode } from "react";
import { KitFields } from "@/components/domain/kit-fields";
import { UploadFacts } from "@/components/upload/upload-facts";
import { useOptionalShell } from "@/components/shell/context";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/card";
import { useConfirm } from "@/components/ui/confirm";
import { Input, Select } from "@/components/ui/field";
import { api } from "@/lib/client";
import { connectionHint } from "@/lib/network";
import { errorKey, type ErrorKey } from "@/lib/errors";
import { formatBytes } from "@/lib/format";
import type { Kits } from "@/lib/kit";
import { progressKey, type FileProgress } from "@/lib/progress";
import { fingerprint, localStore, uploadFile, UploadAbortedError, xhrPutPart, type UploadApi } from "@/lib/upload";
import { useStoredUploads } from "@/components/progress/words";
import { dropUpload, putUpload, registerStop, useLocalUploads } from "@/lib/upload-store";
import { otherGame } from "@/lib/file-match";
import { recordingOrder } from "@/lib/video-parts";

const ROLES = ["main", "goal_cam_left", "goal_cam_right", "other"] as const;
type Role = (typeof ROLES)[number];
type Video = Schemas["VideoOut"];

function apiFor(orgId: string, matchId: string): UploadApi {
  const org = { org_id: orgId };
  return {
    async create(input) {
      const { data, error } = await api.POST("/v1/orgs/{org_id}/matches/{match_id}/videos", {
        params: { path: { ...org, match_id: matchId } },
        body: { ...input, role: input.role as Role },
      });
      if (error || !data) throw error;
      return { videoId: data.video.id, partSize: data.part_size, partCount: data.part_count, resumed: data.resumed ?? false };
    },
    async listParts(videoId) {
      const { data, error } = await api.GET("/v1/orgs/{org_id}/videos/{video_id}/parts", {
        params: { path: { ...org, video_id: videoId } },
      });
      if (error || !data) throw error;
      return data;
    },
    async presign(videoId, numbers) {
      const { data, error } = await api.POST("/v1/orgs/{org_id}/videos/{video_id}/parts", {
        params: { path: { ...org, video_id: videoId } },
        body: { numbers },
      });
      if (error || !data) throw error;
      return data;
    },
    async complete(videoId, parts) {
      const { error } = await api.POST("/v1/orgs/{org_id}/videos/{video_id}/complete", {
        params: { path: { ...org, video_id: videoId } },
        body: { parts },
      });
      if (error) throw error;
    },
  };
}

/** One state at a time (L4): never «läuft» and «fehlgeschlagen» together. */
type State =
  | { kind: "idle" }
  | { kind: "uploading"; file: File; done: number; resumed: boolean }
  | { kind: "paused"; file: File }
  | { kind: "confirm"; file: File; hint: "mobile" | "slow" }
  | { kind: "offline"; file: File }
  | { kind: "done" }
  | { kind: "same" }
  | { kind: "error"; error: ErrorKey | "upload" | "notVideo"; file?: File; tries: number };

/** One file of several chosen at once (two halves, a recording the phone split): they go up one
 * after the other, in the order they were recorded (Q-VIDEO-PARTS). */
type Item = { file: File; status: "waiting" | "uploading" | "done" | "same" | "twice" | "failed"; done: number };
type Outcome = "done" | "same" | "stopped";

export function UploadPanel({
  orgId,
  matchId,
  onUploaded,
  hasMain = false,
  kits,
  stuck = [],
  progressFiles = [],
  existing = [],
  shirts,
}: {
  orgId: string;
  matchId: string;
  onUploaded: () => void;
  hasMain?: boolean;
  /** the match's kits: our shirt is asked before the first video (K2) */
  kits?: Kits | null;
  /** uploads of this match the API holds as unfinished (after a reload, another device) */
  stuck?: Video[];
  progressFiles?: FileProgress[];
  /** the names of the files already in the match: a file of another game is pointed out (A5) */
  existing?: string[];
  /** a question about the shirts from the page (the opponent's colour), shown with ours before «Mehr» */
  shirts?: ReactNode;
}) {
  const t = useTranslations();
  const qc = useQueryClient();
  const confirm = useConfirm();
  const [role, setRole] = useState<Role>("main");
  const [state, setState] = useState<State>({ kind: "idle" });
  const [drag, setDrag] = useState(false);
  const [linkMsg, setLinkMsg] = useState<string | null>(null);
  const [linkError, setLinkError] = useState<ErrorKey | null>(null);
  // a stopped upload taken up again: the file chosen must be that file
  const [resuming, setResuming] = useState<Video | null>(null);
  const [mismatch, setMismatch] = useState<Video | null>(null);
  const ctrl = useRef<AbortController | null>(null);
  const videoOf = useRef<Map<File, string>>(new Map());
  // uploads stopped from the progress block («Upload abbrechen», A1): no «pausiert» afterwards
  const stopped = useRef<Set<File>>(new Set());
  const unregister = useRef<Map<File, () => void>>(new Map());
  // a second file whose name looks like another game: pointed out, never blocked (A5)
  const [otherOf, setOtherOf] = useState<{ file: string; first: string } | null>(null);
  const input = useRef<HTMLInputElement>(null);
  const local = useLocalUploads();
  const stored = useStoredUploads(local);
  const uploading = state.kind === "uploading";
  const scope = `${matchId}:${role}`;

  useEffect(() => {
    if (!uploading) return;
    const warn = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = t("upload.leaveWarning");
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [uploading, t]);

  // the hall Wi-Fi drops: continue by itself when the connection is back (parts already sent stay)
  useEffect(() => {
    if (state.kind !== "offline") return;
    const file = state.file;
    const go = () => resume(file);
    window.addEventListener("online", go, { once: true });
    return () => window.removeEventListener("online", go);
  }, [state]); // eslint-disable-line react-hooks/exhaustive-deps

  // a video chosen while the page was still loading (slow phone): the input holds it, start now
  useEarlyFiles(input, (files) => {
    choose(files);
    if (input.current) input.current.value = "";
  });

  const [queue, setQueue] = useState<Item[]>([]);
  const mark = (file: File, patch: Partial<Item>) => setQueue((q) => q.map((it) => (it.file === file ? { ...it, ...patch } : it)));
  const localKey = (file: File) => fingerprint(file, scope);
  const tell = (file: File, done: number, st: "uploading" | "paused" | "offline" | "failed") =>
    putUpload({ key: localKey(file), matchId, videoId: videoOf.current.get(file) ?? null, filename: file.name, done, total: file.size, state: st });

  async function start(file: File, confirmed = false, tries = 0): Promise<Outcome> {
    if (!looksLikeVideo(file)) {
      setState({ kind: "error", error: "notVideo", tries: 0 });
      return "stopped";
    }
    if (!confirmed) {
      const hint = connectionHint();
      if (hint) {
        setState({ kind: "confirm", file, hint });
        return "stopped";
      }
    }
    ctrl.current = new AbortController();
    setState({ kind: "uploading", file, done: 0, resumed: false });
    mark(file, { status: "uploading" });
    let sent = 0;
    try {
      await uploadFile(file, role, {
        api: apiFor(orgId, matchId),
        store: localStore,
        putPart: xhrPutPart,
        scope,
        signal: ctrl.current.signal,
        onStarted: (id) => {
          videoOf.current.set(file, id);
          unregister.current.get(file)?.();
          unregister.current.set(
            file,
            registerStop(id, () => {
              stopped.current.add(file);
              ctrl.current?.abort();
              localStore.remove(localKey(file));
              dropUpload(localKey(file));
              videoOf.current.delete(file);
            }),
          );
          tell(file, sent, "uploading");
          void qc.invalidateQueries({ queryKey: progressKey(orgId) });
        },
        onProgress: (done) => {
          sent = done;
          setState((s) => (s.kind === "uploading" ? { ...s, done } : s));
          mark(file, { done });
          tell(file, done, "uploading");
        },
      });
      mark(file, { status: "done", done: file.size });
      dropUpload(localKey(file));
      track("first_upload", { role });
      onUploaded();
      void qc.invalidateQueries({ queryKey: progressKey(orgId) });
      return "done";
    } catch (e) {
      const status = e && typeof e === "object" && "status" in e ? (e as { status: number }).status : null;
      const type = e && typeof e === "object" && "type" in e ? String((e as { type: unknown }).type) : "";
      if (status === 409 && type.endsWith("same-file")) {
        // the same file is already in the match: said, nothing stored twice
        mark(file, { status: "same" });
        dropUpload(localKey(file));
        return "same";
      }
      if (stopped.current.has(file)) {
        // cancelled in the progress block: the file is gone, nothing to resume
        stopped.current.delete(file);
        setQueue([]);
        setState({ kind: "idle" });
      } else if (e instanceof UploadAbortedError) {
        setState({ kind: "paused", file });
        tell(file, sent, "paused");
      } else if (!navigator.onLine) {
        setState({ kind: "offline", file });
        tell(file, sent, "offline");
      } else {
        setState({ kind: "error", error: status != null ? errorKey(e) : "upload", file, tries: tries + 1 });
        mark(file, { status: "failed" });
        tell(file, sent, "failed");
      }
      return "stopped";
    }
  }

  /** The chosen files, one after the other; stops where one stops (paused, offline, an error) and
   * goes on from there when that one goes on. */
  async function run(items: Item[], confirmed = false, tries = 0) {
    const open = items.filter((it) => it.status === "waiting" || it.status === "uploading" || it.status === "failed");
    let sent = items.some((it) => it.status === "done");
    for (const [i, it] of open.entries()) {
      const outcome = await start(it.file, confirmed || i > 0, tries);
      if (outcome === "stopped") return;
      sent ||= outcome === "done";
    }
    // nothing new went up: every chosen file was already in the match
    setState({ kind: sent ? "done" : "same" });
  }

  function choose(list: FileList | File[]) {
    const files = recordingOrder(Array.from(list));
    if (files.length === 0 || uploading) return;
    // «Fortsetzen» of a stopped upload: only that very file goes on (same name and size)
    if (resuming) {
      const same = files.find((f) => f.name === resuming.filename && f.size === resuming.size_bytes);
      setResuming(null);
      if (!same) return setMismatch(resuming);
      files.splice(0, files.length, same);
    }
    setMismatch(null);
    // another game? said beside the upload, it goes on (several files per match are wanted)
    const odd = role === "main" ? files.map((f) => ({ file: f.name, first: otherGame(f.name, existing) })).find((x) => x.first) : undefined;
    setOtherOf(odd?.first ? { file: odd.file, first: odd.first } : null);
    const seen = new Set<string>();
    const items: Item[] = files.map((file) => {
      const key = `${file.name}:${file.size}`;
      const twice = seen.has(key);
      seen.add(key);
      return { file, status: twice ? "twice" : "waiting", done: 0 };
    });
    setQueue(items);
    void run(items);
  }

  // going on after a pause, the connection, an error: the file that stopped, then the rest
  function resume(file: File, tries = 0) {
    if (queue.length > 1) void run(queue, true, tries);
    else void start(file, true, tries).then((o) => o !== "stopped" && setState({ kind: o === "done" ? "done" : "same" }));
  }

  /** Throws away an unfinished upload (its parts in storage too). */
  async function discard(videoId: string | undefined, file?: File) {
    if (videoId) await api.DELETE("/v1/orgs/{org_id}/videos/{video_id}", { params: { path: { org_id: orgId, video_id: videoId } } });
    if (file) {
      localStore.remove(localKey(file));
      dropUpload(localKey(file));
      videoOf.current.delete(file);
    }
    onUploaded();
    void qc.invalidateQueries({ queryKey: progressKey(orgId) });
  }

  async function restart(file: File) {
    await discard(videoOf.current.get(file), file);
    setQueue((q) => q.map((it) => (it.file === file ? { ...it, status: "waiting", done: 0 } : it)));
    void start(file, true).then((o) => o !== "stopped" && setState({ kind: o === "done" ? "done" : "same" }));
  }

  async function cancel(file?: File, videoId?: string) {
    if (!(await confirm({ title: t("upload.cancelTitle"), body: t("upload.cancelBody"), confirm: t("upload.cancel"), danger: true }))) return;
    ctrl.current?.abort();
    await discard(videoId ?? (file ? videoOf.current.get(file) : undefined), file);
    setQueue([]);
    setState({ kind: "idle" });
  }

  function onDrop(e: DragEvent) {
    e.preventDefault();
    setDrag(false);
    if (!uploading) choose(e.dataTransfer.files);
  }

  async function importLink(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const url = String(new FormData(e.currentTarget).get("url"));
    const { error } = await api.POST("/v1/orgs/{org_id}/matches/{match_id}/videos/import", {
      params: { path: { org_id: orgId, match_id: matchId } },
      body: { url, role },
    });
    if (error) return setLinkError(errorKey(error));
    setLinkError(null);
    setLinkMsg(t("upload.importStarted"));
    onUploaded();
  }

  const site = useSiteConfig();
  const locale = useLocale();
  const pct = state.kind === "uploading" ? Math.floor((state.done / state.file.size) * 100) : 0;
  // unfinished uploads the API knows, not running here: after a reload or from another device
  const mine = new Set(local.map((u) => u.videoId).filter(Boolean));
  const open = stuck.filter((v) => !mine.has(v.id) && !v.duplicate_of);
  const busyHere = state.kind !== "idle" && state.kind !== "done" && state.kind !== "same";
  return (
    <div className="space-y-5">
      {/* a further main file (the second half) comes after the first and is analysed with it:
          said right here, before choosing (Q-VIDEO-PARTS) */}
      {hasMain && role === "main" && (
        <p className="m-0 max-w-[60ch] border-l-4 border-attn pl-3 text-[17px]" data-testid="second-file-note">
          {t("upload.secondFile")}
        </p>
      )}
      {/* stopped uploads: a clear state and a way on (L4) */}
      {!busyHere &&
        open.map((v) => {
          const f = progressFiles.find((x) => x.video_id === v.id);
          // running elsewhere only when this browser did not start it (after a reload it stopped)
          const elsewhere = f?.state === "running" && !stored.has(v.id);
          return (
            <div key={v.id} className="max-w-[62ch] space-y-2 border-l-4 border-attn pl-3" data-testid="upload-stuck" data-elsewhere={elsewhere || undefined}>
              <p className="m-0 text-[17px] font-bold">{t(elsewhere ? "upload.elsewhereTitle" : "upload.stuckTitle", { name: v.filename })}</p>
              <p className="m-0 text-[15px]">
                {f?.uploaded_bytes != null
                  ? t("upload.stuckBytes", { done: formatBytes(f.uploaded_bytes), total: formatBytes(v.size_bytes) })
                  : t("upload.stuckSize", { total: formatBytes(v.size_bytes) })}{" "}
                {t(elsewhere ? "upload.elsewhereText" : "upload.stuckText")}
              </p>
              <div className="flex flex-wrap gap-2">
                {!elsewhere && (
                  <Button
                    size="sm"
                    onClick={() => {
                      setResuming(v);
                      input.current?.click();
                    }}
                    data-testid="stuck-resume"
                  >
                    {t("upload.resumeChoose")}
                  </Button>
                )}
                {!elsewhere && (
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={async () => {
                      await discard(v.id);
                      input.current?.click();
                    }}
                    data-testid="stuck-restart"
                  >
                    {t("upload.restart")}
                  </Button>
                )}
                <Button size="sm" variant="ghost" onClick={() => void cancel(undefined, v.id)} data-testid="stuck-cancel">
                  {t("upload.cancel")}
                </Button>
              </div>
            </div>
          );
        })}
      {otherOf && (
        <p className="m-0 max-w-[62ch] border-l-4 border-attn pl-3 text-[17px]" role="status" data-testid="upload-other-game">
          {t("upload.otherGame", { name: otherOf.file, first: otherOf.first })}
        </p>
      )}
      {mismatch && (
        <Alert data-testid="upload-mismatch">
          {t("upload.mismatch", { name: mismatch.filename, size: formatBytes(mismatch.size_bytes) })}
        </Alert>
      )}
      {/* the field first (finding A11): what to film, files, size and the analysis are behind «Mehr» below */}
      <label
        onDragOver={(e) => {
          e.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={onDrop}
        className={`flex min-h-24 cursor-pointer flex-col items-center justify-center gap-2 border-2 p-5 text-center sm:min-h-32 sm:border-dashed ${drag ? "border-ink bg-surface" : "border-ink"} max-sm:bg-ink max-sm:text-ground`}
      >
        {/* on a phone there is nothing to drag: «Video wählen» */}
        <span className="text-[19px] font-bold sm:hidden">{t("upload.chooseVideo")}</span>
        <span className="hidden text-[17px] font-bold sm:block">{t("upload.drop")}</span>
        <span className="hidden text-[15px] font-semibold underline underline-offset-4 sm:block">{t("upload.choose")}</span>
        {role === "main" && <span className="text-[15px]">{t("upload.several")}</span>}
        <input
          ref={input}
          type="file"
          accept="video/*,.mts,.m2ts,.mkv"
          multiple={role === "main" && !resuming}
          className="sr-only"
          data-testid="video-file"
          disabled={uploading}
          onChange={(e) => {
            if (e.target.files) choose(e.target.files);
            e.target.value = "";
          }}
        />
      </label>
      {queue.length > 1 && (
        <div data-testid="upload-queue">
          <p className="m-0 mb-1.5 text-[17px] font-bold">{t("upload.queueTitle")}</p>
          <ol className="m-0 list-none border-t-2 border-ink p-0">
            {queue.map((it, i) => (
              <li key={`${it.file.name}-${i}`} className="grid grid-cols-[28px_minmax(0,1fr)] gap-x-3 border-b border-rule py-2.5 text-[17px]" data-testid="upload-queue-item" data-status={it.status}>
                <span className="font-num text-[22px] leading-none">{i + 1}</span>
                <span className="min-w-0">
                  <span className="block truncate font-semibold">{it.file.name}</span>
                  <span className="block text-[15px] text-ink-2">
                    {formatBytes(it.file.size)} ·{" "}
                    <span className={it.status === "same" || it.status === "twice" || it.status === "failed" ? "font-bold text-ink" : undefined}>
                      {it.status === "uploading"
                        ? t("upload.queueUploading", { percent: Math.floor((it.done / Math.max(1, it.file.size)) * 100) })
                        : t(`upload.${({ waiting: "queueWaiting", done: "queueDone", same: "queueSame", twice: "queueTwice", failed: "queueFailed" } as const)[it.status]}`)}
                    </span>
                  </span>
                </span>
              </li>
            ))}
          </ol>
        </div>
      )}
      {state.kind === "uploading" && (
        <div className="space-y-2" role="status" data-testid="upload-running">
          <div className="h-2 overflow-hidden bg-surface">
            <div className="h-full bg-accent transition-all" style={{ width: `${pct}%` }} />
          </div>
          <p className="text-sm tabular-nums" data-testid="upload-progress">
            {t("upload.progress", { percent: pct, done: formatBytes(state.done), total: formatBytes(state.file.size) })}
          </p>
          <p className="m-0 text-[15px] text-ink-2">{t("upload.mayBrowse")}</p>
          <Button variant="secondary" onClick={() => ctrl.current?.abort()}>
            {t("upload.pause")}
          </Button>
        </div>
      )}
      {state.kind === "confirm" && (
        <Alert kind="info">
          <span className="block">{t(state.hint === "mobile" ? "upload.mobileData" : "upload.slowLink", { size: formatBytes(state.file.size) })}</span>
          <span className="mt-2 flex gap-2">
            <Button onClick={() => (queue.length > 1 ? void run(queue, true) : void start(state.file, true).then((o) => o !== "stopped" && setState({ kind: o === "done" ? "done" : "same" })))}>{t("upload.uploadAnyway")}</Button>
            <Button variant="ghost" onClick={() => setState({ kind: "idle" })}>
              {t("upload.later")}
            </Button>
          </span>
        </Alert>
      )}
      {state.kind === "offline" && (
        <Alert kind="info" data-testid="upload-offline">
          {t("upload.offline")}
        </Alert>
      )}
      {state.kind === "paused" && (
        <Alert kind="info" data-testid="upload-paused">
          <span className="block">{t("upload.pausedHere")}</span>
          <span className="mt-2 flex flex-wrap gap-2">
            <Button variant="secondary" onClick={() => resume(state.file)}>
              {t("upload.resume")}
            </Button>
            <Button variant="ghost" onClick={() => void cancel(state.file)}>
              {t("upload.cancel")}
            </Button>
          </span>
        </Alert>
      )}
      {state.kind === "done" && (
        // the reassurance the coach needs on the phone (UX test H05, Z4)
        <Alert kind="success" data-testid="upload-done">
          <span className="block font-bold">{t("upload.done")}</span>
          <span className="block">{t("upload.mayCloseNow")}</span>
        </Alert>
      )}
      {state.kind === "same" && (
        <Alert kind="info" data-testid="upload-same">
          {t("upload.queueSame")}
        </Alert>
      )}
      {state.kind === "error" && (
        <Alert data-testid="upload-error">
          {state.error === "notVideo" ? (
            <>
              <span className="block font-bold">{t("processing.failedTitle")}</span>
              <span className="block">{t("upload.notVideo")}</span>
            </>
          ) : (
            <>
              <span className="block font-bold">{t("upload.failedTitle")}</span>
              <span className="block">{state.error === "upload" ? t("upload.failedText") : t(`errors.${state.error}`)}</span>
              {state.tries > 1 && <span className="mt-1 block">{t("upload.failedAgain")}</span>}
            </>
          )}
          {state.file && (
            <span className="mt-2 flex flex-wrap gap-2">
              <Button variant="secondary" onClick={() => resume(state.file!, state.tries)} data-testid="upload-retry">
                {t("upload.resume")}
              </Button>
              <Button variant="ghost" onClick={() => void restart(state.file!)} data-testid="upload-restart">
                {t("upload.restart")}
              </Button>
              <Button variant="ghost" onClick={() => void cancel(state.file)}>
                {t("upload.cancel")}
              </Button>
            </span>
          )}
        </Alert>
      )}
      {/* our shirt: it helps the analysis tell the teams apart (K2); saved at once, also while the
          upload runs */}
      {kits && role === "main" && !hasMain && <OwnKit orgId={orgId} matchId={matchId} kits={kits} />}
      {shirts}
      {/* the rest can wait: how to film, files and size, another camera, a link (A11: about 200 words
          stood before the field) */}
      <details className="text-[15px]" data-testid="upload-more">
        <summary className="min-h-11 cursor-pointer content-center font-semibold">{t("upload.moreAll")}</summary>
        <div className="mt-3 space-y-5">
          <ul className="m-0 list-none space-y-1.5 p-0 text-[17px]" data-testid="upload-tips">
            <li>{t("upload.tip1")}</li>
            <li>{t("upload.tip2")}</li>
            <li>{t("upload.tip3")}</li>
          </ul>
          <UploadFacts />
          {/* the guide on the website, its address from the configuration */}
          {site && (
            <a href={sitePage(site.site_url, locale, "aufnahme/")} target="_blank" rel="noreferrer" className="inline-flex min-h-11 items-center text-[17px] font-bold text-ink underline decoration-[1.5px] underline-offset-4">
              {t("upload.guide")}
            </a>
          )}
          <div className="max-w-xs">
            <Select label={t("upload.role")} value={role} onChange={(e) => setRole(e.target.value as Role)} disabled={uploading}>
              {ROLES.map((r) => (
                <option key={r} value={r}>
                  {t(`upload.role_${r}`)}
                </option>
              ))}
            </Select>
          </div>
          <form onSubmit={importLink} className="flex flex-wrap items-end gap-2">
            <div className="min-w-64 flex-1">
              <Input label={t("upload.linkLabel")} name="url" type="url" required pattern="https://.*" hint={t("upload.linkHint")} />
            </div>
            <Button type="submit" variant="secondary">
              {t("upload.import")}
            </Button>
          </form>
          {linkMsg && <p className="mt-2 text-ok">{linkMsg}</p>}
          {linkError && <Alert className="mt-2">{t(`errors.${linkError}`)}</Alert>}
          <p className="m-0">{t("upload.tips")}</p>
        </div>
      </details>
    </div>
  );
}

/** Our shirt in this match (K2): the club's home or away shirt in one tap, or another colour; the
 * goalkeeper too. Saved right away, the analysis reads it. */
function OwnKit({ orgId, matchId, kits }: { orgId: string; matchId: string; kits: Kits }) {
  const t = useTranslations();
  const qc = useQueryClient();
  const shell = useOptionalShell();
  const [value, setValue] = useState(kits);
  const [saved, setSaved] = useState(false);
  const timer = useRef<number | null>(null);
  function change(next: Kits) {
    setValue(next);
    setSaved(false);
    if (timer.current) window.clearTimeout(timer.current);
    // the colour picker sends many values while dragging: saved once it rests
    timer.current = window.setTimeout(async () => {
      const r = await api.PATCH("/v1/orgs/{org_id}/matches/{match_id}", {
        params: { path: { org_id: orgId, match_id: matchId } },
        body: { kit_own: next.own, kit_own_gk: next.own_gk },
      });
      if (r.response.ok) {
        setSaved(true);
        void qc.invalidateQueries({ queryKey: ["match", matchId] });
      }
    }, 500);
  }
  return (
    <fieldset className="m-0 max-w-[62ch] border-0 p-0" data-testid="upload-own-kit">
      <legend className="mb-2 text-[17px] font-bold">{t("upload.ownKit")}</legend>
      <KitFields kits={value} onChange={change} only={["own", "own_gk"]} presets={shell ? { home: shell.org.primary_color, away: shell.org.secondary_color ?? null } : null} />
      <p className="m-0 mt-1 text-sm text-ink-2" aria-live="polite">
        {saved ? t("upload.ownKitSaved") : " "}
      </p>
    </fieldset>
  );
}
