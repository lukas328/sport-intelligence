"use client";

import type { Schemas } from "@handball/api-client";
import { useTranslations } from "next-intl";
import { useCallback, useState } from "react";
import { Checkbox, Select } from "@/components/ui/field";

type Video = Schemas["VideoOut"];
export type MultiMode = "single" | "pip" | "side";

export interface MultiAngle {
  mode: MultiMode;
  secondary: string | null;
  secondaryCam: Video | null;
  auto: boolean;
  setMode: (m: MultiMode) => void;
  pick: (id: string | null) => void;
  setAuto: (v: boolean) => void;
}

export function useMultiAngle(cams: Video[], mainId: string): MultiAngle {
  const others = cams.filter((c) => c.id !== mainId);
  const [mode, setMode] = useState<MultiMode>("single");
  const [secondary, setSecondary] = useState<string | null>(others[0]?.id ?? null);
  const [auto, setAuto] = useState(false);
  return {
    mode,
    secondary,
    secondaryCam: others.find((c) => c.id === secondary) ?? null,
    auto,
    setMode,
    pick: useCallback((id: string | null) => setSecondary(id), []),
    setAuto,
  };
}

/** Picture-in-picture, side by side and automatic best camera (addendum 01, 4.5). */
export function MultiAngleControls({ cams, state }: { cams: Video[]; state: MultiAngle }) {
  const t = useTranslations("multiAngle");
  const tc = useTranslations("camera");
  const others = cams.filter((c) => c.role !== "main");
  return (
    <div className="flex flex-wrap items-end gap-3 rounded-md border border-border p-2" data-testid="multi-angle">
      <Select label={t("layout")} value={state.mode} onChange={(e) => state.setMode(e.target.value as MultiMode)}>
        <option value="single">{t("single")}</option>
        <option value="pip">{t("pip")}</option>
        <option value="side">{t("side")}</option>
      </Select>
      <Select label={t("second")} value={state.secondary ?? ""} onChange={(e) => state.pick(e.target.value || null)}>
        {others.map((c) => (
          <option key={c.id} value={c.id}>
            {tc(c.role as "main")}
          </option>
        ))}
      </Select>
      <Checkbox label={t("auto")} checked={state.auto} onChange={(e) => state.setAuto(e.target.checked)} />
    </div>
  );
}
