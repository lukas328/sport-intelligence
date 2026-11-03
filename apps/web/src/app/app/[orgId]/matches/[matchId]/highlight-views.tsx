"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { ShareButton } from "@/components/sharing/share-button";
import { Button } from "@/components/ui/button";
import { Alert, Card, EmptyState } from "@/components/ui/card";
import { Select } from "@/components/ui/field";
import { api } from "@/lib/client";
import { errorKey, type ErrorKey } from "@/lib/errors";

/** Automatic highlights (addendum 01, 4.3): team reels and player reels, 16:9 and 9:16. */
export function HighlightsView({
  orgId,
  matchId,
  teamId,
  staff,
  names,
}: {
  orgId: string;
  matchId: string;
  teamId: string;
  staff: boolean;
  names: Record<string, string>;
}) {
  const t = useTranslations("highlights");
  const tr = useTranslations();
  const qc = useQueryClient();
  const key = ["highlights", matchId];
  const [error, setError] = useState<ErrorKey | null>(null);
  const [format, setFormat] = useState<"16x9" | "9x16">("16x9");
  const [player, setPlayer] = useState("");
  const q = useQuery({
    queryKey: key,
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/matches/{match_id}/highlights", { params: { path: { org_id: orgId, match_id: matchId } } })).data ?? [],
    refetchInterval: (query) => ((query.state.data ?? []).some((r) => r.status === "queued" || r.status === "rendering") ? 5000 : false),
  });
  const create = useMutation({
    mutationFn: async () => {
      const r = await api.POST("/v1/orgs/{org_id}/matches/{match_id}/highlights", {
        params: { path: { org_id: orgId, match_id: matchId } },
        body: { format, player_id: player || null },
      });
      if (r.error) throw r.error;
    },
    onSuccess: () => (setError(null), void qc.invalidateQueries({ queryKey: key })),
    onError: (e) => setError(errorKey(e)),
  });
  return (
    <section className="space-y-4" aria-labelledby="highlights-title">
      <div>
        <h2 id="highlights-title" className="text-lg font-semibold">
          {t("title")}
        </h2>
        <p className="max-w-prose text-sm text-muted">{t("intro")}</p>
      </div>
      {error && <Alert>{tr(`errors.${error}`)}</Alert>}
      {staff && (
        <div className="flex flex-wrap items-end gap-3">
          <Select label={t("format")} value={format} onChange={(e) => setFormat(e.target.value as "16x9")}>
            <option value="16x9">{t("landscape")}</option>
            <option value="9x16">{t("portrait")}</option>
          </Select>
          <Select label={t("player")} value={player} onChange={(e) => setPlayer(e.target.value)}>
            <option value="">{t("team")}</option>
            {Object.entries(names).map(([id, name]) => (
              <option key={id} value={id}>
                {name}
              </option>
            ))}
          </Select>
          <Button variant="secondary" loading={create.isPending} onClick={() => create.mutate()}>
            {t("create")}
          </Button>
        </div>
      )}
      {q.data && q.data.length === 0 && <EmptyState title={t("none")}>{t("noneHint")}</EmptyState>}
      <div className="grid gap-4 md:grid-cols-2">
        {(q.data ?? []).map((r) => (
          <Card key={r.id} className="space-y-2" data-testid="reel">
            <p className="font-medium">
              {r.player_id ? names[r.player_id] ?? t("playerReel") : t("teamReel")} · {r.format === "9x16" ? t("portrait") : t("landscape")}
            </p>
            <p className="text-sm text-muted">
              {t("scenes", { n: r.clip_ids.length })}
              {((r.consent.excluded_players as string[] | undefined) ?? []).length > 0 &&
                ` · ${t("excluded", { n: (r.consent.excluded_players as string[]).length })}`}
            </p>
            {r.status === "ready" ? (
              <>
                <video
                  controls
                  preload="metadata"
                  src={`/v1/orgs/${orgId}/highlights/${r.id}/video.mp4`}
                  className={r.format === "9x16" ? "mx-auto max-h-[70vh] rounded" : "w-full rounded"}
                />
                <div className="flex flex-wrap gap-2">
                  <a className="rounded-md border border-border px-3 py-2 text-sm hover:bg-surface" href={`/v1/orgs/${orgId}/highlights/${r.id}/video.mp4`} download>
                    {t("download")}
                  </a>
                  {staff && <ShareButton orgId={orgId} teamId={teamId} kind="highlight" targetId={r.id} />}
                </div>
              </>
            ) : (
              <p className="text-sm">{t(`status_${r.status}` as "status_queued")}</p>
            )}
          </Card>
        ))}
      </div>
    </section>
  );
}

/** Several files of one match (order, gaps) and suggested match boundaries (addendum 01, 4.8). */
export function PartsPanel({ orgId, matchId, staff }: { orgId: string; matchId: string; staff: boolean }) {
  const t = useTranslations("parts");
  const qc = useQueryClient();
  const path = { org_id: orgId, match_id: matchId };
  const parts = useQuery({
    queryKey: ["parts", matchId],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/matches/{match_id}/parts", { params: { path } })).data ?? [],
  });
  const bounds = useQuery({
    queryKey: ["boundaries", matchId],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/matches/{match_id}/boundaries", { params: { path } })).data ?? [],
  });
  const order = useMutation({
    mutationFn: async (ids: string[]) => api.PUT("/v1/orgs/{org_id}/matches/{match_id}/parts", { params: { path }, body: { video_ids: ids } }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["parts", matchId] }),
  });
  const list = parts.data ?? [];
  const mmss = (ms: number) => `${Math.floor(ms / 60000)}:${String(Math.floor((ms % 60000) / 1000)).padStart(2, "0")}`;
  if (list.length < 2 && (bounds.data ?? []).length === 0) return null;
  return (
    <Card className="space-y-2" data-testid="parts">
      {list.length > 1 && (
        <>
          <h2 className="font-semibold">{t("title")}</h2>
          <ol className="space-y-1 text-sm">
            {list.map((p, i) => (
              <li key={p.video_id} className="flex flex-wrap items-center gap-2">
                <span className="w-6 tabular-nums text-muted">{i + 1}</span>
                <span className="flex-1">{p.filename}</span>
                {p.gap_before_ms != null && p.gap_before_ms > 5000 && <span className="text-accent">{t("gap", { time: mmss(p.gap_before_ms) })}</span>}
                {staff && i > 0 && (
                  <Button
                    variant="ghost"
                    className="min-h-8 px-2 py-1"
                    aria-label={t("up")}
                    onClick={() => {
                      const ids = list.map((x) => x.video_id);
                      [ids[i - 1], ids[i]] = [ids[i]!, ids[i - 1]!];
                      order.mutate(ids);
                    }}
                  >
                    ↑
                  </Button>
                )}
              </li>
            ))}
          </ol>
          <p className="text-xs text-muted">{list.every((p) => p.confirmed) ? t("confirmed") : t("auto")}</p>
        </>
      )}
      {(bounds.data ?? []).map((b) => (
        <Alert key={`${b.video_id}-${b.t_ms}`} kind="info">
          {t("boundary", { time: mmss(b.t_ms), pause: Math.round((b.pause_ms ?? 0) / 60000) })}
        </Alert>
      ))}
    </Card>
  );
}
