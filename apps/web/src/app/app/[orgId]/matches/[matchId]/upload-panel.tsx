"use client";

import { track } from "@/lib/analytics";
import { useLocale, useTranslations } from "next-intl";
import { looksLikeVideo } from "@/lib/video-file";
import { sitePage, useSiteConfig } from "@/lib/site-config";
import { useEffect, useRef, useState, type DragEvent, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/card";
import { Input, Select } from "@/components/ui/field";
import { api } from "@/lib/client";
import { connectionHint } from "@/lib/network";
import { errorKey, type ErrorKey } from "@/lib/errors";
import { formatBytes } from "@/lib/format";
import { localStore, uploadFile, UploadAbortedError, xhrPutPart, type UploadApi } from "@/lib/upload";
import { recordingOrder } from "@/lib/video-parts";

const ROLES = ["main", "goal_cam_left", "goal_cam_right", "other"] as const;
type Role = (typeof ROLES)[number];

function apiFor(orgId: string, matchId: string): UploadApi {
  const org = { org_id: orgId };
  return {
    async create(input) {
      const { data, error } = await api.POST("/v1/orgs/{org_id}/matches/{match_id}/videos", {
        params: { path: { ...org, match_id: matchId } },
        body: { ...input, role: input.role as Role },
      });
      if (error || !data) throw error;
      return { videoId: data.video.id, partSize: data.part_size, partCount: data.part_count };
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

type State =
  | { kind: "idle" }
  | { kind: "uploading"; file: File; done: number; resumed: boolean }
  | { kind: "paused"; file: File }
  | { kind: "confirm"; file: File; hint: "mobile" | "slow" }
  | { kind: "offline"; file: File }
  | { kind: "done" }
  | { kind: "same" }
  | { kind: "error"; error: ErrorKey | "upload" | "notVideo"; file?: File };

/** One file of several chosen at once (two halves, a recording the phone split): they go up one
 * after the other, in the order they were recorded (Q-VIDEO-PARTS). */
type Item = { file: File; status: "waiting" | "uploading" | "done" | "same" | "twice" | "failed"; done: number };
type Outcome = "done" | "same" | "stopped";



export function UploadPanel({ orgId, matchId, onUploaded, hasMain = false }: { orgId: string; matchId: string; onUploaded: () => void; hasMain?: boolean }) {
  const t = useTranslations();
  const [role, setRole] = useState<Role>("main");
  const [state, setState] = useState<State>({ kind: "idle" });
  const [drag, setDrag] = useState(false);
  const [linkMsg, setLinkMsg] = useState<string | null>(null);
  const [linkError, setLinkError] = useState<ErrorKey | null>(null);
  const ctrl = useRef<AbortController | null>(null);
  const uploading = state.kind === "uploading";

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

  const [queue, setQueue] = useState<Item[]>([]);
  const mark = (file: File, patch: Partial<Item>) => setQueue((q) => q.map((it) => (it.file === file ? { ...it, ...patch } : it)));

  async function start(file: File, confirmed = false): Promise<Outcome> {
    if (!looksLikeVideo(file)) {
      setState({ kind: "error", error: "notVideo" });
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
    try {
      await uploadFile(file, role, {
        api: apiFor(orgId, matchId),
        store: localStore,
        putPart: xhrPutPart,
        scope: `${matchId}:${role}`,
        signal: ctrl.current.signal,
        onProgress: (done) => {
          setState((s) => (s.kind === "uploading" ? { ...s, done } : s));
          mark(file, { done });
        },
      });
      mark(file, { status: "done", done: file.size });
      track("first_upload", { role });
      onUploaded();
      return "done";
    } catch (e) {
      const status = e && typeof e === "object" && "status" in e ? (e as { status: number }).status : null;
      const type = e && typeof e === "object" && "type" in e ? String((e as { type: unknown }).type) : "";
      if (status === 409 && type.endsWith("same-file")) {
        // the same file is already in the match: said, nothing stored twice
        mark(file, { status: "same" });
        return "same";
      }
      if (e instanceof UploadAbortedError) setState({ kind: "paused", file });
      else if (!navigator.onLine) setState({ kind: "offline", file });
      else {
        setState({ kind: "error", error: status != null ? errorKey(e) : "upload", file });
        mark(file, { status: "failed" });
      }
      return "stopped";
    }
  }

  /** The chosen files, one after the other; stops where one stops (paused, offline, an error) and
   * goes on from there when that one goes on. */
  async function run(items: Item[], confirmed = false) {
    const open = items.filter((it) => it.status === "waiting" || it.status === "uploading" || it.status === "failed");
    let sent = items.some((it) => it.status === "done");
    for (const [i, it] of open.entries()) {
      const outcome = await start(it.file, confirmed || i > 0);
      if (outcome === "stopped") return;
      sent ||= outcome === "done";
    }
    // nothing new went up: every chosen file was already in the match
    setState({ kind: sent ? "done" : "same" });
  }

  function choose(list: FileList | File[]) {
    const files = recordingOrder(Array.from(list));
    if (files.length === 0 || uploading) return;
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
  function resume(file: File) {
    if (queue.length > 1) void run(queue, true);
    else void start(file, true).then((o) => o !== "stopped" && setState({ kind: o === "done" ? "done" : "same" }));
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
  return (
    <div className="space-y-5">
      {/* a further main file (the second half) comes after the first and is analysed with it:
          said right here, before choosing (Q-VIDEO-PARTS) */}
      {hasMain && role === "main" && (
        <p className="m-0 max-w-[60ch] border-l-4 border-attn pl-3 text-[17px]" data-testid="second-file-note">
          {t("upload.secondFile")}
        </p>
      )}
      {/* one thing first: the file; what to film in three plain lines (UX test H05) */}
      <ul className="m-0 list-none space-y-1.5 p-0 text-[17px]" data-testid="upload-tips">
        <li>{t("upload.tip1")}</li>
        <li>{t("upload.tip2")}</li>
        <li>{t("upload.tip3")}</li>
      </ul>
      {/* the guide on the website, its address from the configuration */}
      {site && <a href={sitePage(site.site_url, locale, "aufnahme/")} target="_blank" rel="noreferrer" className="inline-flex min-h-11 items-center text-[17px] font-bold text-ink underline decoration-[1.5px] underline-offset-4">
        {t("upload.guide")}
      </a>}
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
          type="file"
          accept="video/*,.mts,.m2ts,.mkv"
          multiple={role === "main"}
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
        <div className="space-y-2" role="status">
          <div className="h-2 overflow-hidden bg-surface">
            <div className="h-full bg-accent transition-all" style={{ width: `${pct}%` }} />
          </div>
          <p className="text-sm tabular-nums" data-testid="upload-progress">
            {t("upload.progress", { percent: pct, done: formatBytes(state.done), total: formatBytes(state.file.size) })}
          </p>
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
        <Alert kind="info">
          <span className="block">{t("upload.paused")}</span>
          <Button variant="secondary" className="mt-2" onClick={() => resume(state.file)}>
            {t("upload.resume")}
          </Button>
        </Alert>
      )}
      {state.kind === "done" && (
        // the reassurance the coach needs on the phone (UX test H05, Z4)
        <Alert kind="success" data-testid="upload-done">
          <span className="block font-bold">{t("upload.done")}</span>
          <span className="block">{t("upload.mayClose")}</span>
        </Alert>
      )}
      {state.kind === "same" && (
        <Alert kind="info" data-testid="upload-same">
          {t("upload.queueSame")}
        </Alert>
      )}
      {state.kind === "error" && (
        <Alert>
          {state.error === "notVideo" ? (
            <>
              <span className="block font-bold">{t("processing.failedTitle")}</span>
              <span className="block">{t("upload.notVideo")}</span>
            </>
          ) : (
            <span className="block">{state.error === "upload" ? t("upload.failed") : t(`errors.${state.error}`)}</span>
          )}
          {state.file && (
            <Button variant="secondary" className="mt-2" onClick={() => resume(state.file!)}>
              {t("upload.resume")}
            </Button>
          )}
        </Alert>
      )}
      {/* the rest can wait: another camera, a link, the technical details */}
      <details className="text-[15px]">
        <summary className="min-h-11 cursor-pointer content-center font-semibold">{t("upload.more")}</summary>
        <div className="mt-3 space-y-5">
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
