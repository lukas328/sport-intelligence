"use client";

import type { Schemas } from "@handball/api-client";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Checkbox, Select } from "@/components/ui/field";

type Analysis = Schemas["AnalysisOut"];

export interface SpotlightState {
  ready: boolean;
  track: number | null;
  dim: boolean;
  trail: boolean;
  picking: boolean;
  set: (patch: Partial<Pick<SpotlightState, "track" | "dim" | "trail" | "picking">>) => void;
}

export function useSpotlight(analysis: Analysis | null): SpotlightState {
  const [s, setS] = useState({ track: null as number | null, dim: false, trail: true, picking: false });
  // moving cameras: the stored calibration refers to the panorama, not to each frame (ADR 020)
  const ready = Boolean(
    analysis?.status === "ready" &&
      analysis.calibration &&
      analysis.camera !== "moving" &&
      analysis.chunk_ms &&
      (analysis.chunks ?? 0) > 0,
  );
  return { ready, ...s, set: (patch) => setS((cur) => ({ ...cur, ...patch })) };
}

/** Choose the highlighted player from the list or by clicking in the video (4.2). */
export function SpotlightControls({ spot, tracks, names }: { spot: SpotlightState; tracks: Analysis["tracks"]; names: Record<string, string> }) {
  const t = useTranslations("spotlight");
  const label = (tr: Analysis["tracks"][number]) =>
    (tr.player_id && names[tr.player_id]) || (tr.number != null ? `#${tr.number}` : t("track", { n: tr.track_no }));
  const players = tracks.filter((tr) => tr.team && tr.team !== "referee" && tr.observed_share > 0.05);
  return (
    <div className="flex flex-wrap items-end gap-3 rounded-xl ring-1 ring-inset ring-border p-2" data-testid="spotlight-controls">
      <Select
        label={t("title")}
        value={spot.track ?? ""}
        onChange={(e) => spot.set({ track: e.target.value === "" ? null : Number(e.target.value) })}
      >
        <option value="">{t("off")}</option>
        {players.map((tr) => (
          <option key={tr.track_no} value={tr.track_no}>
            {label(tr)} · {tr.team?.startsWith("home") ? t("own") : t("opponent")}
          </option>
        ))}
      </Select>
      <Button variant={spot.picking ? "primary" : "secondary"} onClick={() => spot.set({ picking: !spot.picking })} aria-pressed={spot.picking}>
        {t("pick")}
      </Button>
      <Checkbox label={t("dim")} checked={spot.dim} onChange={(e) => spot.set({ dim: e.target.checked })} />
      <Checkbox label={t("trail")} checked={spot.trail} onChange={(e) => spot.set({ trail: e.target.checked })} />
    </div>
  );
}
