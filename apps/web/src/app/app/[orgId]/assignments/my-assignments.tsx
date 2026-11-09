"use client";

import type { Schemas } from "@handball/api-client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useFormatter, useTranslations } from "next-intl";
import { Button, buttonClass } from "@/components/ui/button";
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
      {/* hairline rows like the coach's list: the title on its own line, the two actions full width
          under it on phones (one decision per row) */}
      <ul className="border-t-2 border-foreground" data-testid="my-assignments">
        {(q.data ?? []).map((a) => {
          const overdue = !a.done_at && a.due_at && new Date(a.due_at).getTime() < now;
          return (
            <li key={a.id} className={cn("space-y-3 border-b border-foreground/15 py-3.5", a.done_at && "text-muted")}>
              <div>
                <p className={cn("text-[1.0625rem] font-semibold", a.done_at && "line-through")}>{a.title}</p>
                <p className="text-sm text-muted">
                  {t(`kind_${a.kind as "drill"}`)} · {a.team_name}
                  {a.due_at && ` · ${t("dueOn", { date: format.dateTime(new Date(a.due_at), { dateStyle: "medium" }) })}`}
                  {overdue && <span className="ml-1 font-semibold text-foreground">{t("overdue")}</span>}
                </p>
                {a.note && <p className="mt-1 text-sm text-foreground">{a.note}</p>}
              </div>
              <div className="grid grid-cols-2 gap-2 sm:flex">
                <Link href={targetLink(orgId, a)} className={buttonClass("secondary", "md")}>
                  {t("openTarget")}
                </Link>
                <Button variant={a.done_at ? "ghost" : "primary"} onClick={() => toggle.mutate({ id: a.id, done: !a.done_at })}>
                  {a.done_at ? t("markOpen") : t("markDone")}
                </Button>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
