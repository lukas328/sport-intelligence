"use client";

import { Plus, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { useId } from "react";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/card";
import { REFEREE_PICK, kitWarnings, type Kits, type TeamKitKey } from "@/lib/kit";
import { cn } from "@/lib/utils";

const TEAM_KITS = [
  ["own", "matches.kitOwn"],
  ["own_gk", "matches.kitOwnGk"],
  ["opponent", "matches.kitOpp"],
  ["opponent_gk", "matches.kitOppGk"],
] as const satisfies readonly (readonly [TeamKitKey, string])[];

const SWATCH = "relative grid size-8 shrink-0 place-items-center overflow-hidden rounded-full";
const PICKER = "absolute inset-0 size-full cursor-pointer opacity-0";

/** The kit colours of a match as colour swatches: four team kits and the optional referee kit,
 * with the warning when two of them are hard to tell apart. Used by the new and the edit form. */
export function KitFields({ kits, onChange }: { kits: Kits; onChange: (kits: Kits) => void }) {
  const t = useTranslations();
  const hintId = useId();
  const similar = kitWarnings(kits);
  const referee = `${t("matches.kitReferee")} (${t("common.optional")})`;
  return (
    <>
      <div className="flex flex-wrap gap-x-5 gap-y-3">
        {TEAM_KITS.map(([k, label]) => (
          <label key={k} className="flex cursor-pointer items-center gap-2 text-sm">
            <span className={cn(SWATCH, "ring-1 ring-border")} style={{ background: kits[k] }}>
              <input
                aria-label={t(label)}
                name={`kit_${k}`}
                type="color"
                value={kits[k]}
                onChange={(e) => onChange({ ...kits, [k]: e.target.value })}
                className={PICKER}
              />
            </span>
            {t(label)}
          </label>
        ))}
        <div className="flex items-center gap-2">
          <label className="flex cursor-pointer items-center gap-2 text-sm">
            <span
              className={cn(
                SWATCH,
                kits.referee
                  ? "ring-1 ring-border"
                  : "border border-dashed border-muted text-muted",
              )}
              style={kits.referee ? { background: kits.referee } : undefined}
              data-testid="kit-referee"
            >
              {!kits.referee && <Plus aria-hidden className="size-4" />}
              <input
                aria-label={referee}
                aria-describedby={hintId}
                name="kit_referee"
                type="color"
                value={kits.referee ?? REFEREE_PICK}
                onChange={(e) => onChange({ ...kits, referee: e.target.value })}
                className={PICKER}
              />
            </span>
            {referee}
          </label>
          {kits.referee && (
            <Button
              type="button"
              variant="quiet"
              size="icon-sm"
              className="-my-1"
              aria-label={t("matches.kitRefereeClear")}
              title={t("matches.kitRefereeClear")}
              onClick={() => onChange({ ...kits, referee: null })}
            >
              <X aria-hidden />
            </Button>
          )}
        </div>
      </div>
      <p className="mt-2 text-xs text-muted">{t("matches.kitsHint")}</p>
      <p id={hintId} className="mt-1 text-xs text-muted">
        {t("matches.kitRefereeHint")}
      </p>
      {similar.length > 0 && (
        <Alert kind="info" className="mt-3">
          <span data-testid="kit-warning">
            {t("matchForm.kitWarning", {
              pairs: similar
                .map(([a, b]) => `${t(`matchForm.kit_${a}`)} / ${t(`matchForm.kit_${b}`)}`)
                .join(", "),
            })}
          </span>
        </Alert>
      )}
    </>
  );
}
