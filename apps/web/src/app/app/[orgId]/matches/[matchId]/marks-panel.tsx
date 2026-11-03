"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
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
    <details className="rounded-lg border border-border p-4" data-testid="marks-panel">
      <summary className="cursor-pointer font-medium">{t("panel", { n: d?.marks.length ?? 0 })}</summary>
      <div className="mt-3 space-y-3 text-sm">
        <Link href={`/app/${orgId}/matches/${matchId}/marks`} className="text-accent underline">
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
                  className="rounded border border-border px-2"
                  onClick={() => shift.mutate({ id: s.id, offset: (s.offset_ms ?? 0) + delta })}
                >
                  {delta > 0 ? "+" : "-"}
                  {Math.abs(delta) / 1000} s
                </button>
              ))}
          </div>
        ))}
        {(d?.sessions.length ?? 0) > 0 && (
          <button type="button" className="text-accent underline" onClick={() => resync.mutate()}>
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
                      <button type="button" className="tabular-nums text-accent underline" onClick={() => onPlay(m.t_ms!)}>
                        ▶ {mmss(m.t_ms)}
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
