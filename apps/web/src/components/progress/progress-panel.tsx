"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useNow, useTranslations } from "next-intl";
import { useState, type ReactNode } from "react";
import { AnalysisNotice } from "@/components/analysis/analysis-notice";
import { Button, buttonClass } from "@/components/ui/button";
import { useConfirm } from "@/components/ui/confirm";
import { api } from "@/lib/client";
import { formatBytes } from "@/lib/format";
import { STEPS, barValue, fileActions, filesLine, isActive, progressKey, stepState, tone, type FileProgress, type MatchProgress } from "@/lib/progress";
import { storedUploadIds } from "@/lib/upload";
import { stopLocalUpload, useLocalUploads } from "@/lib/upload-store";
import { cn } from "@/lib/utils";
import { useProgressWords } from "./words";

/**
 * The progress block of a match (K13, B4, SPEC 7.13 «Analyse läuft»): the step of each file
 * (hochladen, einlesen, analysieren, fertig), how far, until when (or the step when that cannot
 * be told yet), whether it still moves and what happens next if not, what fails and the way on.
 * `aside` is what the coach can look at or do meanwhile (the match page fills it).
 */
export function ProgressPanel({
  orgId,
  progress,
  staff,
  canDelete = staff,
  onOtherFile,
  onResumeUpload,
  onRemoved,
  onMarkCourt,
  aside,
}: {
  orgId: string;
  progress: MatchProgress;
  staff: boolean;
  /** removing a file that arrived is the staff's (players upload, they do not delete: K18) */
  canDelete?: boolean;
  onOtherFile?: () => void;
  onResumeUpload?: () => void;
  onRemoved?: () => void;
  /** the hall image of the running analysis is there: open the court marking (#141) */
  onMarkCourt?: () => void;
  aside?: ReactNode;
}) {
  const w = useProgressWords();
  const t = useTranslations("progress");
  const now = useNow({ updateInterval: 15_000 }).getTime();
  const p = progress;
  const when = w.when(p, now);
  const tn = tone(p);
  const many = p.files.length > 1;
  const basis = p.files.find((f) => f.stage === p.stage && isActive(f))?.eta_basis;
  const trouble = p.files.find((f) => f.state === "stalled" || f.state === "interrupted");
  // one line that sums up every file, never one file's step for all of them (second round A2)
  const summary = many ? filesLine(p.files) : null;
  const bar = barValue(p);
  // marking the court while the analysis runs: that run takes it, no second run (#141)
  const court = staff && isActive(p) ? (p.files.some((f) => f.court === "mark") ? "mark" : p.files.some((f) => f.court === "taken") ? "taken" : null) : null;
  return (
    <section
      className={cn("grid gap-8", aside && "md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]")}
      aria-labelledby="progress-title"
      data-testid="progress-panel"
      data-state={p.state}
      data-stage={p.stage}
    >
      <div className={cn("min-w-0", tn === "attn" && "border-l-4 border-attn pl-4", tn === "fail" && "border-l-4 border-loss pl-4")}>
        <h2 id="progress-title" className="text-[26px]">
          {w.headline(p)}
        </h2>
        {isActive(p) && (
          <>
            <p className="m-0 mt-1 text-[19px] font-bold" aria-live="polite" data-testid="progress-when">
              {/* several files: what each does, in one line (the files below say more); one file
                  in trouble: how far its step got; otherwise until when */}
              {summary
                ? t("filesSummary", { n: p.files.length, list: summary.map((x) => t(`fileState_${x.word}`, { n: x.n })).join(", ") })
                : trouble
                  ? `${t(`step_${trouble.stage}`)}: ${w.percent(trouble.fraction ?? 0)}`
                  : // the same figure as the strip on every page: the whole way, then the time (BUG-16)
                    `${w.percent(p.overall)} · ${when ?? t("noEta")}`}
            </p>
            {when && !trouble && (
              <p className="m-0 text-[15px] text-ink-2">
                {/* the clock time above, the time left here (a finish tomorrow is easier to read so) */}
                {p.eta_s != null && p.stage !== "upload" ? `${w.left(p.eta_s)} · ` : ""}
                {basis ? t(basis === "history" ? "basisHistory" : "basisMeasured") : ""}
              </p>
            )}
            {/* the bar goes with the line above: the upload while uploading, else the whole way;
                none while something holds (it would promise a progress that does not happen) */}
            {bar != null && (
              <div className="mt-3 h-1.5 bg-rule" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.floor(bar * 100)} aria-label={w.headline(p)}>
                <div className="h-full bg-ink transition-[width] duration-700" style={{ width: `${Math.max(2, bar * 100)}%` }} />
              </div>
            )}
          </>
        )}
        {court === "mark" && onMarkCourt && (
          <div className="mt-5 border-l-4 border-attn py-1 pl-4" role="status" data-testid="progress-court">
            <p className="m-0 text-[19px] font-bold">{t("courtTitle")}</p>
            <p className="m-0 mt-1 max-w-[60ch] text-[15px]">{t("courtText")}</p>
            <Button className="mt-3 max-sm:w-full" onClick={onMarkCourt} data-testid="progress-mark-court">
              {t("courtButton")}
            </Button>
          </div>
        )}
        {court === "taken" && (
          <p className="m-0 mt-4 max-w-[60ch] text-[15px] font-bold" role="status" data-testid="progress-court-taken">
            {t("courtTaken")}
          </p>
        )}
        {!isActive(p) && summary && (
          <p className="m-0 mt-1 text-[19px] font-bold" data-testid="progress-when">
            {t("filesSummary", { n: p.files.length, list: summary.map((x) => t(`fileState_${x.word}`, { n: x.n })).join(", ") })}
          </p>
        )}
        <ol className="m-0 mt-4 list-none space-y-5 p-0">
          {p.files.map((f) => (
            <li key={f.video_id} data-testid="progress-file" data-stage={f.stage} data-state={f.state}>
              {many && (
                <p className="m-0 mb-1.5 truncate text-[17px] font-bold" title={f.filename}>
                  {w.fileName(f, p.files)}
                </p>
              )}
              <Steps f={f} />
              <FileNote f={f} files={p.files} orgId={orgId} staff={staff} now={now} onOtherFile={onOtherFile} onResumeUpload={onResumeUpload} />
              <FileActions f={f} name={w.fileName(f, p.files)} orgId={orgId} staff={staff} canDelete={canDelete} onRemoved={onRemoved} />
            </li>
          ))}
        </ol>
        {/* a stopped upload does not go on by itself: no «läuft von selbst weiter» then */}
        {/* nor while a file is still being sent from the browser: closing the window stops it (the
            upload panel says so) */}
        {isActive(p) && p.state !== "interrupted" && p.stage !== "upload" && <p className="m-0 mt-4 max-w-[60ch] text-[15px] text-ink-2" data-testid="may-close">{t("mayClose")}</p>}
      </div>
      {aside && <div className="min-w-0 space-y-8">{aside}</div>}
    </section>
  );
}

/** The four steps of a file in one row: done, now (with how far), next. */
function Steps({ f }: { f: FileProgress }) {
  const t = useTranslations("progress");
  // another camera is not analysed: three steps
  const steps = STEPS.filter((s) => s !== "analysis" || f.role === "main");
  return (
    <ol className="m-0 grid list-none gap-1 p-0" style={{ gridTemplateColumns: `repeat(${steps.length}, minmax(0, 1fr))` }} aria-label={t("stepsLabel")}>
      {steps.map((s) => {
        const st = stepState(f, s);
        const trouble = st === "now" && (f.state === "stalled" || f.state === "interrupted" || f.state === "failed");
        return (
          <li key={s} className="min-w-0" aria-current={st === "now" ? "step" : undefined}>
            <span className={cn("block h-1.5", st === "done" ? "bg-win" : st === "now" ? (trouble && f.state === "failed" ? "bg-loss" : "bg-ink") : "bg-rule")} aria-hidden />
            <span className={cn("mt-1 block truncate text-[15px]", st === "next" ? "text-ink-2" : "font-bold")}>
              {t(`step_${s}`)}
              <span className="sr-only">
                {": "}
                {t(st === "done" ? "stDone" : st === "now" ? (s === "done" ? "stDone" : "stNow") : "stNext")}
              </span>
            </span>
          </li>
        );
      })}
    </ol>
  );
}

/** One sentence on the file's step: how far and until when, or what holds it and what happens. */
function FileNote({
  f,
  files,
  orgId,
  staff,
  now,
  onOtherFile,
  onResumeUpload,
}: {
  f: FileProgress;
  files: FileProgress[];
  orgId: string;
  staff: boolean;
  now: number;
  onOtherFile?: () => void;
  onResumeUpload?: () => void;
}) {
  const w = useProgressWords();
  const t = useTranslations("progress");
  const qc = useQueryClient();
  const [busy, setBusy] = useState(false);
  const minutes = (s: number | null | undefined) => Math.max(1, Math.round((s ?? 0) / 60));
  const base = "m-0 mt-2 max-w-[62ch] text-[15px]";
  if (f.state === "done") return null;
  if (f.state === "failed") {
    const retry = async () => {
      setBusy(true);
      await api.POST("/v1/orgs/{org_id}/videos/{video_id}/analysis", { params: { path: { org_id: orgId, video_id: f.video_id } } });
      setBusy(false);
      void qc.invalidateQueries({ queryKey: progressKey(orgId) });
      void qc.invalidateQueries({ queryKey: ["match"] });
    };
    // the reason in the coach's words and what helps (second round A3); «Analyse neu starten»
    // only where it can help (not after a timeout on the same file)
    const reason = f.stage === "analysis" || (f.stage === "ingest" && f.error && f.error !== "generic") ? f.error : null;
    return (
      <div className="mt-2 space-y-2" role="alert" data-testid="progress-failed" data-error={f.error ?? undefined}>
        {reason ? (
          <AnalysisNotice notice={{ reason, failed: true, duration_s: f.duration_s, limit_s: f.limit_s }} className="mt-3" plain testId="progress-failed-reason" />
        ) : (
          <p className={cn(base, "mt-0 text-[17px]")}>{t(f.stage === "upload" ? (f.error === "abandoned" ? "failedAbandoned" : "failedUpload") : "failedIngest")}</p>
        )}
        {staff && f.stage === "analysis" && f.retry !== false && (
          <Button size="sm" onClick={() => void retry()} loading={busy} data-testid="progress-retry">
            {t("retryAnalysis")}
          </Button>
        )}
        {staff && f.stage !== "analysis" && f.error !== "abandoned" && onOtherFile && (
          <button type="button" className={buttonClass("primary", "sm")} onClick={onOtherFile}>
            {t("otherFile")}
          </button>
        )}
      </div>
    );
  }
  if (f.state === "stalled") {
    return (
      <div className="mt-2 space-y-1" data-testid="progress-stalled">
        <p className={cn(base, "mt-0 font-bold")}>{t("stalledText", { m: minutes(f.idle_s) })}</p>
        {f.restart_at && <p className={cn(base, "mt-0")}>{t(f.restarted ? "stalledNextLast" : "stalledNext", { time: w.clock(new Date(f.restart_at)) })}</p>}
      </div>
    );
  }
  if (f.state === "interrupted") {
    return (
      <div className="mt-2 space-y-2" data-testid="progress-interrupted">
        <p className={cn(base, "mt-0")}>
          {f.uploaded_bytes != null
            ? t("interruptedText", {
                m: minutes(f.idle_s),
                done: formatBytes(f.uploaded_bytes),
                total: formatBytes(f.size_bytes ?? 0),
              })
            : t("interruptedTextNoBytes", { m: minutes(f.idle_s) })}
        </p>
        {staff && onResumeUpload && (
          <button type="button" className={buttonClass("primary", "sm")} onClick={onResumeUpload}>
            {t("resumeUpload")}
          </button>
        )}
      </div>
    );
  }
  if (f.state === "waiting") {
    const before = files.find((x) => x.part != null && f.part != null && x.part === f.part - 1);
    return (
      <p className={base}>
        {t("waitingPart", { name: before ? w.fileName(before, files) : t("earlierPart") })}
        {f.finish_s != null && files.some((x) => x.state === "running" && x.finish_s != null) ? ` ${t("waitingThen")}` : ""}
      </p>
    );
  }
  if (f.state === "queued") {
    return (
      <p className={base}>
        {f.idle_s != null ? t("queuedLong", { m: minutes(f.idle_s) }) : t("queued")}
        {f.eta_s != null ? ` ${t("thenTakes", { left: w.left(f.eta_s) })}` : ""}
      </p>
    );
  }
  // running
  // the step's own share, named as such: the figure of the whole way stands above (BUG-16)
  const parts = [
    f.fraction != null ? t("stepShare", { n: Math.floor(f.fraction * 100) }) : null,
    f.stage === "upload" && f.uploaded_bytes != null && f.size_bytes ? t("bytesOf", { done: formatBytes(f.uploaded_bytes), total: formatBytes(f.size_bytes) }) : null,
    f.eta_s != null ? w.left(f.eta_s) : t("stepRuns"),
  ].filter(Boolean);
  void now;
  return (
    <p className={base}>
      <b>{t(`step_${f.stage}`)}:</b> {parts.join(" · ")}
      {f.stage === "ingest" && <span className="block text-ink-2">{t("explainIngest")}</span>}
      {f.stage === "analysis" && f.step && <span className="block text-ink-2">{t.has(`sub_${f.step}`) ? t(`sub_${f.step}` as "sub_observe") : null}</span>}
    </p>
  );
}

/**
 * What can be done with one file (second round A1): «Upload abbrechen» while it is uploaded or
 * stuck (whoever uploads may cancel a running upload; the staff any), «Datei entfernen» once it
 * arrived or failed (the staff only, K18). Always asked first; also with a single file.
 */
function FileActions({ f, name, orgId, staff, canDelete, onRemoved }: { f: FileProgress; name: string; orgId: string; staff: boolean; canDelete: boolean; onRemoved?: () => void }) {
  const t = useTranslations("progress");
  const qc = useQueryClient();
  const confirm = useConfirm();
  const local = useLocalUploads();
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  // an upload this browser started (running here or remembered to resume): the uploader's own
  const own = local.some((u) => u.videoId === f.video_id) || (typeof window !== "undefined" && storedUploadIds().has(f.video_id));
  const action = fileActions(f, { staff, canDelete, own });
  if (!action) return null;
  const cancel = action === "cancel";
  async function run() {
    const ok = await confirm({
      title: t(cancel ? "cancelTitle" : "removeTitle", { name }),
      body: t(cancel ? "cancelBody" : "removeBody"),
      confirm: t(cancel ? "cancelUpload" : "removeFile"),
      danger: true,
    });
    if (!ok) return;
    setBusy(true);
    setFailed(false);
    stopLocalUpload(f.video_id);
    const r = await api.DELETE("/v1/orgs/{org_id}/videos/{video_id}", { params: { path: { org_id: orgId, video_id: f.video_id } } });
    setBusy(false);
    if (r.error || !r.response.ok) return setFailed(true);
    void qc.invalidateQueries({ queryKey: progressKey(orgId) });
    void qc.invalidateQueries({ queryKey: ["match"] });
    void qc.invalidateQueries({ queryKey: ["graphics"] });
    onRemoved?.();
  }
  return (
    <div className="mt-2 flex flex-wrap items-center gap-3">
      <Button size="sm" variant="secondary" onClick={() => void run()} loading={busy} data-testid={cancel ? "progress-cancel-upload" : "progress-remove-file"} aria-label={`${t(cancel ? "cancelUpload" : "removeFile")}: ${name}`}>
        {t(cancel ? "cancelUpload" : "removeFile")}
      </Button>
      {failed && (
        <span role="alert" className="text-[15px] font-bold">
          {t("removeFailed")}
        </span>
      )}
    </div>
  );
}
