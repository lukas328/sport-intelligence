"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useFormatter, useTranslations } from "next-intl";
import { EmptyState } from "@/components/ui/card";
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
    <div className="space-y-4">
      <h1 className="text-2xl font-bold sm:text-[1.75rem]">{t("title")}</h1>
      <p className="text-muted">{t("intro")}</p>
      {q.data && q.data.length === 0 && <EmptyState title={t("none")} />}
      <ul className="space-y-2" data-testid="feed-list">
        {(q.data ?? []).map((f) => (
          <li key={`${f.player_id}-${f.match_id}`}>
            <Link
              href={`/app/${orgId}/feed/${f.match_id}?player=${f.player_id}`}
              className="flex flex-wrap items-center gap-3 rounded-2xl bg-raised ring-1 ring-border/70 p-3 hover:bg-surface"
            >
              <span className="text-sm text-muted tabular-nums">{format.dateTime(new Date(f.kickoff_at), { dateStyle: "medium" })}</span>
              <span className="flex-1 font-medium">{f.opponent ?? tm("training")}</span>
              {f.relation === "guardian" && <span className="text-sm text-muted">{f.player_first_name}</span>}
              <span className={f.assessed ? "text-sm text-ok" : "text-sm font-medium text-accent"}>{f.assessed ? t("assessed") : t("assessNow")}</span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
