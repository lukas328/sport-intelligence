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
              className={cn("rounded-md px-2 py-1", keeper === k ? "bg-foreground text-background" : "bg-surface hover:bg-border")}
            >
              {k ? t("keeperView") : t("shooterView")}
            </button>
          ))}
        </div>
      )}
      {/* the goal as it stands in the hall: red and white posts and crossbar, net cells inside */}
      <div className="relative px-2 pt-2" data-testid="goal-grid">
        <span aria-hidden className="absolute inset-x-0 top-0 h-2 rounded-t-sm" style={{ background: "repeating-linear-gradient(90deg, #c8102e 0 22px, #ffffff 22px 44px)", boxShadow: "inset 0 0 0 1px rgb(0 0 0 / 0.15)" }} />
        <span aria-hidden className="absolute top-0 bottom-0 left-0 w-2" style={{ background: "repeating-linear-gradient(180deg, #c8102e 0 22px, #ffffff 22px 44px)", boxShadow: "inset 0 0 0 1px rgb(0 0 0 / 0.15)" }} />
        <span aria-hidden className="absolute top-0 right-0 bottom-0 w-2" style={{ background: "repeating-linear-gradient(180deg, #c8102e 0 22px, #ffffff 22px 44px)", boxShadow: "inset 0 0 0 1px rgb(0 0 0 / 0.15)" }} />
      <div className="grid aspect-[3/2] grid-cols-3 gap-px bg-border">
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
                "flex flex-col items-center justify-center bg-raised text-xs transition-colors hover:brightness-95",
                mode === "pick" && selected === zone && "bg-accent text-accent-contrast",
                d && d.shots > 0 && mode === "stats" && "font-semibold",
              )}
              style={mode === "stats" && pct != null ? { background: `color-mix(in srgb, var(--foreground) ${Math.round(Math.min(70, pct * 0.7))}%, var(--raised))`, color: pct > 55 ? "var(--background)" : undefined } : undefined}
            >
              {mode === "stats" ? (
                d ? (
                  <>
                    <span className="text-sm font-bold tabular-nums font-wide">
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
    </div>
  );
}
