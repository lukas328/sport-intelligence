"use client";

import { useTranslations } from "next-intl";
import { useSideLabel } from "@/components/domain/match-sides";
import { formatClock } from "@/lib/format";
import type { Analysis } from "./analysis-panel";

/** Defence systems per team over time (heuristic from positions, M6). */
export function FormationsCard({ formations, onSeek }: { formations: NonNullable<Analysis["formations"]>; onSeek: (ms: number) => void }) {
  const t = useTranslations("formations");
  const side = useSideLabel();
  const label = (f: string) => (f === "open" ? t("open") : f.replaceAll("-", ":"));
  return (
    <section className="space-y-2" data-testid="formations">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="font-semibold">{t("title")}</h2>
        <p className="text-xs text-muted">{t("hint")}</p>
      </div>
      {formations.length === 0 && <p className="text-sm text-muted">{t("none")}</p>}
      {(["home", "away"] as const).map((team) => {
        const segs = formations.filter((f) => f.team === team);
        if (segs.length === 0) return null;
        const total = segs.reduce((s, f) => s + f.end_ms - f.start_ms, 0);
        const share = Object.entries(
          segs.reduce<Record<string, number>>((acc, f) => ({ ...acc, [f.formation]: (acc[f.formation] ?? 0) + f.end_ms - f.start_ms }), {}),
        ).sort((a, b) => b[1] - a[1]);
        return (
          <div key={team} className="space-y-1 text-sm">
            <p>
              <span className="font-medium">{team === "home" ? side("own") : side("opp", t("opponent"))}: </span>
              {share.map(([f, ms]) => `${label(f)} ${Math.round((ms / total) * 100)} %`).join(" · ")}
            </p>
            <ul className="flex flex-wrap gap-1">
              {segs.map((f) => (
                <li key={`${f.start_ms}-${f.team}`}>
                  <button
                    className="bg-surface px-2 py-0.5 font-score text-xs hover:brightness-90"
                    onClick={() => onSeek(f.start_ms)}
                    aria-label={t("jump", { formation: label(f.formation), time: formatClock(f.start_ms) })}
                  >
                    {formatClock(f.start_ms)} {label(f.formation)}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        );
      })}
    </section>
  );
}
