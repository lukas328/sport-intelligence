"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { ShareButton } from "@/components/sharing/share-button";
import { Button } from "@/components/ui/button";
import { Alert, EmptyState } from "@/components/ui/card";
import { Select } from "@/components/ui/field";
import { api } from "@/lib/client";
import { cn } from "@/lib/utils";
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
      <div className="space-y-1 border-b border-foreground/15 pb-3">
        <h2 id="highlights-title" className="font-display text-2xl">
          {t("title")}
        </h2>
        <p className="max-w-prose text-sm text-muted">{t("intro")}</p>
      </div>
      {error && <Alert>{tr(`errors.${error}`)}</Alert>}
      {staff && (
        // a new reel is an occasional job: folded, not a form on top of the reels
        <details className="text-sm">
        <summary className="cursor-pointer font-medium">{t("newReel")}</summary>
        <div className="flex flex-wrap items-end gap-3 pt-3">
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
        </details>
      )}
      {q.data && q.data.length === 0 && <EmptyState title={t("none")}>{t("noneHint")}</EmptyState>}
      <div className="grid gap-x-12 gap-y-6 md:grid-cols-2">
        {(q.data ?? []).map((r) => (
          <div key={r.id} className="space-y-2 border-t-2 border-foreground pt-3" data-testid="reel">
            <p className="font-semibold">
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
                  className={r.format === "9x16" ? "mx-auto max-h-[70vh]" : "w-full"}
                />
                <div className="flex flex-wrap gap-2">
                  <a className="inline-flex min-h-9 items-center gap-1.5 bg-raised px-4 text-[0.9375rem] font-medium ring-1 ring-inset ring-border hover:bg-surface" href={`/v1/orgs/${orgId}/highlights/${r.id}/video.mp4`} download>
                    {t("download")}
                  </a>
                  {staff && <ShareButton orgId={orgId} teamId={teamId} kind="highlight" targetId={r.id} />}
                </div>
              </>
            ) : (
              // the reel's frame in its real format, so the coach sees what is coming and where
              <div
                className={cn(
                  "grid place-items-center bg-surface text-sm text-muted",
                  r.format === "9x16" ? "aspect-[9/16] h-56" : "aspect-video w-full max-w-sm",
                )}
              >
                {t(`status_${r.status}` as "status_queued")}
              </div>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
