"use client";

import { Check } from "lucide-react";
import { DRILLS, type Lang } from "@handball/tactics";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useFormatter, useLocale, useTranslations } from "next-intl";
import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Alert, Card, EmptyState } from "@/components/ui/card";
import { Input } from "@/components/ui/field";
import { api } from "@/lib/client";
import { useConfirm } from "@/components/ui/confirm";
import { problemCode } from "@handball/api-client";
import { targetLink } from "../../../assignments/my-assignments";

const KINDS = ["playlist", "play", "match", "drill"] as const;
type Kind = (typeof KINDS)[number];

export function TeamAssignments({ orgId, teamId }: { orgId: string; teamId: string }) {
  const t = useTranslations("assignments");
  const format = useFormatter();
  const lang = useLocale() as Lang;
  const qc = useQueryClient();
  const [kind, setKind] = useState<Kind>("playlist");
  const [notice, setNotice] = useState<string | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const team = { org_id: orgId, team_id: teamId };
  const key = ["team-assignments", teamId];
  const list = useQuery({
    queryKey: key,
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/teams/{team_id}/assignments", { params: { path: team } })).data ?? [],
  });
  const playlists = useQuery({
    queryKey: ["playlists", teamId],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/teams/{team_id}/playlists", { params: { path: team } })).data ?? [],
  });
  const plays = useQuery({
    queryKey: ["plays", teamId],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/teams/{team_id}/plays", { params: { path: team } })).data ?? [],
  });
  const matches = useQuery({
    queryKey: ["team-matches", teamId],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/teams/{team_id}/matches", { params: { path: team } })).data ?? [],
  });
  const options: { id: string; label: string }[] = {
    playlist: (playlists.data ?? []).map((p) => ({ id: p.id, label: p.title })),
    play: (plays.data ?? []).map((p) => ({ id: p.id, label: p.name })),
    match: (matches.data ?? []).map((m) => ({ id: m.id, label: `${format.dateTime(new Date(m.kickoff_at), { dateStyle: "short" })} ${m.opponent_name}` })),
    drill: DRILLS.map((d) => ({ id: d.id, label: d.name[lang] ?? d.name["de-CH"] })),
  }[kind];

  const confirm = useConfirm();
  const remove = useMutation({
    mutationFn: async (id: string) => api.DELETE("/v1/orgs/{org_id}/assignments/{assignment_id}", { params: { path: { org_id: orgId, assignment_id: id } } }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: key }),
  });

  async function create(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const f = new FormData(form);
    const target = String(f.get("target") ?? "");
    const due = String(f.get("due") ?? "");
    const title = String(f.get("title") ?? "").trim() || options.find((o) => o.id === target)?.label || "";
    const { error } = await api.POST("/v1/orgs/{org_id}/teams/{team_id}/assignments", {
      params: { path: team },
      body: {
        kind,
        target_id: target,
        title,
        note: String(f.get("note") ?? "").trim() || null,
        due_at: due ? new Date(`${due}T20:00:00`).toISOString() : null,
        user_ids: [],
        notify_email: f.get("email") === "on",
      },
    });
    if (error) return setProblem(problemCode(error) ?? "generic");
    setProblem(null);
    setNotice(t("created"));
    form.reset();
    void qc.invalidateQueries({ queryKey: key });
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_22rem]">
      <section className="space-y-3" aria-label={t("team")}>
        {list.data && list.data.length === 0 && <EmptyState title={t("none")} />}
        <ul className="space-y-2" data-testid="team-assignments">
          {(list.data ?? []).map((a) => (
            <li key={a.id} className="space-y-2 rounded-2xl bg-raised ring-1 ring-border/70 p-3">
              <div className="flex flex-wrap items-center gap-2">
                <Link href={targetLink(orgId, a)} className="font-medium underline decoration-dotted underline-offset-4">
                  {a.title}
                </Link>
                <span className="text-sm text-muted">
                  {t(`kind_${a.kind as "drill"}`)}
                  {a.due_at && ` · ${t("dueOn", { date: format.dateTime(new Date(a.due_at), { dateStyle: "medium" }) })}`}
                </span>
                <span className="ml-auto text-sm tabular-nums">{t("progress", { done: a.done, total: a.recipients })}</span>
              </div>
              <div className="h-2 overflow-hidden rounded bg-surface" aria-hidden>
                <div className="h-full bg-accent" style={{ width: `${a.recipients ? (a.done / a.recipients) * 100 : 0}%` }} />
              </div>
              <ul className="flex flex-wrap gap-1 text-xs">
                {(a.progress ?? []).map((p) => (
                  <li key={String(p.user_id)} className="rounded-full border border-border px-2 py-0.5">
                    {p.done_at ? <Check aria-hidden className="mr-1 inline size-3.5 text-ok" /> : null}
                    {String(p.name)}
                  </li>
                ))}
              </ul>
              <button className="text-xs text-muted underline" onClick={async () => (await confirm({ title: t("delete"), danger: true })) && remove.mutate(a.id)}>
                {t("delete")}
              </button>
            </li>
          ))}
        </ul>
      </section>
      <Card className="h-fit space-y-3">
        <h2 className="text-lg font-semibold">{t("new")}</h2>
        <form onSubmit={create} className="space-y-3" aria-label={t("new")}>
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium">{t("kind")}</span>
            <select value={kind} onChange={(e) => setKind(e.target.value as Kind)} className="min-h-10 rounded-xl bg-raised ring-1 ring-inset ring-border px-2">
              {KINDS.map((k) => (
                <option key={k} value={k}>
                  {t(`kind_${k}`)}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium">{t("target")}</span>
            <select name="target" required className="min-h-10 rounded-xl bg-raised ring-1 ring-inset ring-border px-2">
              {options.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.label}
                </option>
              ))}
            </select>
          </label>
          <Input label={t("titleLabel")} name="title" maxLength={200} />
          <Input label={t("note")} name="note" maxLength={2000} />
          <Input label={t("due")} name="due" type="date" />
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" name="email" defaultChecked />
            {t("email")}
          </label>
          <p className="text-xs text-muted">
            {t("recipients")}: {t("allPlayers")}
          </p>
          <Button type="submit" className="w-full" disabled={options.length === 0}>
            {t("create")}
          </Button>
        </form>
        <div aria-live="polite">
          {problem && <Alert className="py-2">{problem === "no-recipients" ? t("noPlayers") : problem}</Alert>}
          {notice && !problem && (
            <Alert kind="success" className="py-2">
              {notice}
            </Alert>
          )}
        </div>
      </Card>
    </div>
  );
}
