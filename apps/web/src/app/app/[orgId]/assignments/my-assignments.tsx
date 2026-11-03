"use client";

import type { Schemas } from "@handball/api-client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useFormatter, useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/card";
import { api } from "@/lib/client";
import { cn } from "@/lib/utils";

export function targetLink(orgId: string, a: Pick<Schemas["AssignmentOut"], "kind" | "target_id">): string {
  return {
    playlist: `/app/${orgId}/playlists/${a.target_id}`,
    play: `/app/${orgId}/plays/${a.target_id}`,
    match: `/app/${orgId}/matches/${a.target_id}`,
    drill: `/app/${orgId}/drills#${a.target_id}`,
  }[a.kind as "drill"];
}

export function MyAssignments({ orgId }: { orgId: string }) {
  const t = useTranslations("assignments");
  const format = useFormatter();
  const qc = useQueryClient();
  const key = ["my-assignments", orgId];
  const q = useQuery({
    queryKey: key,
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/me/assignments", { params: { path: { org_id: orgId } } })).data ?? [],
  });
  const toggle = useMutation({
    mutationFn: async ({ id, done }: { id: string; done: boolean }) =>
      api.PUT("/v1/orgs/{org_id}/assignments/{assignment_id}/status", { params: { path: { org_id: orgId, assignment_id: id } }, body: { done } }),
    onSuccess: () => (void qc.invalidateQueries({ queryKey: key }), void qc.invalidateQueries({ queryKey: ["notifications", orgId] })),
  });
  const now = Date.now();
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold sm:text-[1.75rem]">{t("mine")}</h1>
      {q.data && q.data.length === 0 && <EmptyState title={t("none")} />}
      <ul className="space-y-2" data-testid="my-assignments">
        {(q.data ?? []).map((a) => {
          const overdue = !a.done_at && a.due_at && new Date(a.due_at).getTime() < now;
          return (
            <li key={a.id} className={cn("flex flex-wrap items-center gap-3 rounded-lg bg-raised border border-border p-3", a.done_at && "opacity-70")}>
              <div className="min-w-0 flex-1">
                <p className={cn("font-medium", a.done_at && "line-through")}>{a.title}</p>
                <p className="text-sm text-muted">
                  {t(`kind_${a.kind as "drill"}`)} · {a.team_name}
                  {a.due_at && ` · ${t("dueOn", { date: format.dateTime(new Date(a.due_at), { dateStyle: "medium" }) })}`}
                  {overdue && <span className="ml-1 font-medium text-error">{t("overdue")}</span>}
                </p>
                {a.note && <p className="mt-1 text-sm">{a.note}</p>}
              </div>
              <Link href={targetLink(orgId, a)} className="inline-flex min-h-9 items-center gap-1.5 rounded-md bg-raised px-4 text-[0.8125rem] font-medium ring-1 ring-inset ring-border hover:bg-surface">
                {t("openTarget")}
              </Link>
              <Button variant={a.done_at ? "ghost" : "primary"} onClick={() => toggle.mutate({ id: a.id, done: !a.done_at })}>
                {a.done_at ? t("markOpen") : t("markDone")}
              </Button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
