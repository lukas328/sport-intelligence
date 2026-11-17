"use client";

import type { Schemas } from "@handball/api-client";
import { DRILLS, type Drill, type Focus } from "@handball/tactics";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronDown, Play } from "lucide-react";
import Link from "next/link";
import { useFormatter, useLocale, useTranslations } from "next-intl";
import { useState } from "react";
import { useInsightText, type Insight } from "@/components/analysis/insights";
import { Button, buttonClass } from "@/components/ui/button";
import { Alert, Skeleton } from "@/components/ui/card";
import { api } from "@/lib/client";
import { toDrillItem } from "@/lib/drill-snapshot";
import { errorKey, type ErrorKey } from "@/lib/errors";
import { cn } from "@/lib/utils";
import { asLang, DrillMeta, DrillSketchView, DrillText } from "./drill-card";

type Tips = Schemas["TrainingTipsOut"];
type Tip = Schemas["TrainingTip"];

const byId = new Map(DRILLS.map((d) => [d.id, d]));
const clock = (s: number | null | undefined) => (s == null ? null : `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`);

/**
 * Trainingstipps aus der Analyse (K21): one to three things to train next, from the team's last
 * analysed matches, each with its numbers, the scenes behind it, drills from the library and one
 * click to make it a session (with the scenes as a collection and, if wanted, a task for the
 * players). Honest when there is nothing to say yet.
 */
export function TrainingTips({
  orgId,
  teamId,
  onPlanned,
  heading = true,
  planHref,
  tasks = true,
}: {
  orgId: string;
  teamId: string;
  onPlanned: () => void;
  /** false where the page title already names the tips (Saison › Trainingstipps) */
  heading?: boolean;
  /** outside the training plan: where the planned unit is found */
  planHref?: string;
  /** «Als Aufgabe an die Spieler»: only while Teamleben (where tasks live) is on */
  tasks?: boolean;
}) {
  const t = useTranslations("training");
  const path = { org_id: orgId, team_id: teamId };
  const q = useQuery({
    queryKey: ["training-tips", teamId],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/teams/{team_id}/training-tips", { params: { path } })).data ?? null,
  });
  const focus = useQuery({
    queryKey: ["focus", teamId],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/teams/{team_id}/focus", { params: { path } })).data ?? [],
  });
  const data = q.data;
  const base = `/app/${orgId}/teams/${teamId}`;

  return (
    <section className="space-y-4" aria-labelledby={heading ? "tips-title" : undefined} aria-label={heading ? undefined : t("tipsTitle")} data-testid="training-tips">
      <div className="space-y-1">
        {heading && (
          <h2 id="tips-title" className="text-2xl">
            {t("tipsTitle")}
          </h2>
        )}
        {data && data.matches_analysed > 0 && <p className="text-[15px] text-muted">{t("tipsFrom", { n: data.matches_analysed })}</p>}
      </div>
      {q.isPending ? (
        <Skeleton className="h-40" />
      ) : !data ? (
        <p className="text-[15px] text-muted">{t("tipsError")}</p>
      ) : data.plan_required ? (
        <p className="text-[15px]">{t("tipsPlan")}</p>
      ) : data.matches_analysed === 0 ? (
        <div className="max-w-[60ch] space-y-3 border-l-4 border-ink bg-paper p-4" data-testid="tips-empty">
          <p className="font-slant m-0 text-[22px] leading-tight">{t("tipsNone")}</p>
          <p className="text-[15px] text-muted">{t("tipsNoneHint")}</p>
          <div className="flex flex-wrap gap-3">
            <Link href={`${base}/matches?upload=1`} className={buttonClass("primary", "sm")}>
              {t("uploadVideo")}
            </Link>
            <Link href={`/app/${orgId}/drills`} className={buttonClass("secondary", "sm")}>
              {t("browseDrills")}
            </Link>
          </div>
        </div>
      ) : data.tips.length === 0 ? (
        <div className="max-w-[60ch] space-y-2">
          <p className="text-[15px]">{t("tipsQuiet")}</p>
          <Link href={`/app/${orgId}/drills`} className="text-[15px] font-semibold underline underline-offset-4">
            {t("browseDrills")}
          </Link>
        </div>
      ) : (
        <ol className="space-y-4">
          {data.tips.map((tip, i) => (
            <TipItem
              key={tip.id}
              n={i + 1}
              tip={tip}
              data={data}
              orgId={orgId}
              teamId={teamId}
              planned={(focus.data ?? []).some((p) => p.insight_key === tip.key && p.match_id === tip.match_id && !p.closed_at)}
              onPlanned={onPlanned}
              planHref={planHref}
              tasks={tasks}
            />
          ))}
        </ol>
      )}
    </section>
  );
}

function TipItem({
  n,
  tip,
  data,
  orgId,
  teamId,
  planned,
  onPlanned,
  planHref,
  tasks,
}: {
  n: number;
  tip: Tip;
  data: Tips;
  orgId: string;
  teamId: string;
  planned: boolean;
  onPlanned: () => void;
  planHref?: string;
  tasks: boolean;
}) {
  const t = useTranslations("training");
  const td = useTranslations("drills");
  const format = useFormatter();
  const lang = asLang(useLocale());
  const text = useInsightText({});
  const [scenes, setScenes] = useState(false);
  const [plan, setPlan] = useState(false);
  const [openDrill, setOpenDrill] = useState<string | null>(null);
  const sentence = text({ id: tip.id, kind: "weakness", key: tip.key, params: tip.params as Insight["params"], score: tip.score, sample: tip.sample ?? 0, evidence: tip.evidence as Insight["evidence"] });
  const topic = (tip.topics[0] ?? "finishing") as Focus;
  const match = data.matches.find((m) => m.match_id === tip.match_id);
  const drills = tip.drills.map((id) => byId.get(id)).filter((d): d is Drill => !!d);
  const date = match ? format.dateTime(new Date(match.kickoff_at), { day: "numeric", month: "short" }) : null;

  return (
    <li className="border-t-2 border-foreground pt-3" data-testid="tip">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <span className="font-num text-2xl font-bold tabular-nums" aria-hidden>
          {n}
        </span>
        <h3 className="text-xl">{td(`focus_${topic}`)}</h3>
        <span className="text-[15px] text-muted">
          {t("tipMatches", { k: tip.matches, n: tip.of })}
          {date && ` · ${match?.opponent ? t("tipLatest", { opponent: match.opponent, date }) : t("tipLatestDate", { date })}`}
        </span>
      </div>
      <p className="mt-1 text-[17px]">{sentence}</p>

      <div className="mt-2 flex flex-wrap gap-x-5 gap-y-1">
        {tip.scenes.length > 0 ? (
          <button type="button" aria-expanded={scenes} onClick={() => setScenes((v) => !v)} className="inline-flex min-h-11 items-center gap-1 text-[15px] font-semibold underline underline-offset-4">
            {t("tipScenes", { n: tip.scenes.length })}
            <ChevronDown aria-hidden className={cn("size-4 transition-transform", scenes && "rotate-180")} />
          </button>
        ) : null}
        <Link href={`/app/${orgId}/matches/${tip.match_id}`} className="inline-flex min-h-11 items-center text-[15px] font-semibold underline underline-offset-4">
          {t("openMatch")}
        </Link>
      </div>
      {scenes && (
        <ol className="mb-2 flex flex-wrap gap-2">
          {tip.scenes.map((s, i) => (
            <li key={s.event_id}>
              <Link
                href={`/app/${orgId}/matches/${tip.match_id}?t=${Math.max(0, s.t_ms - 5000)}`}
                className="inline-flex min-h-11 items-center gap-1.5 px-3 text-[15px] font-semibold ring-1 ring-inset ring-foreground/25 hover:bg-surface"
              >
                <Play aria-hidden className="size-4" />
                {clock(s.clock_s) ? t("sceneAt", { period: s.period ?? 1, clock: clock(s.clock_s)! }) : t("sceneN", { n: i + 1 })}
              </Link>
            </li>
          ))}
        </ol>
      )}

      <h4 className="mt-3 text-[15px] font-semibold">{t("tipDrills")}</h4>
      <ul className="mt-2 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {drills.map((d) => (
          <li key={d.id} className="flex flex-col gap-2 bg-paper p-3 ring-1 ring-ink/10">
            <div className="grid grid-cols-[5.5rem_minmax(0,1fr)] gap-3">
              <DrillSketchView drill={d} lang={lang} />
              <div className="min-w-0">
                <p className="font-semibold leading-tight">{d.name[lang]}</p>
                <DrillMeta drill={d} className="mt-1 text-sm" />
              </div>
            </div>
            <button type="button" aria-expanded={openDrill === d.id} onClick={() => setOpenDrill(openDrill === d.id ? null : d.id)} className="inline-flex min-h-11 items-center gap-1 self-start text-[15px] font-semibold underline underline-offset-4">
              {td("howTo")}
              <ChevronDown aria-hidden className={cn("size-4 transition-transform", openDrill === d.id && "rotate-180")} />
            </button>
            {openDrill === d.id && <DrillText drill={d} lang={lang} />}
          </li>
        ))}
      </ul>
      <p className="mt-2 text-[15px]">
        <Link href={`/app/${orgId}/drills?focus=${tip.topics.join(",")}`} className="font-semibold underline underline-offset-4">
          {t("moreDrills", { focus: td(`focus_${topic}`) })}
        </Link>
      </p>

      <div className="mt-3">
        {planned && !plan ? (
          planHref ? (
            <p className="text-[15px] text-muted">
              {t("tipPlannedElsewhere")}{" "}
              <Link href={planHref} className="font-semibold text-foreground underline underline-offset-4">
                {t("planOpen")}
              </Link>
            </p>
          ) : (
            <p className="text-[15px] text-muted">{t("tipPlanned")}</p>
          )
        ) : plan ? (
          <PlanForm tip={tip} drills={drills} title={t("sessionTitle", { focus: td(`focus_${topic}`) })} orgId={orgId} teamId={teamId} onClose={() => setPlan(false)} onPlanned={onPlanned} planHref={planHref} tasks={tasks} />
        ) : (
          <Button onClick={() => setPlan(true)}>{t("tipPlan")}</Button>
        )}
      </div>
    </li>
  );
}

function PlanForm({
  tip,
  drills,
  title,
  orgId,
  teamId,
  onClose,
  onPlanned,
  planHref,
  tasks,
}: {
  tip: Tip;
  drills: Drill[];
  title: string;
  orgId: string;
  teamId: string;
  onClose: () => void;
  onPlanned: () => void;
  planHref?: string;
  tasks: boolean;
}) {
  const t = useTranslations("training");
  const tr = useTranslations();
  const locale = useLocale();
  const qc = useQueryClient();
  const nextWeek = new Date(Date.now() + 7 * 86400000).toISOString().slice(0, 10);
  const [day, setDay] = useState(nextWeek);
  const [chosen, setChosen] = useState<string[]>(drills.map((d) => d.id));
  const [playlist, setPlaylist] = useState(tip.scenes.length > 0);
  const [assignment, setAssignment] = useState(false);
  const [error, setError] = useState<ErrorKey | null>(null);
  const create = useMutation({
    mutationFn: async () => {
      const r = await api.POST("/v1/orgs/{org_id}/matches/{match_id}/focus", {
        params: { path: { org_id: orgId, match_id: tip.match_id } },
        body: {
          insight_key: tip.key,
          params: tip.params,
          title,
          session: { on_date: day, drills: drills.filter((d) => chosen.includes(d.id)).map((d) => toDrillItem(d, locale)) },
          playlist,
          assignment: tasks && playlist && assignment,
        },
      });
      if (r.error) throw r.error;
      return r.data;
    },
    onSuccess: () => {
      setError(null);
      void qc.invalidateQueries({ queryKey: ["focus", teamId] });
      onPlanned();
    },
    onError: (e) => setError(errorKey(e)),
  });
  const box = "flex min-h-11 items-center gap-3 text-[15px]";
  if (create.data)
    return (
      <Alert kind="success" className="py-2">
        {t("planDone")}{" "}
        {planHref && (
          <>
            <Link className="font-semibold underline underline-offset-4" href={planHref}>
              {t("planOpen")}
            </Link>{" "}
          </>
        )}
        {create.data.playlist_id && (
          <Link className="font-semibold underline underline-offset-4" href={`/app/${orgId}/playlists/${create.data.playlist_id}`}>
            {t("planOpenScenes")}
          </Link>
        )}
      </Alert>
    );
  return (
    <form
      className="max-w-xl space-y-3 bg-paper p-4 ring-1 ring-ink/15"
      aria-label={t("planTitle")}
      onSubmit={(e) => {
        e.preventDefault();
        create.mutate();
      }}
    >
      <p className="font-semibold">{t("planTitle")}</p>
      <label className="flex flex-col gap-1 text-sm">
        <span className="font-medium">{t("date")}</span>
        <input type="date" required value={day} onChange={(e) => setDay(e.target.value)} className="min-h-11 w-48 bg-raised px-2 ring-1 ring-inset ring-border" />
      </label>
      <fieldset className="space-y-1">
        <legend className="text-sm font-medium">{t("planDrills")}</legend>
        {drills.map((d) => (
          <label key={d.id} className={box}>
            <input type="checkbox" className="size-5" checked={chosen.includes(d.id)} onChange={() => setChosen((c) => (c.includes(d.id) ? c.filter((x) => x !== d.id) : [...c, d.id]))} />
            {d.name[asLang(locale)]} ({t("totalMinutes", { minutes: d.minutes })})
          </label>
        ))}
      </fieldset>
      <label className={box}>
        <input type="checkbox" className="size-5" checked={playlist} disabled={tip.scenes.length === 0} onChange={(e) => setPlaylist(e.target.checked)} />
        {t("planPlaylist")}
      </label>
      {tasks && (
        <label className={box}>
          <input type="checkbox" className="size-5" checked={assignment} disabled={!playlist} onChange={(e) => setAssignment(e.target.checked)} />
          {t("planAssignment")}
        </label>
      )}
      <p className="text-sm text-muted">{t("planWhy")}</p>
      {error && <Alert>{tr(`errors.${error}`)}</Alert>}
      <div className="flex flex-wrap gap-2">
        <Button type="submit" disabled={create.isPending || chosen.length === 0}>
          {t("planCreate")}
        </Button>
        <Button variant="ghost" onClick={onClose}>
          {t("planCancel")}
        </Button>
      </div>
    </form>
  );
}
