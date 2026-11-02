"use client";

import { useTranslations } from "next-intl";
import { useEffect, useRef, useState, type DragEvent, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Alert, Card } from "@/components/ui/card";
import { Input, Select } from "@/components/ui/field";
import { api } from "@/lib/client";
import { errorKey, type ErrorKey } from "@/lib/errors";
import { formatBytes } from "@/lib/format";
import { localStore, uploadFile, UploadAbortedError, xhrPutPart, type UploadApi } from "@/lib/upload";

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
  | { kind: "paused" }
  | { kind: "done" }
  | { kind: "error"; error: ErrorKey | "upload" };

export function UploadPanel({ orgId, matchId, onUploaded }: { orgId: string; matchId: string; onUploaded: () => void }) {
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

  async function start(file: File) {
    ctrl.current = new AbortController();
    setState({ kind: "uploading", file, done: 0, resumed: false });
    try {
      await uploadFile(file, role, {
        api: apiFor(orgId, matchId),
        store: localStore,
        putPart: xhrPutPart,
        scope: `${matchId}:${role}`,
        signal: ctrl.current.signal,
        onProgress: (done) => setState((s) => (s.kind === "uploading" ? { ...s, done } : s)),
      });
      setState({ kind: "done" });
      onUploaded();
    } catch (e) {
      if (e instanceof UploadAbortedError) setState({ kind: "paused" });
      else setState({ kind: "error", error: e && typeof e === "object" && "status" in e ? errorKey(e) : "upload" });
    }
  }

  function onDrop(e: DragEvent) {
    e.preventDefault();
    setDrag(false);
    const file = e.dataTransfer.files[0];
    if (file && !uploading) void start(file);
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

  const pct = state.kind === "uploading" ? Math.floor((state.done / state.file.size) * 100) : 0;
  return (
    <Card className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <h2 className="text-lg font-semibold">{t("upload.title")}</h2>
        <div className="w-56">
          <Select label={t("upload.role")} value={role} onChange={(e) => setRole(e.target.value as Role)} disabled={uploading}>
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {t(`upload.role_${r}`)}
              </option>
            ))}
          </Select>
        </div>
      </div>
      <label
        onDragOver={(e) => {
          e.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={onDrop}
        className={`flex min-h-32 cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-6 text-center ${drag ? "border-accent bg-surface" : "border-border"}`}
      >
        <span className="font-medium">{t("upload.drop")}</span>
        <span className="text-sm text-accent underline underline-offset-4">{t("upload.choose")}</span>
        <input
          type="file"
          accept="video/*,.mts,.m2ts,.mkv"
          className="sr-only"
          data-testid="video-file"
          disabled={uploading}
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) void start(f);
            e.target.value = "";
          }}
        />
      </label>
      {state.kind === "uploading" && (
        <div className="space-y-2" role="status">
          <div className="h-2 overflow-hidden rounded bg-surface">
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
      {state.kind === "paused" && <Alert kind="info">{t("upload.paused")}</Alert>}
      {state.kind === "done" && <Alert kind="success">{t("upload.done")}</Alert>}
      {state.kind === "error" && (
        <Alert>{state.error === "upload" ? t("upload.failed") : t(`errors.${state.error}`)}</Alert>
      )}
      <details className="text-sm">
        <summary className="cursor-pointer text-muted">{t("upload.link")}</summary>
        <form onSubmit={importLink} className="mt-3 flex flex-wrap items-end gap-2">
          <div className="min-w-64 flex-1">
            <Input label={t("upload.linkLabel")} name="url" type="url" required pattern="https://.*" hint={t("upload.linkHint")} />
          </div>
          <Button type="submit" variant="secondary">
            {t("upload.import")}
          </Button>
        </form>
        {linkMsg && <p className="mt-2 text-ok">{linkMsg}</p>}
        {linkError && <Alert className="mt-2">{t(`errors.${linkError}`)}</Alert>}
      </details>
      <details className="text-sm">
        <summary className="cursor-pointer text-muted">{t("upload.tipsTitle")}</summary>
        <p className="mt-2">{t("upload.tips")}</p>
      </details>
    </Card>
  );
}
