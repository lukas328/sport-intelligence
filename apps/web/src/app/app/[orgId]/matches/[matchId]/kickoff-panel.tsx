"use client";

import { useQueryClient } from "@tanstack/react-query";
import { Play } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/card";
import { api } from "@/lib/client";
import { errorKey, type ErrorKey } from "@/lib/errors";
import { formatClock } from "@/lib/format";
import { kickoffMissing } from "@/lib/match-workflow";

/** The throw-off of each half, set at the current video time: it maps the match clock to the
 * video, so official goals, goal candidates and the event list line up with the picture. */
export function KickoffPanel({
  orgId,
  matchId,
  kickoff,
  periodS,
  durationMs,
  getTime,
  onSeek,
}: {
  orgId: string;
  matchId: string;
  kickoff: Record<string, number> | null | undefined;
  periodS: number;
  durationMs: number | null;
  getTime: () => number;
  onSeek: (ms: number) => void;
}) {
  const t = useTranslations("workflow");
  const tr = useTranslations();
  const qc = useQueryClient();
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<ErrorKey | null>(null);
  const missing = kickoffMissing(kickoff, periodS, durationMs);
  async function set(period: number) {
    const ms = Math.round(getTime());
    const { error } = await api.PUT("/v1/orgs/{org_id}/matches/{match_id}/kickoff", {
      params: { path: { org_id: orgId, match_id: matchId } },
      body: { period, t_ms: ms },
    });
    if (error) return setError(errorKey(error));
    setError(null);
    setNotice(t("kickoffSaved", { n: period, time: formatClock(ms) }));
    // every time on the match clock moves with it
    for (const key of ["match", "events", "stats", "official-goals", "goal-candidates"]) void qc.invalidateQueries({ queryKey: [key, matchId] });
  }
  return (
    <section className="space-y-4" data-testid="kickoff-panel" aria-labelledby="kickoff-title">
      <div className="space-y-1">
        <h2 id="kickoff-title" className="font-display text-xl">
          {t("kickoff")}
        </h2>
        <p className="text-sm text-muted">{t("kickoffHint")}</p>
      </div>
      <ul className="divide-y divide-border/70 border-y border-border/70">
        {[1, 2].map((p) => {
          const at = kickoff?.[String(p)];
          return (
            <li key={p} className="flex flex-wrap items-center gap-x-3 gap-y-2 py-3">
              <span className="w-24 font-semibold">{t("period", { n: p })}</span>
              {at != null && at < 0 ? (
                // the video starts later in the half (mark read from the score overlay)
                <span className="text-sm text-muted">{t("startsAt", { time: formatClock(-at) })}</span>
              ) : at != null ? (
                <Button variant="secondary" size="sm" className="tabular-nums" aria-label={t("jumpKickoff", { time: formatClock(at) })} onClick={() => onSeek(at)}>
                  <Play aria-hidden className="size-3 fill-current" />
                  {formatClock(at)}
                </Button>
              ) : (
                // the second half of a clip of the first: nothing to set
                <span className={missing.includes(p) ? "text-sm font-medium" : "text-sm text-muted"}>
                  {t(p === 2 && kickoff?.["1"] != null && !missing.includes(2) ? "notNeeded" : "notSet")}
                </span>
              )}
              <Button variant={missing[0] === p ? "primary" : "secondary"} size="sm" className="ml-auto" onClick={() => void set(p)} data-testid={`kickoff-${p}`}>
                {t("setHere")}
              </Button>
            </li>
          );
        })}
      </ul>
      <div aria-live="polite">
        {notice && <p className="text-sm text-ok">{notice}</p>}
        {error && <Alert>{tr(`errors.${error}`)}</Alert>}
      </div>
    </section>
  );
}
