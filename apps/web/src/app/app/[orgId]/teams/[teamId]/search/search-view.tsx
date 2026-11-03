"use client";

import type { Schemas } from "@handball/api-client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useFormatter, useTranslations } from "next-intl";
import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Alert, Card, EmptyState } from "@/components/ui/card";
import { Input } from "@/components/ui/field";
import { api } from "@/lib/client";
import { errorKey, type ErrorKey } from "@/lib/errors";
import { cn } from "@/lib/utils";

type Filter = Schemas["SearchFilter"];
type Hit = Schemas["SearchHit"];
type TagSet = Schemas["TagSetOut"];

const TYPES = ["shot", "turnover", "steal", "suspension_2min", "seven_meter_awarded"] as const;
const OUTCOMES = ["goal", "save", "miss", "post", "blocked"] as const;

function Chip({ on, children, onClick, color }: { on: boolean; children: React.ReactNode; onClick: () => void; color?: string | null }) {
  return (
    <button
      type="button"
      aria-pressed={on}
      onClick={onClick}
      className={cn(
        "inline-flex min-h-8 items-center gap-1 rounded-full border px-3 py-1 text-sm",
        on ? "border-accent bg-accent text-accent-contrast" : "border-border hover:bg-surface",
      )}
    >
      {color && <span aria-hidden className="size-2.5 rounded-full" style={{ background: color }} />}
      {children}
    </button>
  );
}

function toggle<T>(list: T[] | undefined, v: T): T[] {
  const l = list ?? [];
  return l.includes(v) ? l.filter((x) => x !== v) : [...l, v];
}

export function SearchView({ orgId, teamId }: { orgId: string; teamId: string }) {
  const t = useTranslations("search");
  const te = useTranslations("events");
  const tr = useTranslations();
  const format = useFormatter();
  const qc = useQueryClient();
  const [filter, setFilter] = useState<Filter>({});
  const [error, setError] = useState<ErrorKey | null>(null);
  const team = { org_id: orgId, team_id: teamId };
  const tp = useTranslations("presentations");
  const target = useSearchParams().get("presentation");
  const [added, setAdded] = useState<string[]>([]);
  const toPresentation = useMutation({
    mutationFn: async (h: Hit) => {
      const r = await api.POST("/v1/orgs/{org_id}/presentations/{pres_id}/slides", {
        params: { path: { org_id: orgId, pres_id: target! } },
        body: { type: "clip", content: { video_id: h.video_id, in_ms: h.start_ms, out_ms: h.end_ms } },
      });
      if (r.error) throw r.error;
      return h.id;
    },
    onSuccess: (id) => setAdded((a) => [...a, id]),
    onError: (e) => setError(errorKey(e)),
  });

  const sets = useQuery({
    queryKey: ["tag-sets", teamId],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/teams/{team_id}/tag-sets", { params: { path: team } })).data ?? [],
  });
  const tags = (sets.data ?? []).flatMap((s: TagSet) => s.tags);
  const result = useQuery({
    queryKey: ["search", teamId, filter],
    queryFn: async () => (await api.POST("/v1/orgs/{org_id}/teams/{team_id}/search", { params: { path: team }, body: filter })).data,
  });
  const saved = useQuery({
    queryKey: ["saved-filters", teamId],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/teams/{team_id}/saved-filters", { params: { path: team } })).data ?? [],
  });

  const fail = (e: unknown) => setError(errorKey(e));
  const createSet = useMutation({
    mutationFn: async (name: string) => {
      const r = await api.POST("/v1/orgs/{org_id}/teams/{team_id}/tag-sets", { params: { path: team }, body: { name, tags: [] } });
      if (r.error) throw r.error;
    },
    onSuccess: () => (setError(null), void qc.invalidateQueries({ queryKey: ["tag-sets", teamId] })),
    onError: fail,
  });
  const addTag = useMutation({
    mutationFn: async ({ set, name }: { set: string; name: string }) => {
      const r = await api.POST("/v1/orgs/{org_id}/tag-sets/{tag_set_id}/tags", {
        params: { path: { org_id: orgId, tag_set_id: set } },
        body: { name },
      });
      if (r.error) throw r.error;
    },
    onSuccess: () => (setError(null), void qc.invalidateQueries({ queryKey: ["tag-sets", teamId] })),
    onError: fail,
  });
  const setLinks = useMutation({
    mutationFn: async ({ hit, tagIds }: { hit: Hit; tagIds: string[] }) => {
      const r = await api.PUT("/v1/orgs/{org_id}/tag-links", {
        params: { path: { org_id: orgId } },
        body: { target_type: hit.kind, target_id: hit.id, tag_ids: tagIds },
      });
      if (r.error) throw r.error;
    },
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["search", teamId] }),
    onError: fail,
  });
  const save = useMutation({
    mutationFn: async (name: string) => {
      const r = await api.POST("/v1/orgs/{org_id}/teams/{team_id}/saved-filters", { params: { path: team }, body: { name, query: filter } });
      if (r.error) throw r.error;
    },
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["saved-filters", teamId] }),
    onError: fail,
  });

  function submitName(e: FormEvent<HTMLFormElement>, run: (name: string) => void) {
    e.preventDefault();
    const name = String(new FormData(e.currentTarget).get("name") ?? "").trim();
    if (name) run(name);
    e.currentTarget.reset();
  }

  const tagName = (id: string) => tags.find((x) => x.id === id);
  const hits = result.data?.hits ?? [];
  const facetTags: Record<string, number> = result.data?.facets.tags ?? {};

  return (
    <div className="grid gap-6 lg:grid-cols-[18rem_1fr]">
      <aside className="space-y-4">
        <Card className="space-y-3">
          <h2 className="font-semibold">{t("tagSets")}</h2>
          {(sets.data ?? []).map((s) => (
            <div key={s.id} className="space-y-2">
              <p className="text-sm font-medium">{s.name}</p>
              <div className="flex flex-wrap gap-1">
                {s.tags.map((tag) => (
                  <Chip key={tag.id} color={tag.color} on={(filter.tags_any ?? []).includes(tag.id)} onClick={() => setFilter((f) => ({ ...f, tags_any: toggle(f.tags_any, tag.id) }))}>
                    {tag.name}
                    {facetTags[tag.id] != null && <span className="tabular-nums opacity-70">{facetTags[tag.id]}</span>}
                  </Chip>
                ))}
              </div>
              <form onSubmit={(e) => submitName(e, (name) => addTag.mutate({ set: s.id, name }))} className="flex gap-2" aria-label={t("addTagTo", { set: s.name })}>
                <Input label={t("newTag")} name="name" maxLength={60} className="min-h-8" />
                <Button type="submit" variant="secondary" className="self-end">
                  {t("add")}
                </Button>
              </form>
            </div>
          ))}
          <form onSubmit={(e) => submitName(e, (name) => createSet.mutate(name))} className="flex gap-2" aria-label={t("newSet")}>
            <Input label={t("newSet")} name="name" maxLength={60} placeholder={t("newSetPlaceholder")} />
            <Button type="submit" variant="secondary" className="self-end">
              {t("add")}
            </Button>
          </form>
          <p className="text-xs text-muted">{t("ownTagsHint")}</p>
        </Card>
        <Card className="space-y-2">
          <h2 className="font-semibold">{t("smart")}</h2>
          {(saved.data ?? []).length === 0 && <p className="text-sm text-muted">{t("smartNone")}</p>}
          <ul className="space-y-1">
            {(saved.data ?? []).map((sf) => (
              <li key={sf.id}>
                <button type="button" className="text-sm font-medium text-accent hover:underline" onClick={() => setFilter(sf.query)}>
                  {sf.name}
                </button>
              </li>
            ))}
          </ul>
        </Card>
      </aside>

      <section className="space-y-4" aria-labelledby="search-title">
        <h2 id="search-title" className="text-lg font-semibold">
          {t("title")}
        </h2>
        {error && <Alert>{tr(`errors.${error}`)}</Alert>}
        <div className="space-y-2">
          <div className="flex flex-wrap gap-1" role="group" aria-label={t("types")}>
            {TYPES.map((ty) => (
              <Chip key={ty} on={(filter.types ?? []).includes(ty)} onClick={() => setFilter((f) => ({ ...f, types: toggle(f.types, ty) }))}>
                {t(`type_${ty}`)}
              </Chip>
            ))}
          </div>
          <div className="flex flex-wrap gap-1" role="group" aria-label={t("outcomes")}>
            {OUTCOMES.map((o) => (
              <Chip key={o} on={(filter.outcomes ?? []).includes(o)} onClick={() => setFilter((f) => ({ ...f, outcomes: toggle(f.outcomes, o) }))}>
                {te(o)}
              </Chip>
            ))}
            {(["own", "opponent"] as const).map((side) => (
              <Chip key={side} on={(filter.sides ?? []).includes(side)} onClick={() => setFilter((f) => ({ ...f, sides: toggle(f.sides, side) }))}>
                {t(`side_${side}`)}
              </Chip>
            ))}
          </div>
          <div className="flex flex-wrap items-end gap-3">
            <Button variant="ghost" onClick={() => setFilter({})}>
              {t("reset")}
            </Button>
            <form onSubmit={(e) => submitName(e, (name) => save.mutate(name))} className="flex gap-2" aria-label={t("saveSmart")}>
              <Input label={t("smartName")} name="name" maxLength={120} />
              <Button type="submit" variant="secondary" className="self-end">
                {t("saveSmart")}
              </Button>
            </form>
          </div>
        </div>
        <p className="text-sm text-muted" role="status" data-testid="search-count">
          {result.data ? t("count", { n: result.data.total }) : ""}
        </p>
        {result.data && hits.length === 0 && <EmptyState title={t("none")} />}
        <ul className="divide-y divide-border/70 rounded-2xl bg-raised ring-1 ring-border/70" data-testid="search-hits">
          {hits.map((h) => (
            <li key={`${h.kind}-${h.id}`} className="space-y-2 px-3 py-2">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm text-muted tabular-nums">{format.dateTime(new Date(h.kickoff_at), { dateStyle: "short" })}</span>
                <span className="font-medium">{h.match_label}</span>
                <span className="text-sm">
                  {h.kind === "clip" ? h.title ?? t("clip") : [h.type && t(`type_${h.type as "shot"}`), h.outcome && te(h.outcome as "goal"), h.number != null && `#${h.number}`].filter(Boolean).join(" · ")}
                </span>
                {target && h.video_id && h.start_ms != null && (
                  <Button variant="secondary" className="min-h-8 px-3 py-1" disabled={added.includes(h.id)} onClick={() => toPresentation.mutate(h)}>
                    {added.includes(h.id) ? tp("addedToPresentation") : tp("addToPresentation")}
                  </Button>
                )}
                {h.video_id && h.start_ms != null && (
                  <Link href={`/app/${orgId}/matches/${h.match_id}?t=${h.start_ms}`} className="ml-auto inline-flex min-h-9 items-center gap-1.5 rounded-full bg-raised px-4 text-[0.8125rem] font-medium ring-1 ring-inset ring-border hover:bg-surface">
                    {t("watch")}
                  </Link>
                )}
              </div>
              <div className="flex flex-wrap gap-1" role="group" aria-label={t("tagsOf")}>
                {tags.map((tag) => {
                  const on = h.tag_ids.includes(tag.id);
                  return (
                    <Chip key={tag.id} on={on} color={tag.color} onClick={() => setLinks.mutate({ hit: h, tagIds: toggle(h.tag_ids, tag.id) })}>
                      {tagName(tag.id)?.name}
                    </Chip>
                  );
                })}
              </div>
            </li>
          ))}
        </ul>
        {result.data?.truncated && <p className="text-sm text-muted">{t("truncated", { n: hits.length })}</p>}
      </section>
    </div>
  );
}
