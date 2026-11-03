"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useFormatter, useTranslations } from "next-intl";
import { Check, ChevronRight, Film } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { EmptyState, Skeleton } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { api } from "@/lib/client";

export function FeedList({ orgId }: { orgId: string }) {
  const t = useTranslations("feed");
  const tm = useTranslations("matches");
  const format = useFormatter();
  const q = useQuery({
    queryKey: ["my-feeds", orgId],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/me/feeds", { params: { path: { org_id: orgId } } })).data ?? [],
  });
  return (
    <div className="space-y-8">
      <PageHeader title={t("title")} description={t("intro")} />
      {q.isLoading ? (
        <Skeleton className="h-40" />
      ) : (q.data ?? []).length === 0 ? (
        <EmptyState icon={<Film />} title={t("none")} />
      ) : (
        <ul className="divide-y divide-border/70 overflow-hidden rounded-lg bg-raised border border-border" data-testid="feed-list">
          {(q.data ?? []).map((f) => {
            const d = new Date(f.kickoff_at);
            return (
              <li key={`${f.player_id}-${f.match_id}`}>
                <Link href={`/app/${orgId}/feed/${f.match_id}?player=${f.player_id}`} className="group flex items-center gap-4 px-4 py-4 transition-colors hover:bg-surface/70 sm:px-5">
                  <span className="w-11 shrink-0 text-center leading-none">
                    <span className="block text-lg font-bold font-wide tabular-nums">{format.dateTime(d, { day: "numeric" })}</span>
                    <span className="mt-1 block text-[0.6875rem] font-medium uppercase tracking-wide text-muted">{format.dateTime(d, { month: "short" })}</span>
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate font-semibold">{f.opponent ?? tm("training")}</span>
                    {f.relation === "guardian" && <span className="block text-[0.8125rem] text-muted">{f.player_first_name}</span>}
                  </span>
                  {f.assessed ? (
                    <span className="inline-flex items-center gap-1 text-[0.8125rem] text-ok">
                      <Check aria-hidden className="size-4" />
                      {t("assessed")}
                    </span>
                  ) : (
                    <Badge tone="accent">{t("assessNow")}</Badge>
                  )}
                  <ChevronRight aria-hidden className="size-4 shrink-0 text-muted transition-transform group-hover:translate-x-0.5" />
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
