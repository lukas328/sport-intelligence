"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { ChevronDown, Hand, Play } from "lucide-react";
import { useTranslations } from "next-intl";
import { api } from "@/lib/client";

/** "Marked during the match" (addendum 01, 5.3): the coach track after the automatic sync. */
export function MarksPanel({ orgId, matchId, onPlay }: { orgId: string; matchId: string; onPlay?: (ms: number) => void }) {
  const t = useTranslations("marks");
  const qc = useQueryClient();
  const path = { org_id: orgId, match_id: matchId };
  const data = useQuery({
    queryKey: ["marks", matchId],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/matches/{match_id}/marks", { params: { path } })).data,
  });
  const resync = useMutation({
    mutationFn: async () => api.POST("/v1/orgs/{org_id}/matches/{match_id}/marks/sync", { params: { path } }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["marks", matchId] }),
  });
  const shift = useMutation({
    mutationFn: async ({ id, offset }: { id: string; offset: number }) =>
      api.PUT("/v1/orgs/{org_id}/mark-sessions/{session_id}/offset", { params: { path: { org_id: orgId, session_id: id } }, body: { offset_ms: offset } }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["marks", matchId] }),
  });
  const d = data.data;
  const mmss = (ms: number) => `${Math.floor(ms / 60000)}:${String(Math.floor((ms % 60000) / 1000)).padStart(2, "0")}`;
  return (
    <details className="group rounded-2xl bg-raised px-5 py-4 ring-1 ring-border/70" data-testid="marks-panel">
      <summary className="flex cursor-pointer list-none items-center gap-2 font-semibold [&::-webkit-details-marker]:hidden">
        <Hand aria-hidden className="size-4 text-muted" />
        {t("panel", { n: d?.marks.length ?? 0 })}
        <ChevronDown aria-hidden className="ml-auto size-4 text-muted transition-transform group-open:rotate-180" />
      </summary>
      <div className="mt-3 space-y-3 text-sm">
        <Link href={`/app/${orgId}/matches/${matchId}/marks`} className="font-medium text-accent hover:underline">
          {t("open")}
        </Link>
        {(d?.sessions ?? []).map((s) => (
          <div key={s.id} className="flex flex-wrap items-center gap-2 text-muted">
            <span>
              {s.device ?? t("device")}: {s.offset_ms == null ? t("notSynced") : t(`source_${s.source ?? "none"}`)}
            </span>
            {s.offset_ms != null &&
              [-5000, -1000, 1000, 5000].map((delta) => (
                <button
                  key={delta}
                  type="button"
                  className="rounded-full bg-surface px-2.5 py-0.5 text-xs font-medium text-foreground hover:bg-border"
                  onClick={() => shift.mutate({ id: s.id, offset: (s.offset_ms ?? 0) + delta })}
                >
                  {delta > 0 ? "+" : "-"}
                  {Math.abs(delta) / 1000} s
                </button>
              ))}
          </div>
        ))}
        {(d?.sessions.length ?? 0) > 0 && (
          <button type="button" className="font-medium text-accent hover:underline" onClick={() => resync.mutate()}>
            {t("resync")}
          </button>
        )}
        {[1, 2].map((half) => {
          const items = (d?.marks ?? []).filter((m) => m.half === half);
          if (items.length === 0) return null;
          return (
            <div key={half}>
              <p className="font-medium">{t("half", { n: half })}</p>
              <ul className="space-y-1">
                {items.map((m) => (
                  <li key={m.id} className="flex items-center gap-2">
                    {m.t_ms != null && onPlay ? (
                      <button type="button" className="inline-flex items-center gap-1 rounded-full bg-accent/10 px-2 py-0.5 text-xs font-semibold text-accent tabular-nums hover:bg-accent/20" onClick={() => onPlay(m.t_ms!)}>
                        <Play aria-hidden className="size-3 fill-current" /> {mmss(m.t_ms)}
                      </button>
                    ) : (
                      <span className="tabular-nums text-muted">{new Date(m.device_time).toLocaleTimeString()}</span>
                    )}
                    <span>{m.label || t(`key_${m.key}`)}</span>
                    {m.note && <span className="text-muted">{m.note}</span>}
                  </li>
                ))}
              </ul>
            </div>
          );
        })}
      </div>
    </details>
  );
}
