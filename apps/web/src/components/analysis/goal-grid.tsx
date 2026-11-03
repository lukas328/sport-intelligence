"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";
import { cn } from "@/lib/utils";

const ROWS = [
  ["TL", "TC", "TR"],
  ["ML", "MC", "MR"],
  ["BL", "BC", "BR"],
] as const;

const mirror = (z: string) => z[0] + ({ L: "R", R: "L", C: "C" } as Record<string, string>)[z[1]!]!;

/** 3x3 goal. Data is stored from the shooter's view (BRIEF 4.4); the keeper view mirrors it. */
export function GoalGrid({
  data,
  onCell,
  selected,
  mode = "stats",
  saves = false,
}: {
  /** goals/shots per zone; with `saves` the numbers are saves/faced and shown in green */
  saves?: boolean;
  data?: Record<string, { shots: number; goals: number }>;
  onCell?: (zone: string) => void;
  selected?: string | null;
  mode?: "stats" | "pick";
}) {
  const t = useTranslations("shotsView");
  const [keeper, setKeeper] = useState(saves);
  return (
    <div className="space-y-2">
      {mode === "stats" && (
        <div className="flex gap-1 text-xs" role="group" aria-label={t("goal")}>
          {[false, true].map((k) => (
            <button
              key={String(k)}
              aria-pressed={keeper === k}
              onClick={() => setKeeper(k)}
              className={cn("rounded px-2 py-1", keeper === k ? "bg-accent text-accent-contrast" : "bg-surface")}
            >
              {k ? t("keeperView") : t("shooterView")}
            </button>
          ))}
        </div>
      )}
      <div className="grid aspect-[3/2] grid-cols-3 gap-0.5 rounded-t-md border-4 border-b-0 border-red-600 bg-red-600 p-0.5" data-testid="goal-grid">
        {ROWS.flat().map((cell) => {
          const zone = keeper ? mirror(cell) : cell;
          const d = data?.[zone];
          const pct = d && d.shots ? Math.round((d.goals / d.shots) * 100) : null;
          return (
            <button
              key={cell}
              type="button"
              onClick={() => onCell?.(zone)}
              aria-pressed={mode === "pick" ? selected === zone : undefined}
              aria-label={`${zone}${d ? `: ${d.goals}/${d.shots}` : ""}`}
              className={cn(
                "flex flex-col items-center justify-center bg-background text-xs",
                mode === "pick" && selected === zone && "bg-accent text-accent-contrast",
                d && d.shots > 0 && mode === "stats" && "font-semibold",
              )}
              style={mode === "stats" && pct != null ? { background: `color-mix(in srgb, var(${saves ? "--ok" : "--error"}) ${Math.min(80, pct)}%, var(--background))` } : undefined}
            >
              {mode === "stats" ? (
                d ? (
                  <>
                    <span className="tabular-nums">
                      {d.goals}/{d.shots}
                    </span>
                    {pct != null && <span className="opacity-70">{pct} %</span>}
                  </>
                ) : (
                  <span className="opacity-40">0</span>
                )
              ) : (
                zone
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
