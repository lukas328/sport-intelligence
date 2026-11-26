"use client";

import type { Schemas } from "@handball/api-client";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useFormatter, useTranslations } from "next-intl";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { CourtCalibration, CourtPreview } from "@/components/analysis/court-calibration";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/card";
import { MiniCourt } from "@/components/video/mini-court";
import { track } from "@/lib/analytics";
import { api } from "@/lib/client";
import { courtFromHall, courtFromHallSure, courtUnconfirmed } from "@/lib/match-workflow";
import { cn } from "@/lib/utils";

export type Analysis = Schemas["AnalysisOut"];

/** The court step: the analysis state, the court check and the mini court. */
export function AnalysisPanel({
  analysis,
  orgId,
  videoId,
  colours,
  getTime,
  canCalibrate,
  onConfirmed,
  openMark = null,
}: {
  analysis: Analysis | null;
  orgId: string;
  videoId: string;
  colours: Record<string, string>;
  getTime: () => number;
  canCalibrate: boolean;
  onConfirmed?: () => void;
  /** the marking asked for from outside (the progress «Spielfeld markieren»); a new object each time */
  openMark?: { n: number } | null;
}) {
  const t = useTranslations("analysis");
  const format = useFormatter();
  // the court dialog; «Neu markieren» beside the court preview goes straight to the lines
  const [marking, setMarking] = useState<false | "suggest" | "mark">(false);
  const qc = useQueryClient();
  const confirm = useMutation({
    mutationFn: async () => {
      const { error } = await api.POST("/v1/orgs/{org_id}/videos/{video_id}/calibration/confirm", {
        params: { path: { org_id: orgId, video_id: videoId } },
      });
      if (error) throw new Error("confirm");
    },
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["analysis", videoId] });
      onConfirmed?.();
    },
  });
  const confirmCourt = () => confirm.mutate();
  const confirming = confirm.isPending;
  const confirmFailed = confirm.isError;
  const ready = analysis?.status === "ready";
  useEffect(() => {
    if (ready) track("analysis_viewed");
  }, [ready]);
  // «Spielfeld markieren» from the progress or the strip opens the dialog here once it can open
  // (the analysis and its hall image may come a moment after the workbench)
  const markable = Boolean(
    canCalibrate &&
      analysis?.panorama != null &&
      (analysis.status === "ready" ||
        (analysis.status === "running" && analysis.calibration_state !== "updating" && analysis.calibration_state !== "confirmed")),
  );
  const handledMark = useRef<number | null>(null);
  useEffect(() => {
    if (!openMark || handledMark.current === openMark.n || !markable) return;
    handledMark.current = openMark.n;
    setMarking("suggest");
  }, [openMark, markable]);
  if (!analysis || analysis.status === "none") return null;
  const canMark = canCalibrate && analysis.status === "ready" && analysis.panorama != null;
  // the hall image comes early in the run: the court is marked while the analysis goes on and
  // that run takes it, no second run afterwards
  const markEarly =
    canCalibrate &&
    analysis.status === "running" &&
    analysis.panorama != null &&
    analysis.calibration_state !== "updating" &&
    analysis.calibration_state !== "confirmed";
  const unconfirmed = courtUnconfirmed(analysis);
  const courtState = analysis.calibration_state;
  const info = (analysis.calibration_info ?? {}) as { reason?: string; method?: string };
  const REASONS = ["camera_motion", "no_floor", "flat_view", "few_people", "court"] as const;
  const reason = REASONS.find((r) => r === info.reason) ?? (analysis.needs_calibration && analysis.calibration_error ? "court" : null);
  const hallName = analysis.hall?.name ?? null;
  const fromHall = courtFromHall(analysis);
  const hallCheck = canMark && fromHall && unconfirmed && courtState !== "undeterminable";
  const hallConfirmed = fromHall && analysis.calibration?.source === "user_correction";
  const hallSure = !hallConfirmed && courtFromHallSure(analysis);
  // a confirmed court carried over from an earlier match of the hall: say where it came from,
  // with the realign button beside it (while the court waits for its check, that check says it)
  const origin = !hallCheck && analysis.calibration_origin?.source === "hall" ? analysis.calibration_origin : null;
  const markButton = canMark && !hallCheck && (
    <Button
      variant={analysis.needs_calibration ? "primary" : "secondary"}
      size={analysis.needs_calibration || unconfirmed ? "md" : "sm"}
      onClick={() => setMarking("suggest")}
      data-testid="mark-court"
    >
      {t(courtState === "undeterminable" ? "courtMarkAnyway" : analysis.needs_calibration ? "markCourt" : unconfirmed ? "checkCourtButton" : "realign")}
    </Button>
  );
  return (
    // while the court waits for its check the answer bar is fixed on phones: room for it at the end
    <section className={cn("space-y-3", hallCheck && "max-lg:pb-24")} data-testid="analysis-panel">
      <h2 className="sr-only">{t("title")}</h2>
      {analysis.status === "running" &&
        (markEarly ? (
          // the one thing to do while the analysis runs: in the signal colour of an open step
          <div className="flex flex-wrap items-center gap-x-3 gap-y-2 border-l-4 border-attn pl-4" data-testid="mark-early">
            <p className="min-w-0 flex-[1_1_16rem] text-[15px] font-semibold">{t("runningMark")}</p>
            <Button className="max-sm:w-full" onClick={() => setMarking("suggest")} data-testid="mark-court">
              {t("markCourt")}
            </Button>
          </div>
        ) : (
          <p className="text-sm">{t(analysis.calibration_state === "updating" ? "courtUpdating" : "running")}</p>
        ))}
      {analysis.status === "failed" && (
        <Alert>
          <span className="block font-medium">{t(`failure_${analysis.error_code ?? "generic"}` as "failure_generic")}</span>
          <span className="block">{t(`failureNext_${analysis.error_code ?? "generic"}` as "failureNext_generic")}</span>
          <span className="block text-xs">{t("failureCredit")}</span>
        </Alert>
      )}
      {analysis.status === "ready" && analysis.needs_calibration && courtState !== "undeterminable" && (
        <Alert kind="info">
          {t(canMark ? "needsCalibration" : "needsCalibrationStaff")}
          {/* why the automatic court failed, in the coach's words (ADR 025: a reason code) */}
          {reason && <span className="mt-1 block text-muted">{t(`calibReason_${reason}`)}</span>}
        </Alert>
      )}
      {/* one sentence: does the court fit (the coach said it cannot be set, or it is being applied) */}
      {analysis.status === "ready" && (courtState === "undeterminable" || courtState === "updating") ? (
        <p className="text-[0.9375rem]" data-testid="court-state">
          {t(courtState === "undeterminable" ? "courtUndeterminable" : "courtUpdating")}
        </p>
      ) : analysis.status === "ready" && !analysis.needs_calibration && origin ? (
        <div className="flex flex-wrap items-center gap-x-3 gap-y-2" data-testid="court-origin">
          <p className="min-w-0 flex-[1_1_16rem] text-[0.9375rem]">
            {t.rich(origin.hall ? (origin.reference_kickoff_at ? "courtOriginHall" : "courtOriginHallNoDate") : origin.reference_kickoff_at ? "courtOriginNoName" : "courtOriginNoNameNoDate", {
              hall: origin.hall ?? "",
              date: origin.reference_kickoff_at ? format.dateTime(new Date(origin.reference_kickoff_at), { day: "numeric", month: "short" }) : "",
              link: (chunks) =>
                origin.reference_match_id ? (
                  <Link href={`/app/${orgId}/matches/${origin.reference_match_id}`} className="underline underline-offset-4">
                    {chunks}
                  </Link>
                ) : (
                  chunks
                ),
            })}
            {canMark && ` ${t("courtOriginRealign")}`}
          </p>
          {markButton}
        </div>
      ) : analysis.status === "ready" && !analysis.needs_calibration ? (
        <p className="text-[0.9375rem]">
          {fromHall
            ? hallSure
              ? t("courtFromHallSure")
              : t(hallConfirmed ? "courtFromHallOk" : hallCheck ? "courtFromHallCheck" : "courtFromHall", { hall: hallName ?? "" })
            : unconfirmed
              ? t("checkCourt")
              : t("courtOk")}
        </p>
      ) : null}
      {/* a court from the hall is checked here in one look, not in the marking dialog */}
      {hallCheck && <CourtPreview orgId={orgId} videoId={videoId} analysis={analysis} alt={t("courtPreviewAlt")} />}
      {/* a court marked once is carried over to the next videos of the same hall */}
      {canMark && !fromHall && (analysis.needs_calibration || unconfirmed) && (
        <p className="text-xs text-muted" data-testid="hall-hint">
          {hallName ? t("hallOnce", { hall: hallName }) : t("hallUnknown")}
        </p>
      )}
      {hallCheck ? (
        // phones: the one answer waits in the thumb zone above the bottom navigation, wherever the
        // page is scrolled, until the court is checked
        <div className="flex flex-wrap gap-2 max-lg:fixed max-lg:inset-x-0 max-lg:bottom-[calc(4.25rem+env(safe-area-inset-bottom))] max-lg:z-20 max-lg:border-t max-lg:border-foreground/15 max-lg:bg-background max-lg:px-4 max-lg:py-3 max-lg:[&>*]:flex-1">
          <Button onClick={confirmCourt} loading={confirming} data-testid="court-confirm">
            {t("courtFits")}
          </Button>
          <Button variant="secondary" onClick={() => setMarking("mark")} data-testid="mark-court">
            {t("courtRemark")}
          </Button>
        </div>
      ) : (
        !origin && markButton
      )}
      {confirmFailed && <Alert className="py-2">{t("courtConfirmError")}</Alert>}
      {marking && <CourtCalibration orgId={orgId} videoId={videoId} analysis={analysis} start={marking} onClose={() => setMarking(false)} />}
      {/* no positions on a court the coach said cannot be set */}
      {courtState !== "undeterminable" && analysis.chunks != null && analysis.chunk_ms != null && analysis.chunks > 0 && (
        <MiniCourt
          baseUrl={`/v1/orgs/${orgId}/videos/${videoId}/tracks`}
          chunkMs={analysis.chunk_ms}
          chunks={analysis.chunks}
          tracks={analysis.tracks}
          colours={colours}
          getTime={getTime}
          label={t("title")}
        />
      )}
      {/* the legend of the mini court: nothing to explain without it */}
      {courtState !== "undeterminable" && analysis.chunks != null && analysis.chunks > 0 && (
        <div className="flex flex-wrap gap-3 text-xs text-muted">
          {(["home", "away", "referee"] as const).map((k) => (
            <span key={k} className="flex items-center gap-1">
              <span aria-hidden className="inline-block size-3 rounded-full ring-1 ring-foreground/50" style={{ background: colours[k] }} />
              {t(k)}
            </span>
          ))}
        </div>
      )}
      {/* what the analysis did, for those who want to know; not a coach's task */}
      <details className="text-xs text-muted">
        <summary className="cursor-pointer hover:text-foreground">{t("technical")}</summary>
        <div className="mt-2 space-y-1.5">
          {analysis.detector === "heuristic" && <p title={t("heuristicHint")}>{t("heuristic")}</p>}
          {analysis.auto_events && (
            <p data-testid="auto-events">
              {(analysis.auto_events.missing as string[] | undefined)?.includes("goalkeepers")
                ? t("autoNoGoalkeepers")
                : t("autoSummary", { events: Number(analysis.auto_events.events ?? 0), possessions: Number(analysis.auto_events.possessions ?? 0) })}{" "}
              {t("autoLimits")}
              {(analysis.auto_events.missing as string[] | undefined)?.includes("throw_offs") && (
                <span className="block" data-testid="no-throw-offs">
                  {t("autoNoThrowOffs")}
                </span>
              )}
              {Number(analysis.auto_events.overlay_goals ?? 0) > 0 && (
                <span className="block" data-testid="overlay-goals">
                  {t("autoOverlay", { goals: Number(analysis.auto_events.overlay_goals) })}
                </span>
              )}
            </p>
          )}
          {analysis.calibration && (
            <p>
              {t("calibration")}: {t(`calibration_${analysis.calibration.source as "heuristic"}`)},{" "}
              {/* the automatic court's error is not measured yet (reprojection 0): no «100 %»,
                  the court is asked in Prüfen (real-video test, Q-CAL-QUALITY) */}
              {analysis.calibration.source !== "user_correction" && !analysis.calibration.reprojection_px ? t("confidenceUnmeasured") : t("confidence", { value: Math.round(analysis.calibration.confidence * 100) })}
            </p>
          )}
          {analysis.tracks.length > 0 && <p>{t("tracks", { count: analysis.tracks.length })}</p>}
        </div>
      </details>
    </section>
  );
}
