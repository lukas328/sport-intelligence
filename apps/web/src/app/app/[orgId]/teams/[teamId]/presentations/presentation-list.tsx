"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useFormatter, useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/card";
import { Input } from "@/components/ui/field";
import { api } from "@/lib/client";

export function PresentationList({ orgId, teamId }: { orgId: string; teamId: string }) {
  const t = useTranslations("presentations");
  const format = useFormatter();
  const router = useRouter();
  const path = { org_id: orgId, team_id: teamId };
  const q = useQuery({
    queryKey: ["presentations", teamId],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/teams/{team_id}/presentations", { params: { path } })).data ?? [],
  });
  const create = useMutation({
    mutationFn: async (title: string) => (await api.POST("/v1/orgs/{org_id}/teams/{team_id}/presentations", { params: { path }, body: { title } })).data,
    onSuccess: (p) => p && router.push(`/app/${orgId}/presentations/${p.id}`),
  });
  return (
    <div className="space-y-4">
      <form
        className="flex flex-wrap items-end gap-2"
        aria-label={t("new")}
        onSubmit={(e) => {
          e.preventDefault();
          const title = String(new FormData(e.currentTarget).get("title") ?? "").trim();
          if (title) create.mutate(title);
        }}
      >
        <Input label={t("newTitle")} name="title" required maxLength={160} placeholder={t("newPlaceholder")} />
        <Button type="submit" loading={create.isPending}>
          {t("new")}
        </Button>
      </form>
      {q.data && q.data.length === 0 && <EmptyState title={t("none")}>{t("noneHint")}</EmptyState>}
      <ul className={q.data?.length ? "divide-y divide-foreground/10 border-t-2 border-foreground" : undefined} data-testid="presentation-list">
        {(q.data ?? []).map((p) => (
          <li key={p.id}>
            <Link href={`/app/${orgId}/presentations/${p.id}`} className="group flex flex-wrap items-baseline gap-x-3 py-3">
              <span className="flex-1 font-medium group-hover:underline group-hover:underline-offset-4">{p.title}</span>
              <span className="text-sm text-muted">{t("slides", { n: p.slides })}</span>
              {p.shared_with_players && <span className="text-sm text-muted">{t("shared")}</span>}
              <span className="text-sm text-muted">{format.dateTime(new Date(p.created_at), { dateStyle: "medium" })}</span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
