"use client";

import type { Schemas } from "@handball/api-client";
import { COURT, type Point } from "@handball/court";
import { useQueryClient } from "@tanstack/react-query";
import { Eraser, Magnet, Minus, Plus, Scan, Undo2, X } from "lucide-react";
import { useFormatter, useTranslations } from "next-intl";
import { useCallback, useEffect, useMemo, useReducer, useRef, useState } from "react";
import { createPortal } from "react-dom";
import {
  CalibrationStage,
  type OverlayTone,
  type StageHandle,
} from "@/components/analysis/calibration-stage";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/card";
import {
  calibrationState,
  checkClicks,
  confirmCourt,
  droppedRefs,
  lastClicks,
  fetchCourtModel,
  markUndeterminable,
  saveCourt,
  suggestionOf,
  type ClickProblem,
  type Outcome,
  type ServerFit,
  type UndeterminableReason,
} from "@/lib/calibration-api";
import { countOn, flowReducer, initialFlow, offeredLine } from "@/lib/calibration-flow";
import { courtPolylines } from "@/lib/court-calibration";
import {
  LINE_NAMES,
  LOCAL_COURT_MODEL,
  MAX_MEDIAN_PX,
  MIN_EQUATIONS,
  PREVIEW_EQUATIONS,
  POINT_NAMES,
  fitClicks,
  type ClickFit,
  type ClickRef,
  type Clicks,
  type CourtModel,
  type LineName,
  type PointName,
  type Pt,
} from "@/lib/court-fit";
import type { Homography } from "@/lib/spotlight";
import { cn } from "@/lib/utils";

type Analysis = Schemas["AnalysisOut"];

const flipY = (y: number) => COURT.width - y;
const courtPath = (pts: readonly Point[]) =>
  pts.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x} ${flipY(y)}`).join(" ");
const imagePath = (pts: Pt[]) =>
  pts.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)} ${y.toFixed(1)}`).join(" ");
const keyOf = (c: Clicks) => JSON.stringify(c);

/** The small court on a chip, the chosen line or point drawn strong. */
function MiniCourt({ line, point, className }: { line?: string; point?: Pt; className?: string }) {
  const l = line ? LOCAL_COURT_MODEL.lines[line] : undefined;
  return (
    <svg viewBox="-1.5 -1.5 43 23" className={cn("h-[22px] w-11 shrink-0", className)} aria-hidden>
      <rect x={-1.5} y={-1.5} width={43} height={23} fill="var(--court)" />
      {Object.entries(COURT.lines).map(([name, pts]) => (
        <path
          key={name}
          d={courtPath(pts)}
          fill="none"
          stroke="var(--court-text)"
          strokeOpacity={0.55}
          strokeWidth={0.5}
        />
      ))}
      {l && <path d={courtPath(l.court)} fill="none" stroke="var(--attn)" strokeWidth={2.2} />}
      {point && (
        <circle
          cx={point[0]}
          cy={flipY(point[1])}
          r={2.2}
          fill="var(--attn)"
          stroke="var(--court)"
          strokeWidth={0.6}
        />
      )}
    </svg>
  );
}

/**
 * Mark the court on the hall image (ADR 020, manual calibration in line mode). First the court
 * the analysis suggests (from an earlier video of the same hall, or found automatically): one tap
 * «Passt». Otherwise pick a court line and tap 2 to 3 spots on it; the court is drawn as soon as
 * the clicks allow, and «Speichern» is offered once the clicks agree with one court as the server
 * requires. Named points stay possible as the advanced option.
 */
export function CourtCalibration({
  orgId,
  videoId,
  analysis,
  onClose,
  imageSrc,
  onDone,
  start = "suggest",
}: {
  orgId: string;
  videoId: string;
  analysis: Analysis;
  onClose: () => void;
  /** the hall image, when not the video's panorama (the component page) */
  imageSrc?: string;
  /** after an answer was saved: «Passt», a court from the clicks, «nicht bestimmbar» */
  onDone?: (answer: "confirmed" | "saved" | "undeterminable") => void;
  /** «mark»: the coach already looked at the suggestion (beside it «Neu markieren»): to the lines */
  start?: "suggest" | "mark";
}) {
  const t = useTranslations("calibrate");
  const format = useFormatter();
  const qc = useQueryClient();
  const pano = analysis.panorama!;
  const size: [number, number] = [pano.width, pano.height];
  const src = imageSrc ?? `/v1/orgs/${orgId}/videos/${videoId}/panorama`;
  const state = calibrationState(analysis);
  const suggestion = useMemo(() => {
    const s = suggestionOf(analysis);
    return s && s.imageSize[0] === pano.width && s.imageSize[1] === pano.height ? s : null;
  }, [analysis, pano.width, pano.height]);
  // a court confirmed before (realign): shown under the clicks until they give one
  const existing: Homography | null =
    state === "confirmed" &&
    analysis.calibration &&
    analysis.calibration.image_size[0] === pano.width &&
    analysis.calibration.image_size[1] === pano.height
      ? analysis.calibration.homography
      : null;

  // the coach's last clicks, to edit them again (only what the dialog offers)
  const [prefill] = useState(() => {
    const c = lastClicks(analysis, LOCAL_COURT_MODEL);
    if (!c) return null;
    const points = Object.fromEntries(
      Object.entries(c.points).filter(([n]) => POINT_NAMES.includes(n as PointName)),
    );
    return Object.keys(c.lines).length || Object.keys(points).length
      ? { lines: c.lines, points }
      : null;
  });
  const [flow, dispatch] = useReducer(
    flowReducer,
    { suggestion: suggestion != null && start === "suggest", clicks: prefill },
    initialFlow,
  );
  const [model, setModel] = useState<CourtModel>(LOCAL_COURT_MODEL);
  const [fit, setFit] = useState<{ key: string; fit: ClickFit } | null>(null);
  const [dragFit, setDragFit] = useState<Homography | null>(null);
  const [server, setServer] = useState<{ key: string; outcome: Outcome<ServerFit> } | null>(null);
  // «nicht bestimmbar» is offered; hidden again only if its endpoint turns out missing
  const [undeterminable, setUndeterminable] = useState(true);
  const [asking, setAsking] = useState(false);
  const [advanced, setAdvanced] = useState(false);
  const [busy, setBusy] = useState<"confirm" | "save" | "skip" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [zoomed, setZoomed] = useState(false);
  const stage = useRef<StageHandle>(null);
  const dialog = useRef<HTMLDivElement>(null);
  const offered = offeredLine(flow);
  const clicksKey = keyOf(flow.clicks);

  // the API's court model (a missing endpoint: the local model)
  useEffect(() => {
    let live = true;
    void fetchCourtModel(orgId).then((m) => live && m && setModel(m));
    return () => {
      live = false;
    };
  }, [orgId]);

  // the local fit after each change of the clicks (after the click is painted)
  useEffect(() => {
    const clicks = flow.clicks;
    const key = keyOf(clicks);
    const id = window.setTimeout(() => {
      setFit({ key, fit: fitClicks(clicks, size, model) });
      setDragFit(null);
    }, 0);
    return () => window.clearTimeout(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- the clicks by value
  }, [clicksKey, model, size[0], size[1]]);

  const local = fit?.key === clicksKey ? fit.fit : null;

  // the server's check of the same clicks, after a pause (not on every click)
  useEffect(() => {
    if (
      !local ||
      local.equations < MIN_EQUATIONS ||
      (local.status !== "ok" && local.status !== "disagree")
    )
      return;
    const key = clicksKey;
    const clicks = flow.clicks;
    const id = window.setTimeout(() => {
      void checkClicks(orgId, videoId, {
        space: "panorama",
        frame_ms: 0,
        lines: clicks.lines,
        points: clicks.points,
      }).then((outcome) => setServer({ key, outcome }));
    }, 700);
    return () => window.clearTimeout(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- the clicks by value
  }, [local, clicksKey, orgId, videoId]);
  const checked =
    server?.key === clicksKey &&
    server.outcome.kind !== "missing" &&
    server.outcome.kind !== "error"
      ? server.outcome
      : null;

  // the court the clicks give, and whether it passes (the server's word where it has spoken)
  const verdict = useMemo(() => {
    // the clicks cannot tell which of two courts is meant: never saved, whatever the server says
    if (local?.ambiguous)
      return {
        ok: false,
        median: local.medianPx,
        homography: local.homography,
        worst: null as ClickRef | null,
        dropped: local.dropped,
        ambiguous: local.ambiguous,
      };
    if (checked?.kind === "ok")
      return {
        ok: true,
        median: checked.value.residual_px.median,
        homography: checked.value.homography as Homography,
        worst: null as ClickRef | null,
        dropped: droppedRefs(checked.value.dropped),
      };
    if (checked?.kind === "refused")
      return {
        ok: false,
        median: checked.problem.median_px ?? local?.medianPx ?? null,
        homography: local?.homography ?? null,
        worst: serverRef(checked.problem) ?? local?.worst ?? null,
        dropped: local?.dropped ?? [],
        problem: checked.problem,
      };
    return {
      ok: local?.status === "ok",
      median: local?.medianPx ?? null,
      homography: local?.homography ?? null,
      worst: local?.status === "disagree" ? (local.worst as ClickRef | null) : null,
      dropped: local?.dropped ?? [],
    };
  }, [checked, local]);

  const equations =
    2 * Object.keys(flow.clicks.points).length +
    Object.values(flow.clicks.lines).reduce((s, l) => s + l.length, 0);
  const marking = flow.step === "mark";
  const overlay: { homography: Homography; tone: OverlayTone } | null = !marking
    ? suggestion && { homography: suggestion.homography, tone: "suggest" }
    : dragFit
      ? { homography: dragFit, tone: "draft" }
      : verdict.homography
        ? {
            homography: verdict.homography,
            tone: verdict.ok ? "fit" : local?.status === "need-more" ? "draft" : "bad",
          }
        : (suggestion ?? (existing ? { homography: existing } : null)) && {
            homography: (suggestion?.homography ?? existing)!,
            tone: "suggest",
          };

  const onDrag = useCallback(
    (ref: ClickRef, p: Pt) => {
      // while a click is dragged: a quick refit from the last court
      const base = local?.homography;
      if (!base) return;
      const c: Clicks = { points: { ...flow.clicks.points }, lines: { ...flow.clicks.lines } };
      if (ref.kind === "point") c.points[ref.name] = p;
      else {
        const l = (c.lines[ref.name] ?? []).slice();
        l[ref.index] = p;
        c.lines[ref.name] = l;
      }
      const f = fitClicks(c, size, model, base);
      if (f.homography) setDragFit(f.homography);
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps -- size by value
    [local, flow.clicks, model, size[0], size[1]],
  );

  const close = useCallback(() => onClose(), [onClose]);

  async function done(answer: "confirmed" | "saved" | "undeterminable") {
    await qc.invalidateQueries({ queryKey: ["analysis", videoId] });
    onClose();
    onDone?.(answer);
  }

  async function confirm() {
    setBusy("confirm");
    setError(null);
    const ok = await confirmCourt(orgId, videoId);
    setBusy(null);
    if (!ok) return setError(t("errorConfirm"));
    await done("confirmed");
  }

  async function save() {
    if (!verdict.ok) return;
    setBusy("save");
    setError(null);
    const r = await saveCourt(orgId, videoId, flow.clicks, verdict.homography, model);
    setBusy(null);
    if (r.kind === "ok") return done("saved");
    if (r.kind === "refused") return setError(problemText(r.problem));
    setError(t("errorSave"));
  }

  async function skip(reason: UndeterminableReason) {
    setBusy("skip");
    setError(null);
    const r = await markUndeterminable(orgId, videoId, reason);
    setBusy(null);
    if (r.kind === "ok") return done("undeterminable");
    if (r.kind === "missing") setUndeterminable(false);
    setError(t("errorSave"));
  }

  const lineLabel = (n: string) =>
    LINE_NAMES.includes(n as LineName)
      ? t(`lines.${n}` as "lines.side_near")
      : POINT_NAMES.includes(n as PointName)
        ? t(`points.${n}` as "points.corner_bl")
        : n;
  function problemText(p: ClickProblem): string {
    if (p.code === "no-hall-image") return t("errorNoHallImage");
    if (p.code === "clicks-too-few") return t("errorTooFew");
    if (p.code === "clicks-disagree") {
      const w = serverRef(p);
      return w ? t("disagreeLine", { line: lineLabel(w.name) }) : t("errorDisagree");
    }
    return t("errorSave");
  }

  // keys on the desktop: 1 to 9 a line, Z back, arrows nudge the last click, Enter saves
  const onKey = useRef<(e: KeyboardEvent) => void>(() => {});
  onKey.current = (e: KeyboardEvent) => {
    const el = e.target as HTMLElement | null;
    if (e.key === "Escape") {
      e.preventDefault();
      if (asking) setAsking(false);
      else close();
      return;
    }
    if (el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.tagName === "SELECT"))
      return;
    if (!marking) {
      if (e.key === "Enter" && suggestion && el?.tagName !== "BUTTON") {
        e.preventDefault();
        void confirm();
      }
      return;
    }
    const k = e.key;
    if (/^[1-9]$/.test(k) && !e.ctrlKey && !e.metaKey && !e.altKey) {
      e.preventDefault();
      setAdvanced(false);
      dispatch({ type: "line", name: LINE_NAMES[Number(k) - 1]! });
    } else if ((k === "z" || k === "Z") && !e.altKey) {
      e.preventDefault();
      dispatch({ type: "undo" });
    } else if (k === "Delete" || k === "Backspace") {
      e.preventDefault();
      dispatch({ type: "clearLine" });
    } else if (k === "e" || k === "E") dispatch({ type: "snap" });
    else if (k === "+" || k === "=") stage.current?.zoom(1.5);
    else if (k === "-") stage.current?.zoom(1 / 1.5);
    else if (k === "0") stage.current?.fit();
    else if (k.startsWith("Arrow") && flow.selected) {
      e.preventDefault();
      const step = e.shiftKey ? 5 : 0.5;
      dispatch({
        type: "nudge",
        dx: k === "ArrowLeft" ? -step : k === "ArrowRight" ? step : 0,
        dy: k === "ArrowUp" ? -step : k === "ArrowDown" ? step : 0,
      });
    } else if (k === "Enter" && el?.tagName !== "BUTTON" && verdict.ok) {
      e.preventDefault();
      void save();
    }
  };
  useEffect(() => {
    // the page under the dialog does not scroll along (a phone swipes the picture)
    const before = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = before;
    };
  }, []);
  useEffect(() => {
    dialog.current?.focus();
    const h = (e: KeyboardEvent) => onKey.current(e);
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, []);

  const current = marking
    ? flow.mode === "line"
      ? { kind: "line" as const, name: flow.line }
      : { kind: "point" as const, name: flow.point }
    : null;
  const flagged = [...verdict.dropped, ...(verdict.worst ? [verdict.worst] : [])];
  const need = Math.max(0, (local?.homography ? MIN_EQUATIONS : PREVIEW_EQUATIONS) - equations);

  // the quality bar: how many clicks are still needed, then how far the clicks lie off the court
  const quality = (() => {
    if (!local || equations < PREVIEW_EQUATIONS || local.status === "too-few")
      return {
        tone: "muted",
        text: t("qualityFew", { n: Math.max(1, PREVIEW_EQUATIONS - equations, need) }),
        fill: Math.min(1, equations / MIN_EQUATIONS),
      };
    if (local.status === "need-more")
      return {
        tone: "muted",
        text: t("qualityMore", { n: MIN_EQUATIONS - equations }),
        fill: Math.min(1, equations / MIN_EQUATIONS),
      };
    if (local.status === "no-court") return { tone: "bad", text: t("qualityNoCourt"), fill: 1 };
    const px = (verdict.median ?? 0).toFixed(1);
    if ("ambiguous" in verdict && verdict.ambiguous) return { tone: "bad", text: t("qualityAmbiguous"), fill: 0.5 };
    return verdict.ok
      ? {
          tone: "ok",
          text: t("qualityOk", { px }),
          fill: Math.max(0.08, 1 - (verdict.median ?? 0) / (2 * MAX_MEDIAN_PX)),
        }
      : {
          tone: "bad",
          text: t("qualityBad", { px, max: MAX_MEDIAN_PX }),
          fill: Math.max(0.05, 1 - (verdict.median ?? 0) / (2 * MAX_MEDIAN_PX)),
        };
  })();
  const hint =
    "ambiguous" in verdict && verdict.ambiguous
      ? t("ambiguousLine", { line: lineLabel(verdict.ambiguous) })
      : verdict.worst && !verdict.ok
      ? t("disagreeLine", { line: lineLabel(verdict.worst.name) })
      : verdict.ok && verdict.dropped.length > 0
        ? t("droppedLine", { line: lineLabel(verdict.dropped[0]!.name) })
        : null;

  const lineChip = (name: LineName, i: number) => {
    const n = countOn(flow.clicks, name);
    const active = flow.mode === "line" && flow.line === name;
    return (
      <button
        key={name}
        type="button"
        aria-pressed={active}
        aria-label={t("lineChip", { line: t(`lines.${name}`), key: i + 1, count: n })}
        onClick={() => dispatch({ type: "line", name })}
        className={cn(
          "flex min-h-11 shrink-0 cursor-pointer items-center gap-2 border-2 px-2 py-1 text-left text-[15px] font-semibold",
          active
            ? "border-ink bg-ink text-ground"
            : "border-rule bg-paper text-ink hover:border-ink",
        )}
        data-testid={`line-${name}`}
      >
        <MiniCourt line={name} />
        <span className="min-w-0 flex-1 leading-tight hyphens-auto">{t(`lines.${name}`)}</span>
        <span
          aria-hidden
          className={cn(
            "shrink-0 font-mono text-[13px] tabular-nums",
            active ? "text-ground" : "text-ink-2",
          )}
        >
          {n > 0 ? `${n}/3` : <kbd className="max-lg:hidden">{i + 1}</kbd>}
        </span>
      </button>
    );
  };
  const pointChip = (name: PointName) => {
    const set = name in flow.clicks.points;
    const active = flow.mode === "point" && flow.point === name;
    return (
      <button
        key={name}
        type="button"
        aria-pressed={active}
        aria-label={`${t(`points.${name}`)}${set ? `, ${t("pointSet")}` : ""}`}
        onClick={() => dispatch({ type: "point", name })}
        className={cn(
          "flex min-h-11 shrink-0 cursor-pointer items-center gap-2 border-2 px-2 py-1 text-left text-[15px] font-semibold",
          active
            ? "border-ink bg-ink text-ground"
            : set
              ? "border-ink bg-paper text-ink"
              : "border-rule bg-paper text-ink hover:border-ink",
        )}
        data-testid={`point-${name}`}
      >
        <MiniCourt point={model.points[name] ?? LOCAL_COURT_MODEL.points[name]} />
        <span className="min-w-0 flex-1 leading-tight hyphens-auto">{t(`points.${name}`)}</span>
      </button>
    );
  };

  const skipBlock =
    undeterminable &&
    // for a court still open (suggested or missing): the API keeps a confirmed court over it
    (state === "suggested" || state === "missing") &&
    (asking ? (
      <div className="space-y-2 border-2 border-ink p-3" role="group" aria-labelledby="calib-why">
        <p id="calib-why" className="text-[15px] font-semibold">
          {t("undeterminableWhy")}
        </p>
        <div className="flex flex-wrap gap-2">
          {(["too_far", "cut", "other"] as const).map((r) => (
            <Button
              key={r}
              variant="secondary"
              size="sm"
              onClick={() => void skip(r)}
              loading={busy === "skip"}
              data-testid={`skip-${r}`}
            >
              {t(`reason_${r}`)}
            </Button>
          ))}
          <Button variant="quiet" size="sm" onClick={() => setAsking(false)}>
            {t("cancel")}
          </Button>
        </div>
      </div>
    ) : (
      <Button
        variant="quiet"
        size="sm"
        onClick={() => setAsking(true)}
        data-testid="calibration-undeterminable"
      >
        {t("undeterminable")}
      </Button>
    ));

  const content = (
    <div
      className="fixed inset-0 z-50 flex items-stretch justify-center bg-black/60 sm:p-4 [@media(max-height:520px)]:p-0"
      onClick={close}
    >
      <div
        ref={dialog}
        role="dialog"
        aria-modal="true"
        aria-labelledby="calibrate-title"
        tabIndex={-1}
        className="flex h-full w-full max-w-7xl flex-col overflow-hidden bg-raised outline-none"
        onClick={(e) => e.stopPropagation()}
        data-testid="calibration-dialog"
      >
        <div className="flex shrink-0 items-center justify-between gap-2 border-b border-rule py-1 pr-1 pl-4">
          <h2 id="calibrate-title" className="text-lg font-semibold">
            {marking ? t("title") : t("titleCheck")}
          </h2>
          <Button
            variant="ghost"
            size="icon"
            onClick={close}
            aria-label={t("close")}
            data-testid="calibration-close"
          >
            <X aria-hidden />
          </Button>
        </div>

        <div className="grid min-h-0 flex-1 grid-cols-[minmax(0,1fr)] grid-rows-[auto_minmax(0,1fr)] lg:grid-cols-[minmax(0,1fr)_26rem] lg:grid-rows-1 [@media(orientation:landscape)_and_(max-height:520px)]:grid-cols-[minmax(0,1fr)_17rem] [@media(orientation:landscape)_and_(max-height:520px)]:grid-rows-1">
          <div className="flex min-h-0 flex-col bg-[var(--court-bar)]">
            <div
              className="relative mx-auto w-full max-h-[52vh] lg:max-h-none lg:min-h-0 lg:flex-1 [@media(orientation:landscape)_and_(max-height:520px)]:max-h-none [@media(orientation:landscape)_and_(max-height:520px)]:min-h-0 [@media(orientation:landscape)_and_(max-height:520px)]:flex-1"
              style={{ aspectRatio: `${pano.width} / ${pano.height}` }}
            >
              <CalibrationStage
                ref={stage}
                src={src}
                alt={t("imageAlt")}
                label={marking ? t("stageLabel") : t("stageLabelCheck")}
                size={size}
                model={model}
                overlay={overlay}
                clicks={flow.clicks}
                current={current}
                selected={flow.selected}
                flagged={flagged}
                interactive={marking}
                snap={flow.snap}
                onPlace={(p) => dispatch({ type: "place", p })}
                onDrag={onDrag}
                onMove={(ref, p, prev) => dispatch({ type: "move", ref, p, prev })}
                onSelect={(ref) => dispatch({ type: "select", ref })}
                onZoomChange={setZoomed}
              />
            </div>
            {/* the tools under the picture, never on it: a button on the picture hides clicks */}
            <div className="flex shrink-0 flex-wrap items-center gap-1 px-1 py-1 text-[var(--court-text)]">
              {marking && (
                <>
                  <button
                    type="button"
                    onClick={() => dispatch({ type: "undo" })}
                    disabled={flow.history.length === 0}
                    className={toolClass}
                    aria-label={t("undoLabel")}
                    data-testid="calibration-undo"
                  >
                    <Undo2 aria-hidden className="size-5" />
                    <span className="max-sm:sr-only">{t("undo")}</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => dispatch({ type: "clearLine" })}
                    disabled={
                      countOn(flow.clicks, flow.mode === "line" ? flow.line : flow.point) === 0
                    }
                    className={toolClass}
                    aria-label={
                      flow.mode === "line"
                        ? t("clearLineLabel", { line: t(`lines.${flow.line}`) })
                        : t("clearPoint")
                    }
                    data-testid="calibration-clear-line"
                  >
                    <Eraser aria-hidden className="size-5" />
                    <span className="max-sm:sr-only">
                      {flow.mode === "line" ? t("clearLine") : t("clearPoint")}
                    </span>
                  </button>
                  <button
                    type="button"
                    onClick={() => dispatch({ type: "snap" })}
                    aria-pressed={flow.snap}
                    className={cn(toolClass, flow.snap && "bg-white/15")}
                    aria-label={t("snapLabel")}
                    title={t("snapLabel")}
                    data-testid="calibration-snap"
                  >
                    <Magnet aria-hidden className="size-5" />
                    <span className="max-sm:sr-only">{t("snap")}</span>
                  </button>
                </>
              )}
              <span className="flex-1" />
              <button
                type="button"
                onClick={() => stage.current?.zoom(1 / 1.5)}
                disabled={!zoomed}
                className={toolClass}
                aria-label={t("zoomOut")}
              >
                <Minus aria-hidden className="size-5" />
              </button>
              <button
                type="button"
                onClick={() => stage.current?.zoom(1.5)}
                className={toolClass}
                aria-label={t("zoomIn")}
                data-testid="calibration-zoom-in"
              >
                <Plus aria-hidden className="size-5" />
              </button>
              <button
                type="button"
                onClick={() => stage.current?.fit()}
                disabled={!zoomed}
                className={toolClass}
                aria-label={t("zoomFit")}
              >
                <Scan aria-hidden className="size-5" />
              </button>
            </div>
          </div>

          <div className="flex min-h-0 flex-col">
            <div className="min-h-0 flex-1 space-y-3 overflow-y-auto overscroll-contain p-4 [@media(orientation:landscape)_and_(max-height:520px)]:p-3">
              {!marking && suggestion ? (
                <>
                  <p className="text-[15px] font-semibold" data-testid="suggestion-source">
                    {suggestion.source === "hall"
                      ? suggestion.kickoffAt
                        ? t("sourceHallMatch", {
                            date: format.dateTime(new Date(suggestion.kickoffAt), {
                              day: "numeric",
                              month: "short",
                            }),
                          })
                        : suggestion.label
                          ? t("sourceHallLabel", { label: suggestion.label })
                          : t("sourceHall")
                      : t("sourceAuto")}
                  </p>
                  <p className="text-[15px] text-ink-2">{t("suggestQuestion")}</p>
                </>
              ) : (
                <>
                  <p
                    className="text-[15px]"
                    aria-live="polite"
                    data-testid="calibration-instruction"
                  >
                    {flow.mode === "line"
                      ? t("lineNow", { line: t(`lines.${flow.line}`) })
                      : t("pointNow", { point: t(`points.${flow.point}`) })}
                  </p>
                  {equations === 0 && <p className="text-sm text-ink-2">{t("markIntro")}</p>}
                  {offered && (
                    // three clicks on the line: the next one is offered, the choice stays with the coach
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => dispatch({ type: "line", name: offered })}
                      data-testid="calibration-next"
                    >
                      {t("nextLine", { line: t(`lines.${offered}`) })}
                    </Button>
                  )}
                  {!advanced ? (
                    <div
                      role="group"
                      aria-label={t("linesGroup")}
                      className="grid grid-cols-2 gap-1.5 [@media(orientation:landscape)_and_(max-height:520px)]:grid-cols-1"
                      data-testid="line-chips"
                    >
                      {LINE_NAMES.map(lineChip)}
                    </div>
                  ) : (
                    <div
                      role="group"
                      aria-label={t("pointsGroup")}
                      className="grid grid-cols-2 gap-1.5 [@media(orientation:landscape)_and_(max-height:520px)]:grid-cols-1"
                      data-testid="point-chips"
                    >
                      {POINT_NAMES.map(pointChip)}
                    </div>
                  )}
                  <button
                    type="button"
                    className="min-h-11 cursor-pointer text-left text-sm font-semibold text-ink underline underline-offset-4"
                    onClick={() => {
                      setAdvanced((a) => !a);
                      dispatch({ type: "mode", mode: advanced ? "line" : "point" });
                    }}
                    aria-expanded={advanced}
                    data-testid="calibration-advanced"
                  >
                    {advanced ? t("advancedHide") : t("advanced")}
                  </button>
                  <p className="text-xs text-ink-2 max-lg:hidden">{t("keysHint")}</p>
                </>
              )}
              {(state === "updating" || state === "undeterminable") && (
                <Alert kind="info" data-testid="calibration-state-note">
                  {t(state === "updating" ? "stateUpdating" : "stateUndeterminable")}
                </Alert>
              )}
              {error && <Alert>{error}</Alert>}
            </div>
            {/* the answer in the thumb zone */}
            <div className="shrink-0 space-y-2 border-t border-rule bg-raised p-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] [@media(max-height:520px)]:space-y-1 [@media(max-height:520px)]:p-2">
              {!marking && suggestion ? (
                <div className="grid grid-cols-2 gap-2">
                  <Button
                    onClick={() => void confirm()}
                    loading={busy === "confirm"}
                    data-testid="calibration-confirm"
                  >
                    {t("fits")}
                  </Button>
                  <Button
                    variant="secondary"
                    onClick={() => dispatch({ type: "correct" })}
                    data-testid="calibration-correct"
                  >
                    {t("correct")}
                  </Button>
                </div>
              ) : (
                <>
                  <div className="space-y-1.5" data-testid="calibration-quality">
                    <div className="flex items-baseline justify-between gap-2">
                      <span className="text-sm font-semibold">{t("qualityTitle")}</span>
                      {verdict.median != null &&
                        local?.status !== "need-more" &&
                        local?.status !== "too-few" && (
                          <span className="font-mono text-[13px] tabular-nums text-ink-2">
                            {t("pxShort", { px: verdict.median.toFixed(1) })}
                          </span>
                        )}
                    </div>
                    <div
                      role="meter"
                      aria-label={t("qualityTitle")}
                      aria-valuemin={0}
                      aria-valuemax={100}
                      aria-valuenow={Math.round(quality.fill * 100)}
                      aria-valuetext={quality.text}
                      className="h-2 w-full bg-rule"
                    >
                      <div
                        className={cn(
                          "h-full",
                          quality.tone === "ok"
                            ? "bg-win"
                            : quality.tone === "bad"
                              ? "bg-loss"
                              : "bg-ink-2",
                        )}
                        style={{ width: `${Math.round(quality.fill * 100)}%` }}
                      />
                    </div>
                    <p
                      className={cn(
                        "text-sm",
                        quality.tone === "ok"
                          ? "text-win"
                          : quality.tone === "bad"
                            ? "text-loss"
                            : "text-ink-2",
                      )}
                      aria-live="polite"
                      data-testid="calibration-quality-text"
                    >
                      {quality.text}
                    </p>
                    {hint && (
                      <p className="text-sm text-ink" data-testid="calibration-hint">
                        {hint}
                      </p>
                    )}
                  </div>
                  <Button
                    className="w-full"
                    onClick={() => void save()}
                    disabled={!verdict.ok}
                    loading={busy === "save"}
                    data-testid="calibration-save"
                  >
                    {t("save")}
                  </Button>
                </>
              )}
              {(skipBlock || (marking && suggestion)) && (
                <div className="flex flex-wrap items-center gap-x-2">
                  {marking && suggestion && (
                    <Button
                      variant="quiet"
                      size="sm"
                      onClick={() => dispatch({ type: "suggest" })}
                      data-testid="calibration-back"
                    >
                      {t("backToSuggestion")}
                    </Button>
                  )}
                  {skipBlock}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
  // on top of everything (the page head, a section with its own stacking): in the body; the
  // server (and a test) renders it in place
  return typeof document === "undefined" ? content : createPortal(content, document.body);
}

const toolClass =
  "inline-flex min-h-11 min-w-11 cursor-pointer items-center justify-center gap-1.5 px-2 text-[15px] font-semibold hover:bg-white/10 focus-visible:outline-3 focus-visible:outline-offset-[-3px] focus-visible:outline-white disabled:cursor-default disabled:opacity-40";

/** The click a server problem names, as the dialog knows clicks. */
function serverRef(p: ClickProblem): ClickRef | null {
  const w = p.worst;
  if (!w) return null;
  return w.kind === "point"
    ? { kind: "point", name: w.name }
    : { kind: "line", name: w.name, index: w.index ?? 0 };
}

/**
 * The hall image with the current court drawn on it, read-only: enough to say "Passt" without
 * opening the marking dialog. Nothing when the court is not on the hall image.
 */
export function CourtPreview({
  orgId,
  videoId,
  analysis,
  alt,
}: {
  orgId: string;
  videoId: string;
  analysis: Analysis;
  alt: string;
}) {
  const pano = analysis.panorama;
  const cal = analysis.calibration;
  if (!pano || !cal || cal.image_size[0] !== pano.width || cal.image_size[1] !== pano.height)
    return null;
  return (
    <div
      className="relative overflow-hidden bg-black ring-1 ring-inset ring-border"
      data-testid="court-preview"
    >
      {/* eslint-disable-next-line @next/next/no-img-element -- authenticated API image, not a static asset */}
      <img
        src={`/v1/orgs/${orgId}/videos/${videoId}/panorama`}
        alt={alt}
        width={pano.width}
        height={pano.height}
        className="block h-auto w-full"
      />
      <svg
        viewBox={`0 0 ${pano.width} ${pano.height}`}
        className="pointer-events-none absolute inset-0 size-full"
        aria-hidden
      >
        {/* a dark halo under the orange: the lines must stand out on any hall floor, also outdoors on a phone */}
        {courtPolylines(cal.homography).map((line, i) => (
          <path
            key={`h${i}`}
            d={imagePath(line)}
            fill="none"
            stroke="#000"
            strokeOpacity={0.55}
            strokeWidth={5}
            vectorEffect="non-scaling-stroke"
          />
        ))}
        {courtPolylines(cal.homography).map((line, i) => (
          <path
            key={i}
            d={imagePath(line)}
            fill="none"
            stroke="#f97316"
            strokeWidth={2.5}
            vectorEffect="non-scaling-stroke"
          />
        ))}
      </svg>
    </div>
  );
}
