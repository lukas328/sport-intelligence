"use client";

import type { Schemas } from "@handball/api-client";
import { COURT, type Point } from "@handball/court";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useEffect, useMemo, useRef, useState, type MouseEvent } from "react";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/card";
import { api } from "@/lib/client";
import {
  COURT_LANDMARKS,
  MIN_POINTS,
  courtPolylines,
  fitHomography,
  reprojectionPx,
  wellSpread,
  type Pt,
} from "@/lib/court-calibration";
import { cn } from "@/lib/utils";

type Analysis = Schemas["AnalysisOut"];

const flipY = (y: number) => COURT.width - y;
const courtPath = (pts: readonly Point[]) => pts.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x} ${flipY(y)}`).join(" ");
const imagePath = (pts: Pt[]) => pts.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)} ${y.toFixed(1)}`).join(" ");

/**
 * Mark the court on the hall image (ADR 020): pick a landmark on the small court, click the same
 * spot in the hall image. The court is previewed live; saving re-runs the analysis with the points.
 */
export function CourtCalibration({
  orgId,
  videoId,
  analysis,
  onClose,
}: {
  orgId: string;
  videoId: string;
  analysis: Analysis;
  onClose: () => void;
}) {
  const t = useTranslations("calibrate");
  const qc = useQueryClient();
  const pano = analysis.panorama!;
  const [points, setPoints] = useState<{ id: string; image: Pt }[]>([]);
  const [selected, setSelected] = useState<string>(COURT_LANDMARKS[0]!.id);
  const [fit, setFit] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(false);
  const dialog = useRef<HTMLDivElement>(null);

  useEffect(() => {
    dialog.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const court = points.map((p) => COURT_LANDMARKS.find((l) => l.id === p.id)!.court);
  const live = useMemo(() => (points.length >= MIN_POINTS ? fitHomography(court, points.map((p) => p.image)) : null), [points]); // eslint-disable-line react-hooks/exhaustive-deps
  const existing =
    analysis.calibration &&
    analysis.calibration.image_size[0] === pano.width &&
    analysis.calibration.image_size[1] === pano.height
      ? analysis.calibration.homography
      : null;
  const preview = live ?? (points.length === 0 ? existing : null);
  const error_px = live ? reprojectionPx(live, court, points.map((p) => p.image)) : null;

  function place(e: MouseEvent<HTMLImageElement>) {
    const r = e.currentTarget.getBoundingClientRect();
    const image: Pt = [((e.clientX - r.left) / r.width) * pano.width, ((e.clientY - r.top) / r.height) * pano.height];
    setPoints((ps) => [...ps.filter((p) => p.id !== selected), { id: selected, image }]);
    // continue with the next landmark that is not placed yet
    const placed = new Set([...points.map((p) => p.id), selected]);
    const next = COURT_LANDMARKS.find((l) => !placed.has(l.id));
    if (next) setSelected(next.id);
  }

  const autoCourt = existing != null && analysis.calibration?.source === "heuristic";

  async function confirmAuto() {
    setSaving(true);
    setError(false);
    const { error: err } = await api.POST("/v1/orgs/{org_id}/videos/{video_id}/calibration/confirm", {
      params: { path: { org_id: orgId, video_id: videoId } },
    });
    setSaving(false);
    if (err) {
      setError(true);
      return;
    }
    await qc.invalidateQueries({ queryKey: ["analysis", videoId] });
    onClose();
  }

  async function save() {
    setSaving(true);
    setError(false);
    const { error: err } = await api.POST("/v1/orgs/{org_id}/videos/{video_id}/calibration", {
      params: { path: { org_id: orgId, video_id: videoId } },
      body: {
        space: "panorama",
        frame_ms: 0,
        points: points.map((p) => ({ image: p.image, court: COURT_LANDMARKS.find((l) => l.id === p.id)!.court })),
      },
    });
    setSaving(false);
    if (err) {
      setError(true);
      return;
    }
    await qc.invalidateQueries({ queryKey: ["analysis", videoId] });
    onClose();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-stretch justify-center bg-black/60 p-2 sm:p-6" onClick={onClose}>
      <div
        ref={dialog}
        role="dialog"
        aria-modal="true"
        aria-labelledby="calibrate-title"
        tabIndex={-1}
        className="flex w-full max-w-7xl flex-col gap-3 overflow-hidden rounded-lg bg-raised p-4 shadow-xl outline-none"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <h2 id="calibrate-title" className="text-lg font-semibold">
              {t("title")}
            </h2>
            <p className="text-sm text-muted">{t(analysis.camera === "moving" ? "introMoving" : "introFixed")}</p>
          </div>
          <div className="flex gap-2">
            <Button variant="secondary" onClick={() => setFit((f) => !f)}>
              {fit ? t("zoomIn") : t("zoomFit")}
            </Button>
            <Button variant="ghost" onClick={onClose}>
              {t("close")}
            </Button>
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-auto rounded-md ring-1 ring-inset ring-border bg-black">
          <div className="relative" style={fit ? { width: "100%" } : { width: pano.width }}>
            {/* eslint-disable-next-line @next/next/no-img-element -- authenticated API image, not a static asset */}
            <img
              src={`/v1/orgs/${orgId}/videos/${videoId}/panorama`}
              alt={t("imageAlt")}
              width={pano.width}
              height={pano.height}
              className="block h-auto w-full cursor-crosshair select-none"
              draggable={false}
              onClick={place}
              data-testid="hall-image"
            />
            <svg
              viewBox={`0 0 ${pano.width} ${pano.height}`}
              className="pointer-events-none absolute inset-0 size-full"
              aria-hidden
            >
              {preview &&
                courtPolylines(preview).map((line, i) => (
                  <path
                    key={i}
                    d={imagePath(line)}
                    fill="none"
                    stroke={live ? "#22d3ee" : "#f97316"}
                    strokeWidth={Math.max(2, pano.width / 900)}
                    vectorEffect="non-scaling-stroke"
                  />
                ))}
              {points.map((p) => {
                const n = COURT_LANDMARKS.findIndex((l) => l.id === p.id) + 1;
                const r = Math.max(6, pano.width / 300);
                return (
                  <g key={p.id}>
                    <circle cx={p.image[0]} cy={p.image[1]} r={r} fill="#facc15" stroke="#000" strokeWidth={r / 4} />
                    <text x={p.image[0] + r * 1.4} y={p.image[1] - r} fontSize={r * 2.4} fill="#facc15" stroke="#000" strokeWidth={r / 5}>
                      {n}
                    </text>
                  </g>
                );
              })}
            </svg>
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-[minmax(0,22rem)_1fr]">
          <div className="space-y-2">
            <p className="text-sm font-medium">{t("pick", { name: t(`landmarks.${selected}` as "landmarks.cornerNearLeft") })}</p>
            <svg viewBox={`-2 -2 ${COURT.length + 4} ${COURT.width + 4}`} className="w-full rounded-md" style={{ background: "var(--court)" }}>
              <title>{t("courtTitle")}</title>
              {Object.entries(COURT.lines).map(([name, pts]) => (
                <path key={name} d={courtPath(pts)} fill="none" stroke="var(--court-line)" strokeWidth={0.12} />
              ))}
              {COURT_LANDMARKS.map((l, i) => {
                const done = points.some((p) => p.id === l.id);
                const active = l.id === selected;
                return (
                  <g
                    key={l.id}
                    role="button"
                    tabIndex={0}
                    aria-label={t(`landmarks.${l.id}` as "landmarks.cornerNearLeft")}
                    aria-pressed={active}
                    className="cursor-pointer focus:outline-none"
                    onClick={() => setSelected(l.id)}
                    onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && (e.preventDefault(), setSelected(l.id))}
                  >
                    <circle cx={l.court[0]} cy={flipY(l.court[1])} r={active ? 1.1 : 0.8} fill={done ? "#facc15" : active ? "#22d3ee" : "#ffffff"} stroke="#000" strokeWidth={0.15} />
                    <text x={l.court[0]} y={flipY(l.court[1]) + 0.45} fontSize={1} textAnchor="middle" fill="#000">
                      {i + 1}
                    </text>
                  </g>
                );
              })}
            </svg>
            <p className="text-xs text-muted">{t("nearSide")}</p>
          </div>

          <div className="space-y-2 text-sm">
            <p>{t("count", { count: points.length, min: MIN_POINTS })}</p>
            {error_px != null && <p className={cn(error_px > 15 ? "text-error" : "text-muted")}>{t("fit", { px: Math.round(error_px) })}</p>}
            {live && !wellSpread(court) && (
              <Alert kind="info" className="text-sm">
                {t("spread")}
              </Alert>
            )}
            {!live && points.length === 0 && existing && <p className="text-muted">{t(autoCourt ? "existingAuto" : "existing")}</p>}
            <ul className="flex flex-wrap gap-2">
              {points.map((p) => (
                <li key={p.id}>
                  <button
                    type="button"
                    className="rounded-md border border-border px-2 py-0.5 text-xs hover:bg-surface"
                    onClick={() => setPoints((ps) => ps.filter((x) => x.id !== p.id))}
                    aria-label={t("remove", { name: t(`landmarks.${p.id}` as "landmarks.cornerNearLeft") })}
                  >
                    {COURT_LANDMARKS.findIndex((l) => l.id === p.id) + 1} · {t(`landmarks.${p.id}` as "landmarks.cornerNearLeft")} ×
                  </button>
                </li>
              ))}
            </ul>
            {error && <Alert>{t("error")}</Alert>}
            <div className="flex flex-wrap gap-2 pt-1">
              {autoCourt && points.length === 0 && (
                <Button onClick={confirmAuto} loading={saving} data-testid="calibration-confirm">
                  {t("confirm")}
                </Button>
              )}
              <Button variant={autoCourt && points.length === 0 ? "secondary" : "primary"} onClick={save} disabled={!live} loading={saving} data-testid="calibration-save">
                {t("save")}
              </Button>
              <Button variant="secondary" onClick={() => setPoints([])} disabled={points.length === 0}>
                {t("reset")}
              </Button>
            </div>
            <p className="text-xs text-muted">{t("hint")}</p>
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * The hall image with the current court drawn on it, read-only: enough to say "Passt" without
 * opening the marking dialog. Nothing when the court is not on the hall image.
 */
export function CourtPreview({ orgId, videoId, analysis, alt }: { orgId: string; videoId: string; analysis: Analysis; alt: string }) {
  const pano = analysis.panorama;
  const cal = analysis.calibration;
  if (!pano || !cal || cal.image_size[0] !== pano.width || cal.image_size[1] !== pano.height) return null;
  return (
    <div className="relative overflow-hidden rounded-md bg-black ring-1 ring-inset ring-border" data-testid="court-preview">
      {/* eslint-disable-next-line @next/next/no-img-element -- authenticated API image, not a static asset */}
      <img src={`/v1/orgs/${orgId}/videos/${videoId}/panorama`} alt={alt} width={pano.width} height={pano.height} className="block h-auto w-full" />
      <svg viewBox={`0 0 ${pano.width} ${pano.height}`} className="pointer-events-none absolute inset-0 size-full" aria-hidden>
        {/* a dark halo under the orange: the lines must stand out on any hall floor, also outdoors on a phone */}
        {courtPolylines(cal.homography).map((line, i) => (
          <path key={`h${i}`} d={imagePath(line)} fill="none" stroke="#000" strokeOpacity={0.55} strokeWidth={5} vectorEffect="non-scaling-stroke" />
        ))}
        {courtPolylines(cal.homography).map((line, i) => (
          <path key={i} d={imagePath(line)} fill="none" stroke="#f97316" strokeWidth={2.5} vectorEffect="non-scaling-stroke" />
        ))}
      </svg>
    </div>
  );
}
