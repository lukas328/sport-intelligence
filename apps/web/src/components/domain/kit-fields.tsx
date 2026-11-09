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

const SWATCH = "relative grid size-9 shrink-0 place-items-center rounded-sm has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-accent";

/** A shirt in the kit's colour: the swatch looks like what it stands for. */
function Shirt({ colour, empty = false }: { colour?: string; empty?: boolean }) {
  return (
    <svg aria-hidden viewBox="0 0 24 24" className="size-9">
      <path
        d="M8 3 4.2 4.8 2 9l3.2 1.6L6.4 9v12h11.2V9l1.2 1.6L22 9l-2.2-4.2L16 3c-.9 1.4-2.3 2.2-4 2.2S8.9 4.4 8 3Z"
        fill={empty ? "none" : colour}
        stroke="currentColor"
        strokeOpacity={empty ? 0.6 : 0.35}
        strokeWidth="1"
        strokeDasharray={empty ? "2 1.5" : undefined}
        strokeLinejoin="round"
      />
    </svg>
  );
}
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
            <span className={SWATCH}>
              <Shirt colour={kits[k]} />
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
            <span className={cn(SWATCH, !kits.referee && "text-muted")} data-testid="kit-referee">
              <Shirt colour={kits.referee ?? undefined} empty={!kits.referee} />
              {!kits.referee && <Plus aria-hidden className="absolute size-3.5" />}
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
