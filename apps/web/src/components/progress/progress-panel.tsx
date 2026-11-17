"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useNow, useTranslations } from "next-intl";
import { useState, type ReactNode } from "react";
import { Button, buttonClass } from "@/components/ui/button";
import { api } from "@/lib/client";
import { formatBytes } from "@/lib/format";
import { STEPS, isActive, progressKey, stepState, tone, type FileProgress, type MatchProgress } from "@/lib/progress";
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
  onOtherFile,
  onResumeUpload,
  aside,
}: {
  orgId: string;
  progress: MatchProgress;
  staff: boolean;
  onOtherFile?: () => void;
  onResumeUpload?: () => void;
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
              {/* in trouble: how far the step that holds got («Hochladen: 2 %»), not the whole way */}
              {trouble ? `${t(`step_${trouble.stage}`)}: ${w.percent(trouble.fraction ?? 0)}` : (when ?? t("noEta"))}
            </p>
            {when && (
              <p className="m-0 text-[15px] text-ink-2">
                {/* the clock time above, the time left here (a finish tomorrow is easier to read so) */}
                {p.eta_s != null && p.stage !== "upload" ? `${w.left(p.eta_s)} · ` : ""}
                {basis ? t(basis === "history" ? "basisHistory" : "basisMeasured") : ""}
              </p>
            )}
            <div className="mt-3 h-1.5 bg-rule" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.floor(p.overall * 100)} aria-label={w.headline(p)}>
              <div className="h-full bg-ink transition-[width] duration-700" style={{ width: `${Math.max(2, p.overall * 100)}%` }} />
            </div>
          </>
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
    return (
      <div className="mt-2 space-y-2" role="alert" data-testid="progress-failed">
        <p className={cn(base, "mt-0 text-[17px]")}>{t(f.stage === "analysis" ? "failedAnalysis" : f.stage === "upload" ? "failedUpload" : "failedIngest")}</p>
        {staff && f.stage === "analysis" && (
          <Button size="sm" onClick={() => void retry()} loading={busy}>
            {t("retryAnalysis")}
          </Button>
        )}
        {staff && f.stage !== "analysis" && onOtherFile && (
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
  const parts = [
    f.fraction != null ? w.percent(f.fraction) : null,
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
