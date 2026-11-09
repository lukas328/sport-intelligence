"use client";

import { useTranslations } from "next-intl";
import { useCallback } from "react";
import { formatClock } from "@/lib/format";
import { clockAt } from "@/lib/match-workflow";

/** Times in the workbench as the coach thinks of them: "1. HZ 12:55" on the match clock. Video
 * time only while no throw-off places the video on the match clock. */
export function useGameTime(kickoff: Record<string, number> | null | undefined, periodS: number) {
  const t = useTranslations("events");
  const clock = useCallback(
    (period: number | null | undefined, clockS: number | null | undefined) =>
      clockS == null ? null : t("at", { period: period ?? Math.floor(clockS / periodS) + 1, clock: formatClock(clockS * 1000) }),
    [t, periodS],
  );
  const at = useCallback(
    (videoMs: number) => {
      const c = clockAt(kickoff, periodS, videoMs);
      return c == null || c < 0 ? formatClock(videoMs) : clock(Math.min(2, Math.floor(c / periodS) + 1), c)!;
    },
    [kickoff, periodS, clock],
  );
  return { at, clock };
}
