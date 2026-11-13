"use client";

import type { Schemas } from "@handball/api-client";
import { DRILLS } from "@handball/tactics";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowDown, ArrowUp, Plus, X } from "lucide-react";
import { useFormatter, useLocale, useTranslations } from "next-intl";
import Link from "next/link";
import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { useConfirm } from "@/components/ui/confirm";
import { Alert, EmptyState, Sheet } from "@/components/ui/card";
import { AttendancePanel } from "@/components/team/attendance-panel";
import { TrainingSlots } from "@/components/training/training-slots";
import { api } from "@/lib/client";
import { move, toDrillItem, totalMinutes, type DrillItem } from "@/lib/drill-snapshot";
import { drillItemOf, useTeamDrills } from "@/lib/team-drills";
import { errorKey, type ErrorKey } from "@/lib/errors";

type Session = Schemas["TrainingSessionOut"];
type Focus = Schemas["FocusOut"];
const control = "min-h-9 border border-border bg-background px-2 text-sm";

function SessionForm({
  orgId,
  teamId,
  initial,
  onDone,
}: {
  orgId: string;
  teamId: string;
  initial?: Session;
  onDone: () => void;
}) {
  const t = useTranslations("training");
  const tr = useTranslations();
  const locale = useLocale();
  const [drills, setDrills] = useState<DrillItem[]>(initial?.drills ?? []);
  // the team's list (own and club drills first, then the library); the static library until it loads
  const teamDrills = useTeamDrills(orgId, teamId, locale);
  const choices: DrillItem[] = teamDrills.data?.length ? teamDrills.data.map(drillItemOf) : DRILLS.map((d) => toDrillItem(d, locale));
  const [pick, setPick] = useState("");
  const [error, setError] = useState<ErrorKey | null>(null);
  const save = useMutation({
    mutationFn: async (body: Schemas["TrainingSessionIn"]) => {
      const r = initial
        ? await api.PUT("/v1/orgs/{org_id}/sessions/{session_id}", { params: { path: { org_id: orgId, session_id: initial.id } }, body })
        : await api.POST("/v1/orgs/{org_id}/teams/{team_id}/sessions", { params: { path: { org_id: orgId, team_id: teamId } }, body });
      if (r.error) throw r.error;
    },
    onSuccess: onDone,
    onError: (e) => setError(errorKey(e)),
  });
  const submit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const day = String(f.get("on_date"));
    const time = String(f.get("time") || "");
    save.mutate({
      on_date: day,
      starts_at: time ? new Date(`${day}T${time}`).toISOString() : null,
      title: String(f.get("title") || "") || null,
      location: String(f.get("location") || "") || null,
      notes: String(f.get("notes") || "") || null,
      drills,
    });
  };
  const startTime = initial?.starts_at ? new Date(initial.starts_at).toTimeString().slice(0, 5) : "";
  return (
    <form onSubmit={submit} className="space-y-3" aria-label={initial ? t("edit") : t("new")}>
      <div className="flex flex-wrap gap-3">
        <label className="text-sm">
          <span className="block font-medium">{t("date")}</span>
          <input name="on_date" type="date" required defaultValue={initial?.on_date ?? ""} className={control} />
        </label>
        <label className="text-sm">
          <span className="block font-medium">{t("time")}</span>
          <input name="time" type="time" defaultValue={startTime} className={control} />
        </label>
        <label className="text-sm">
          <span className="block font-medium">{t("titleLabel")}</span>
          <input name="title" maxLength={120} defaultValue={initial?.title ?? ""} className={control} />
        </label>
        <label className="text-sm">
          <span className="block font-medium">{t("location")}</span>
          <input name="location" maxLength={160} defaultValue={initial?.location ?? ""} className={control} />
        </label>
      </div>
      <div className="space-y-2">
        <p className="text-sm font-medium">{t("drills", { minutes: totalMinutes(drills) })}</p>
        <ol className="space-y-1">
          {drills.map((d, i) => (
            <li key={`${d.drill_id}-${i}`} className="flex flex-wrap items-center gap-2 text-sm">
              <span className="min-w-0 flex-1">{i + 1}. {d.name}</span>
              <label className="flex items-center gap-1">
                <span className="sr-only">{t("minutes")}</span>
                <input
                  type="number"
                  min={1}
                  max={180}
                  value={d.minutes}
                  onChange={(e) => setDrills((ds) => ds.map((x, j) => (j === i ? { ...x, minutes: Number(e.target.value) || 1 } : x)))}
                  className={`${control} w-16`}
                />
                {t("min")}
              </label>
              <button type="button" aria-label={t("up")} className="px-1" onClick={() => setDrills((ds) => move(ds, i, -1))}><ArrowUp aria-hidden className="size-4" /></button>
              <button type="button" aria-label={t("down")} className="px-1" onClick={() => setDrills((ds) => move(ds, i, 1))}><ArrowDown aria-hidden className="size-4" /></button>
              <button type="button" aria-label={t("remove")} className="px-1 text-error" onClick={() => setDrills((ds) => ds.filter((_, j) => j !== i))}><X aria-hidden className="size-4" /></button>
            </li>
          ))}
        </ol>
        <div className="flex flex-wrap gap-2">
          <select aria-label={t("addDrill")} className={control} value={pick} onChange={(e) => setPick(e.target.value)}>
            {choices.map((d) => (
              <option key={d.drill_id} value={d.drill_id}>{d.name} ({d.minutes} {t("min")})</option>
            ))}
          </select>
          <Button
            type="button"
            variant="secondary"
            onClick={() => {
              const d = choices.find((x) => x.drill_id === (pick || choices[0]?.drill_id));
              if (d) setDrills((ds) => [...ds, d]);
            }}
          >
            {t("addDrill")}
          </Button>
        </div>
      </div>
      <label className="block text-sm">
        <span className="block font-medium">{t("notes")}</span>
        <textarea name="notes" maxLength={5000} rows={2} defaultValue={initial?.notes ?? ""} className="w-full bg-raised ring-1 ring-inset ring-border p-2" />
      </label>
      {error && <Alert>{tr(`errors.${error}`)}</Alert>}
      <Button type="submit" disabled={save.isPending}>{t("save")}</Button>
    </form>
  );
}

function FocusList({ focus }: { focus: Focus[] }) {
  const t = useTranslations("training");
  const tm = useTranslations("matrix");
  const fmt = (metric: string, v: number | null | undefined, perMatch: number | null | undefined) => {
    if (v == null) return "-";
    if (metric.endsWith("_pct")) return `${Math.round(v * 100)} %`;
    return perMatch != null ? t("perMatch", { n: perMatch }) : String(v);
  };
  if (focus.length === 0) return null;
  return (
    <section className="space-y-2" aria-labelledby="focus-title">
      <h3 id="focus-title" className="text-lg font-semibold">{t("focusTitle")}</h3>
      <p className="text-sm text-muted">{t("focusHint")}</p>
      <ul className="border-t-2 border-foreground">
        {focus.map((f) => {
          const fu = f.followup;
          return (
            <li key={f.id} className="space-y-1 border-b border-foreground/15 py-3 text-sm">
                <p className="font-medium">{f.metric ? tm(`m_${f.metric}`) : f.insight_key}</p>
                {fu ? (
                  <>
                    <p>
                      {t("before", { n: fu.before.matches })}: {fmt(fu.metric, fu.before.value, fu.before.per_match)} ·{" "}
                      {t("after", { n: fu.after.matches })}: {fmt(fu.metric, fu.after.value, fu.after.per_match)}
                      {fu.trend && ` · ${t(`trend_${fu.trend}`)}`}
                    </p>
                    <p className="text-xs text-muted">{fu.small_sample ? t("smallSample") : t("observation")}</p>
                  </>
                ) : (
                  <p className="text-muted">{t("noFollowup")}</p>
                )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}

export function TrainingView({ orgId, teamId, canPlan }: { orgId: string; teamId: string; canPlan: boolean }) {
  const t = useTranslations("training");
  const tr = useTranslations();
  const locale = useLocale();
  const format = useFormatter();
  const qc = useQueryClient();
  const team = { org_id: orgId, team_id: teamId };
  const [editing, setEditing] = useState<string | "new" | null>(null);
  const [open, setOpen] = useState<string | null>(null);
  const [calendar, setCalendar] = useState<string | null>(null);
  const [imported, setImported] = useState<{ created: number; updated: number } | null>(null);
  const [icsName, setIcsName] = useState<string | null>(null);
  const [error, setError] = useState<ErrorKey | null>(null);
  const sessions = useQuery({
    queryKey: ["sessions", teamId],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/teams/{team_id}/sessions", { params: { path: team } })).data ?? [],
  });
  // who is out (injured, away): the staff plan the unit with it; names from the current squad
  const statuses = useQuery({
    queryKey: ["player-statuses", teamId],
    enabled: canPlan,
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/teams/{team_id}/player-statuses", { params: { path: team } })).data ?? [],
  });
  const squad = useQuery({
    queryKey: ["squad-names", teamId],
    enabled: canPlan && (statuses.data?.length ?? 0) > 0,
    queryFn: async () => {
      const tm = (await api.GET("/v1/orgs/{org_id}/teams/{team_id}", { params: { path: team } })).data;
      if (!tm?.current_season) return [];
      return (await api.GET("/v1/orgs/{org_id}/teams/{team_id}/seasons/{season_id}/roster", { params: { path: { ...team, season_id: tm.current_season.id } } })).data ?? [];
    },
  });
  const outOn = (day: string) =>
    (statuses.data ?? [])
      .filter((x) => x.until == null || x.until >= day)
      .map((x) => {
        const p = (squad.data ?? []).find((r) => r.player_id === x.player_id);
        return p ? `${p.first_name} ${p.last_name} (${tr(`playerStatus.${x.kind}`).toLowerCase()})` : null;
      })
      .filter((x): x is string => x != null);
  const confirm = useConfirm();
  const teamInfo = useQuery({
    queryKey: ["team-info", teamId],
    enabled: canPlan,
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/teams/{team_id}", { params: { path: team } })).data ?? null,
  });
  const season = teamInfo.data?.current_season ?? null;
  const focus = useQuery({
    queryKey: ["focus", teamId],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/teams/{team_id}/focus", { params: { path: team } })).data ?? [],
  });
  const link = useMutation({
    mutationFn: async () => {
      const r = await api.POST("/v1/orgs/{org_id}/teams/{team_id}/calendar", { params: { path: team } });
      if (r.error) throw r.error;
      return r.data.url;
    },
    onSuccess: (url) => setCalendar(url),
    onError: (e) => setError(errorKey(e)),
  });
  const remove = useMutation({
    mutationFn: async (id: string) => api.DELETE("/v1/orgs/{org_id}/sessions/{session_id}", { params: { path: { org_id: orgId, session_id: id } } }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["sessions", teamId] }),
  });
  const importIcs = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const file = (e.currentTarget.elements.namedItem("ics") as HTMLInputElement).files?.[0];
    if (!file) return;
    const body = new FormData();
    body.append("file", file);
    const r = await api.POST("/v1/orgs/{org_id}/teams/{team_id}/sessions/import", {
      params: { path: team },
      body: body as unknown as { file: string },
      bodySerializer: (x) => x as unknown as FormData,
    });
    if (r.error || !r.data) {
      setError(errorKey(r.error));
      return;
    }
    setImported(r.data as { created: number; updated: number });
    void qc.invalidateQueries({ queryKey: ["sessions", teamId] });
  };
  const today = new Date().toISOString().slice(0, 10);
  const all = sessions.data ?? [];
  const upcoming = all.filter((s) => s.on_date >= today);
  const inFourWeeks = new Date(Date.now() + 28 * 86400_000).toISOString().slice(0, 10);
  const inTwoWeeks = new Date(Date.now() + 14 * 86400_000).toISOString().slice(0, 10);
  // at least the next unit, even when it is further away
  const soon = upcoming.filter((s, i) => i === 0 || s.on_date <= inFourWeeks);
  const [allUpcoming, setAllUpcoming] = useState(false);
  const past = all.filter((s) => s.on_date < today).reverse().slice(0, 10);
  const done = () => {
    setEditing(null);
    void qc.invalidateQueries({ queryKey: ["sessions", teamId] });
  };

  const item = (s: Session) => (
    <li key={s.id} className="space-y-2 border-b border-foreground/15 py-4">
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <h3 className="font-semibold">{s.title || t("defaultTitle")}</h3>
          <span className="text-sm text-muted">
            {format.dateTime(new Date(`${s.on_date}T12:00:00`), { weekday: "short", day: "numeric", month: "short" })}
            {s.starts_at && `, ${format.dateTime(new Date(s.starts_at), { hour: "2-digit", minute: "2-digit" })}`}
            {s.location && ` · ${s.location}`} · {s.total_minutes > 0 ? t("totalMinutes", { minutes: s.total_minutes }) : t("empty")}
          </span>
        </div>
        {s.drills.length > 0 && <p className="text-sm">{s.drills.map((d) => d.name).join(" · ")}</p>}
        {/* who is out only where it changes the plan: the next two weeks */}
        {canPlan && s.on_date >= today && s.on_date <= inTwoWeeks && outOn(s.on_date).length > 0 && (
          <p className="text-sm" data-testid="session-out">
            <span className="font-semibold">{t("outOnDay", { n: outOn(s.on_date).length })}</span> <span className="text-muted">{outOn(s.on_date).join(", ")}</span>
          </p>
        )}
        <div className="flex flex-wrap gap-3 text-sm">
          <a className="font-medium text-accent hover:underline" href={`/v1/orgs/${orgId}/sessions/${s.id}/pdf?lang=${locale}`}>{t("pdf")}</a>
          {canPlan && (
            <>
              <button type="button" className="font-medium text-accent hover:underline" onClick={() => setEditing(s.id)}>{t("edit")}</button>
              <button type="button" className="font-medium text-accent hover:underline" onClick={() => setOpen(open === s.id ? null : s.id)}>{t("attendance")}</button>
              {/* apart from the everyday actions, and asked once: a thumb slip must not delete a unit */}
              <button
                type="button"
                className="ml-auto text-muted underline underline-offset-2 hover:text-foreground"
                onClick={async () => (await confirm({ title: t("deleteConfirm", { title: s.title || t("defaultTitle") }), confirm: t("delete"), danger: true })) && remove.mutate(s.id)}
              >
                {t("delete")}
              </button>
            </>
          )}
        </div>
        {editing === s.id && <SessionForm orgId={orgId} teamId={teamId} initial={s} onDone={done} />}
        {open === s.id && <AttendancePanel orgId={orgId} kind="session" id={s.id} />}
    </li>
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="sr-only">{t("title")}</h2>
        <p className="max-w-xl text-sm text-muted">{t("hint")}</p>
        {/* the drill library left the navigation with the training plan; this is its way in */}
        <Link href={`/app/${orgId}/drills`} className="text-sm font-medium underline underline-offset-4 hover:text-foreground">
          {tr("shell.drills")}
        </Link>
        {canPlan && (
          <Button onClick={() => setEditing(editing === "new" ? null : "new")}>
            <Plus aria-hidden />
            {t("new")}
          </Button>
        )}
      </div>
      {editing === "new" && (
        <section className="border-t-2 border-foreground pt-4">
          <SessionForm orgId={orgId} teamId={teamId} onDone={done} />
        </section>
      )}
      {error && <Alert>{tr(`errors.${error}`)}</Alert>}
      {canPlan && season && (
        <TrainingSlots orgId={orgId} teamId={teamId} season={season} onGenerated={() => void qc.invalidateQueries({ queryKey: ["sessions", teamId] })} />
      )}
      <section className="space-y-2" aria-labelledby="upcoming">
        <h3 id="upcoming" className="text-lg font-semibold">{t("upcoming")}</h3>
        {upcoming.length === 0 ? (
          <EmptyState
            title={t("none")}
            action={canPlan && editing !== "new" ? <Button variant="secondary" size="sm" onClick={() => setEditing("new")}>{t("planFirst")}</Button> : undefined}
          >
            {canPlan ? t("noneHint") : null}
          </EmptyState>
        ) : (
          <>
            {/* units made for a whole season would fill the page: the next four weeks, the rest folded */}
            <ul className="border-t-2 border-foreground">{(allUpcoming ? upcoming : soon).map(item)}</ul>
            {upcoming.length > soon.length && (
              <button type="button" className="min-h-9 text-sm font-medium underline underline-offset-2" onClick={() => setAllUpcoming((v) => !v)}>
                {allUpcoming ? t("upcomingLess") : t("upcomingMore", { n: upcoming.length - soon.length })}
              </button>
            )}
          </>
        )}
      </section>
      {past.length > 0 && (
        <section className="space-y-2" aria-labelledby="past">
          <h3 id="past" className="text-lg font-semibold">{t("past")}</h3>
          <ul className="border-t-2 border-foreground">{past.map(item)}</ul>
        </section>
      )}
      <FocusList focus={focus.data ?? []} />
      {canPlan && (
        // the calendar is a schedule tool: folded, so the page stays about the units
        <details className="border-t border-foreground/15 pt-3">
        <summary className="cursor-pointer font-medium">{t("calendarTools")}</summary>
        <section className="mt-4 grid gap-10 md:grid-cols-2 md:gap-x-12">
          <Sheet className="space-y-2">
            <h3 className="text-lg">{t("calendar")}</h3>
            <p className="text-sm text-muted">{t("calendarHint")}</p>
            {calendar ? (
              <input readOnly value={calendar} aria-label={t("calendar")} className={`${control} w-full`} onFocus={(e) => e.currentTarget.select()} />
            ) : (
              <Button variant="secondary" onClick={() => link.mutate()}>{t("calendarCreate")}</Button>
            )}
          </Sheet>
          <Sheet>
            <form onSubmit={importIcs} className="space-y-3">
              <h3 className="text-lg">{t("importTitle")}</h3>
              <p className="text-sm text-muted">{t("importHint")}</p>
              <label className="flex min-h-10 cursor-pointer items-center gap-3 px-1 text-[0.9375rem] ring-1 ring-inset ring-foreground/20 focus-within:ring-2 focus-within:ring-accent hover:ring-foreground/40">
                <span className="ml-1 bg-surface px-3 py-1 text-sm font-semibold">{tr("roster.csvChoose")}</span>
                <span className="min-w-0 truncate text-muted">{icsName ?? tr("roster.csvNone")}</span>
                <input name="ics" type="file" accept=".ics,text/calendar" required className="sr-only" aria-label={t("importTitle")} onChange={(e) => setIcsName(e.currentTarget.files?.[0]?.name ?? null)} />
              </label>
              <Button type="submit" variant="secondary">{t("import")}</Button>
              {imported && <p className="text-sm text-ok">{t("imported", imported)}</p>}
            </form>
          </Sheet>
        </section>
        </details>
      )}
    </div>
  );
}
