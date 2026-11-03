"use client";

import { Play } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, EmptyState } from "@/components/ui/card";
import { Input } from "@/components/ui/field";
import { api } from "@/lib/client";
import { cn } from "@/lib/utils";

/** Coach overview of "Deine Szenen" (addendum 01, 4.7): scenes, comments, self-assessments. */
export function TeamFeedView({ orgId, matchId, onPlay }: { orgId: string; matchId: string; onPlay?: ((ms: number) => void) | undefined }) {
  const t = useTranslations("feed");
  const qc = useQueryClient();
  const path = { org_id: orgId, match_id: matchId };
  const key = ["team-feed", matchId];
  const [msg, setMsg] = useState<string | null>(null);
  const q = useQuery({
    queryKey: key,
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/matches/{match_id}/feed", { params: { path } })).data ?? [],
  });
  const generate = useMutation({
    mutationFn: async () => (await api.POST("/v1/orgs/{org_id}/matches/{match_id}/feed/generate", { params: { path } })).data,
    onSuccess: (d) => {
      setMsg(t("generated", { n: d?.players ?? 0 }));
      void qc.invalidateQueries({ queryKey: key });
    },
  });
  const comment = useMutation({
    mutationFn: async ({ id, text }: { id: string; text: string }) =>
      api.PATCH("/v1/orgs/{org_id}/feed-items/{item_id}", { params: { path: { org_id: orgId, item_id: id } }, body: { coach_comment: text || null } }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: key }),
  });
  return (
    <section className="space-y-4" aria-labelledby="feed-overview">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 id="feed-overview" className="text-lg font-semibold">
            {t("overview")}
          </h2>
          <p className="max-w-prose text-sm text-muted">{t("overviewIntro")}</p>
        </div>
        <Button variant="secondary" loading={generate.isPending} onClick={() => generate.mutate()}>
          {t("generate")}
        </Button>
      </div>
      {msg && (
        <p role="status" className="text-sm">
          {msg}
        </p>
      )}
      {q.data && q.data.length === 0 && <EmptyState title={t("noFeed")} />}
      <div className="grid gap-4 md:grid-cols-2">
        {(q.data ?? []).map((p) => (
          <Card key={p.player_id} className="space-y-2" data-testid="feed-player">
            <h3 className="font-semibold">
              {p.number != null && `#${p.number} `}
              {p.name}
            </h3>
            <p className="text-sm">
              {t("selfAssessment")}:{" "}
              {p.self_assessment ? (
                <strong>
                  {p.self_assessment.rating}/5{p.self_assessment.text && ` · ${p.self_assessment.text}`}
                </strong>
              ) : (
                <span className="text-muted">{t("noAssessment")}</span>
              )}
            </p>
            <ol className="space-y-2">
              {p.items.map((s) => (
                <li key={s.id} className="space-y-1 rounded-xl ring-1 ring-inset ring-border p-2 text-sm">
                  <div className="flex items-center gap-2">
                    <span className={cn("size-2 rounded-full", s.positive ? "bg-ok" : "bg-muted")} aria-hidden />
                    <span className="flex-1">{t(`reason_${s.reason}` as "reason_goal")}</span>
                    {s.seen && <span className="text-xs text-muted">{t("seen")}</span>}
                    {onPlay && (
                      <button type="button" className="font-medium text-accent hover:underline" onClick={() => onPlay(s.start_ms)}>
                        <Play aria-hidden className="size-4 fill-current" />
                      </button>
                    )}
                  </div>
                  <form
                    className="flex items-end gap-2"
                    onSubmit={(e) => {
                      e.preventDefault();
                      comment.mutate({ id: s.id, text: String(new FormData(e.currentTarget).get("c") ?? "").trim() });
                    }}
                  >
                    <Input label={t("comment")} name="c" defaultValue={s.coach_comment ?? ""} maxLength={1000} />
                    <Button type="submit" variant="ghost">
                      {t("saveComment")}
                    </Button>
                  </form>
                </li>
              ))}
            </ol>
          </Card>
        ))}
      </div>
    </section>
  );
}
