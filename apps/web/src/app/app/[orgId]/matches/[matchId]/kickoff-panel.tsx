"use client";

import { useQueryClient } from "@tanstack/react-query";
import { Play } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/card";
import { Input } from "@/components/ui/field";
import { api } from "@/lib/client";
import { errorKey, type ErrorKey } from "@/lib/errors";
import { formatClock } from "@/lib/format";
import { kickoffMissing, parseClock } from "@/lib/match-workflow";

/** The throw-off of each half, set at the current video time: it maps the match clock to the
 * video, so official goals, goal candidates and the event list line up with the picture. A video
 * that starts after the throw-off gets its clock from what the match clock shows at one moment. */
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
  const [editing, setEditing] = useState<number | null>(null);
  // the half whose clock is being entered, and what was typed
  const [clockFor, setClockFor] = useState<number | null>(null);
  const [clock, setClock] = useState("");
  const [clockInvalid, setClockInvalid] = useState(false);
  const missing = kickoffMissing(kickoff, periodS, durationMs);
  async function set(period: number, clockS?: number) {
    const ms = Math.round(getTime());
    const { error } = await api.PUT("/v1/orgs/{org_id}/matches/{match_id}/kickoff", {
      params: { path: { org_id: orgId, match_id: matchId } },
      body: clockS == null ? { period, t_ms: ms } : { period, t_ms: ms, clock_s: clockS },
    });
    if (error) return setError(errorKey(error));
    setError(null);
    setClockFor(null);
    setNotice(
      clockS == null
        ? t("kickoffSaved", { n: period, time: formatClock(ms) })
        : t("clockSaved", { n: period, clock: formatClock(clockS * 1000), time: formatClock(ms) }),
    );
    // every time on the match clock moves with it
    for (const key of ["match", "events", "stats", "official-goals", "goal-candidates"]) void qc.invalidateQueries({ queryKey: [key, matchId] });
  }
  function submitClock(period: number) {
    const s = parseClock(clock);
    setClockInvalid(s == null);
    if (s != null) void set(period, s);
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
              {/* nothing to set where the half is not in the video; a mark read from the overlay
                  only changes on request */}
              {(at == null ? !(p === 2 && kickoff?.["1"] != null && !missing.includes(2)) : at >= 0 || editing === p) ? (
                <span className="ml-auto flex flex-wrap gap-2">
                  {clockFor !== p && (
                    <Button
                      variant="quiet"
                      size="sm"
                      onClick={() => (setClockFor(p), setClock(""), setClockInvalid(false))}
                      data-testid={`kickoff-clock-${p}`}
                    >
                      {t("clockHere")}
                    </Button>
                  )}
                  <Button variant={missing[0] === p ? "primary" : "secondary"} size="sm" onClick={() => void set(p)} data-testid={`kickoff-${p}`}>
                    {t("setHere")}
                  </Button>
                </span>
              ) : at != null && at < 0 ? (
                <Button variant="quiet" size="sm" className="ml-auto" onClick={() => setEditing(p)}>
                  {t("change")}
                </Button>
              ) : null}
              {clockFor === p && (
                // the paused moment of a video that starts after the throw-off: what the clock shows
                <form
                  className="flex w-full flex-wrap items-end gap-2"
                  onSubmit={(e) => (e.preventDefault(), submitClock(p))}
                  data-testid={`kickoff-clock-form-${p}`}
                >
                  <div className="w-32">
                    <Input
                      label={t("clockLabel")}
                      value={clock}
                      onChange={(e) => setClock(e.target.value)}
                      inputMode="decimal"
                      autoComplete="off"
                      placeholder={p === 1 ? "12:40" : formatClock((periodS + 760) * 1000)}
                      // the error sits under the whole row, not squeezed under the narrow field
                      aria-invalid={clockInvalid || undefined}
                      aria-describedby={clockInvalid ? `clock-error-${p}` : undefined}
                      // Escape leaves the field without saving
                      onKeyDown={(e) => e.key === "Escape" && setClockFor(null)}
                      className="font-score tabular-nums"
                      autoFocus
                    />
                  </div>
                  <Button type="submit" size="sm" variant="secondary">
                    {t("clockSave")}
                  </Button>
                  <Button type="button" size="sm" variant="quiet" onClick={() => setClockFor(null)}>
                    {t("clockCancel")}
                  </Button>
                  {clockInvalid && (
                    <p id={`clock-error-${p}`} className="w-full text-sm text-error">
                      {t("clockInvalid")}
                    </p>
                  )}
                </form>
              )}
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
