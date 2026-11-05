"use client";

import type { Schemas } from "@handball/api-client";
import { useMutation, useQueries, useQuery, useQueryClient } from "@tanstack/react-query";
import { Play } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useFormatter, useTranslations } from "next-intl";
import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Alert, EmptyState } from "@/components/ui/card";
import { Input } from "@/components/ui/field";
import { api } from "@/lib/client";
import { errorKey, type ErrorKey } from "@/lib/errors";
import { formatClock } from "@/lib/format";
import { clockAt } from "@/lib/match-workflow";
import { cn } from "@/lib/utils";

type Filter = Schemas["SearchFilter"];
type Hit = Schemas["SearchHit"];
type TagSet = Schemas["TagSetOut"];

const TYPES = ["shot", "turnover", "steal", "suspension_2min", "seven_meter_awarded"] as const;
const OUTCOMES = ["goal", "save", "miss", "post", "blocked"] as const;
/** rows per page: 135 scenes in one block were a wall */
const PAGE = 40;

function Chip({ on, children, onClick, color }: { on: boolean; children: React.ReactNode; onClick: () => void; color?: string | null }) {
  return (
    <button
      type="button"
      aria-pressed={on}
      onClick={onClick}
      className={cn(
        "inline-flex min-h-8 shrink-0 items-center gap-1 whitespace-nowrap rounded-md border px-3 py-1 text-sm",
        on ? "border-foreground bg-foreground text-background" : "border-border bg-raised hover:bg-surface",
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

export function SearchView({ orgId, teamId, teamName, seasonId }: { orgId: string; teamId: string; teamName: string; seasonId: string | null }) {
  const t = useTranslations("search");
  const te = useTranslations("events");
  const tr = useTranslations();
  const format = useFormatter();
  const qc = useQueryClient();
  const params = useSearchParams();
  // links from the season stage ("goals as clips") open the search pre-filtered
  const [filter, setFilter] = useState<Filter>(() => {
    const outcomes = (params.get("outcome") ?? "").split(",").filter((o): o is (typeof OUTCOMES)[number] => (OUTCOMES as readonly string[]).includes(o));
    const types = (params.get("type") ?? "").split(",").filter((o): o is (typeof TYPES)[number] => (TYPES as readonly string[]).includes(o));
    const side = params.get("side");
    return { ...(outcomes.length ? { outcomes } : {}), ...(types.length ? { types } : {}), ...(side === "own" || side === "opponent" ? { sides: [side] } : {}) } as Filter;
  });
  const [error, setError] = useState<ErrorKey | null>(null);
  const team = { org_id: orgId, team_id: teamId };
  const tp = useTranslations("presentations");
  const target = params.get("presentation");
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
  const all = result.data?.hits ?? [];
  // paging starts over with every new filter
  const fkey = JSON.stringify(filter);
  const [page, setPage] = useState({ key: fkey, n: PAGE });
  const shown = page.key === fkey ? page.n : PAGE;
  const hits = all.slice(0, shown);
  // the match clock needs each match's throw-off; one request per match on the page
  const matchIds = [...new Set(hits.map((h) => h.match_id))];
  const matches = useQueries({
    queries: matchIds.map((id) => ({
      queryKey: ["match", id],
      queryFn: async () => (await api.GET("/v1/orgs/{org_id}/matches/{match_id}", { params: { path: { org_id: orgId, match_id: id } } })).data,
      staleTime: 60_000,
    })),
  });
  // own shirt numbers read as names
  const roster = useQuery({
    queryKey: ["roster", seasonId],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/teams/{team_id}/seasons/{season_id}/roster", { params: { path: { ...team, season_id: seasonId! } } })).data ?? [],
    enabled: !!seasonId,
  });
  const player = (h: Hit) => {
    if (h.number == null) return null;
    const p = h.side === "own" ? (roster.data ?? []).find((r) => r.jersey_number === h.number) : undefined;
    return p ? `${t("shirt", { n: h.number })} ${p.first_name} ${p.last_name}` : t("shirt", { n: h.number });
  };
  const matchOf = (id: string) => matches[matchIds.indexOf(id)]?.data;
  const clockOf = (h: Hit) => {
    const m = matchOf(h.match_id);
    if (!m || h.t_ms == null) return null;
    const c = clockAt(m.kickoff_ms, m.period_s, h.t_ms);
    return c == null || c < 0 ? null : te("at", { period: Math.min(2, Math.floor(c / m.period_s) + 1), clock: formatClock(c * 1000) });
  };
  const facetTags: Record<string, number> = result.data?.facets.tags ?? {};

  const sideName = (side: string | null | undefined, m = undefined as ReturnType<typeof matchOf>) =>
    side === "own" ? teamName : side === "opponent" ? m?.opponent?.name ?? t("side_opponent") : null;
  const filters = (
    <div className="space-y-3">
      {/* labelled groups; on phones each group is one scrolling row */}
      <div className="scrollbar-none -mx-1 flex items-center gap-1 overflow-x-auto px-1 sm:flex-wrap" role="group" aria-label={t("types")}>
        <span className="mr-1 shrink-0 text-[0.8125rem] font-semibold text-muted">{t("types")}</span>
        {TYPES.map((ty) => (
          <Chip key={ty} on={(filter.types ?? []).includes(ty)} onClick={() => setFilter((f) => ({ ...f, types: toggle(f.types, ty) }))}>
            {t(`type_${ty}`)}
          </Chip>
        ))}
      </div>
      <div className="scrollbar-none -mx-1 flex items-center gap-1 overflow-x-auto px-1 sm:flex-wrap" role="group" aria-label={t("outcomes")}>
        <span className="mr-1 shrink-0 text-[0.8125rem] font-semibold text-muted">{t("outcomes")}</span>
        {OUTCOMES.map((o) => (
          <Chip key={o} on={(filter.outcomes ?? []).includes(o)} onClick={() => setFilter((f) => ({ ...f, outcomes: toggle(f.outcomes, o) }))}>
            {te(o)}
          </Chip>
        ))}
        {(["own", "opponent"] as const).map((side) => (
          <Chip key={side} on={(filter.sides ?? []).includes(side)} onClick={() => setFilter((f) => ({ ...f, sides: toggle(f.sides, side) }))}>
            {side === "own" && teamName ? teamName : t(`side_${side}`)}
          </Chip>
        ))}
      </div>
    </div>
  );

  return (
    <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_17rem]">
      <section className="min-w-0 space-y-4" aria-labelledby="search-title">
        <h2 id="search-title" className="sr-only">
          {t("title")}
        </h2>
        {error && <Alert>{tr(`errors.${error}`)}</Alert>}
        {filters}
        <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1 border-b-2 border-foreground pb-2">
          <p className="font-semibold" role="status" data-testid="search-count">
            {result.data ? t("count", { n: result.data.total }) : ""}
          </p>
          {fkey !== "{}" && (
            <button type="button" className="text-sm font-medium text-muted underline underline-offset-4 hover:text-foreground" onClick={() => setFilter({})}>
              {t("reset")}
            </button>
          )}
        </div>
        {result.data && hits.length === 0 && <EmptyState title={t("none")} />}
        <ul className="divide-y divide-foreground/10" data-testid="search-hits">
          {hits.map((h, i) => {
            const m = matchOf(h.match_id);
            const first = i === 0 || hits[i - 1]!.match_id !== h.match_id;
            const playable = h.video_id && h.start_ms != null;
            const what = h.kind === "clip" ? h.title ?? t("clip") : [h.type && t(`type_${h.type as "shot"}`), h.outcome && te(h.outcome as "goal")].filter(Boolean).join(" · ");
            return (
              <li key={`${h.kind}-${h.id}`} className={cn("py-2.5", first && i > 0 && "mt-4 border-t-2 border-t-foreground/30")}>
                {first && (
                  <p className="pb-1.5 text-[0.8125rem] font-semibold text-muted">
                    {format.dateTime(new Date(h.kickoff_at), { day: "numeric", month: "short", year: "2-digit" })} · {h.match_label}
                  </p>
                )}
                <div className="grid grid-cols-[6.5rem_minmax(0,1fr)_auto] items-baseline gap-x-3">
                  <span className="font-score text-sm tabular-nums">{clockOf(h)}</span>
                  <span className="min-w-0">
                    <span className="font-medium">{what}</span>
                    {(h.side || h.number != null) && (
                      <span className="text-sm text-muted">
                        {" · "}
                        {[sideName(h.side, m), player(h)].filter(Boolean).join(" ")}
                      </span>
                    )}
                  </span>
                  <span className="flex items-center gap-2">
                    {target && playable && (
                      <Button variant="secondary" className="min-h-8 px-3 py-1" disabled={added.includes(h.id)} onClick={() => toPresentation.mutate(h)}>
                        {added.includes(h.id) ? tp("addedToPresentation") : tp("addToPresentation")}
                      </Button>
                    )}
                    {playable ? (
                      <Link href={`/app/${orgId}/matches/${h.match_id}?t=${h.start_ms}`} className="inline-flex min-h-9 items-center gap-1 text-sm font-semibold hover:underline hover:underline-offset-4">
                        <Play aria-hidden className="size-3 fill-current" />
                        {t("watch")}
                      </Link>
                    ) : (
                      <span className="text-sm text-muted">{t(h.t_ms == null ? "noTime" : "noVideo")}</span>
                    )}
                  </span>
                </div>
                {tags.length > 0 && (
                  <div className="mt-1.5 flex flex-wrap gap-1 pl-0 sm:pl-[7.25rem]" role="group" aria-label={t("tagsOf")}>
                    {tags.map((tag) => (
                      <Chip key={tag.id} on={h.tag_ids.includes(tag.id)} color={tag.color} onClick={() => setLinks.mutate({ hit: h, tagIds: toggle(h.tag_ids, tag.id) })}>
                        {tagName(tag.id)?.name}
                      </Chip>
                    ))}
                  </div>
                )}
              </li>
            );
          })}
        </ul>
        {all.length > shown && (
          <Button variant="secondary" onClick={() => setPage({ key: fkey, n: shown + PAGE })}>
            {t("more", { n: Math.min(PAGE, all.length - shown), shown, total: all.length })}
          </Button>
        )}
        {result.data?.truncated && all.length <= shown && <p className="text-sm text-muted">{t("truncated", { n: all.length })}</p>}
      </section>

      <aside className="space-y-8 lg:border-l lg:border-foreground/15 lg:pl-6">
        <section className="space-y-2">
          <h2 className="font-semibold">{t("smart")}</h2>
          {(saved.data ?? []).length === 0 && <p className="text-sm text-muted">{t("smartNone")}</p>}
          <ul className="space-y-1">
            {(saved.data ?? []).map((sf) => (
              <li key={sf.id}>
                <button type="button" className="min-h-8 text-sm font-medium underline underline-offset-4 hover:text-accent" onClick={() => setFilter(sf.query)}>
                  {sf.name}
                </button>
              </li>
            ))}
          </ul>
          {fkey !== "{}" && (
            <form onSubmit={(e) => submitName(e, (name) => save.mutate(name))} className="flex gap-2" aria-label={t("saveSmart")}>
              <Input label={t("smartName")} name="name" maxLength={120} />
              <Button type="submit" variant="secondary" className="self-end">
                {t("saveSmart")}
              </Button>
            </form>
          )}
        </section>
        <section className="space-y-3">
          <h2 className="font-semibold">{t("tagSets")}</h2>
          <p className="text-sm text-muted">{t("ownTagsHint")}</p>
          {(sets.data ?? []).map((s) => (
            <div key={s.id} className="space-y-2 border-t border-foreground/10 pt-3">
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
          <form onSubmit={(e) => submitName(e, (name) => createSet.mutate(name))} className="flex gap-2 border-t border-foreground/10 pt-3" aria-label={t("newSet")}>
            <Input label={t("newSet")} name="name" maxLength={60} placeholder={t("newSetPlaceholder")} />
            <Button type="submit" variant="secondary" className="self-end">
              {t("add")}
            </Button>
          </form>
        </section>
      </aside>
    </div>
  );
}
