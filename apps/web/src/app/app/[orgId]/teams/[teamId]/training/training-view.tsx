"use client";

import type { Schemas } from "@handball/api-client";
import { DRILLS } from "@handball/tactics";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowDown, ArrowUp, Plus, X } from "lucide-react";
import { useFormatter, useLocale, useTranslations } from "next-intl";
import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Alert, Card, EmptyState, Sheet } from "@/components/ui/card";
import { api } from "@/lib/client";
import { move, toDrillItem, totalMinutes, type DrillItem } from "@/lib/drill-snapshot";
import { errorKey, type ErrorKey } from "@/lib/errors";

type Session = Schemas["TrainingSessionOut"];
type Focus = Schemas["FocusOut"];
type Status = NonNullable<Schemas["AttendanceRecord"]["status"]>;
const STATUSES: Status[] = ["present", "late", "excused", "injured", "absent"];
const control = "min-h-9 rounded-md border border-border bg-background px-2 text-sm";

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
  const [pick, setPick] = useState(DRILLS[0]?.id ?? "");
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
            {DRILLS.map((d) => (
              <option key={d.id} value={d.id}>{toDrillItem(d, locale).name} ({d.minutes} {t("min")})</option>
            ))}
          </select>
          <Button
            type="button"
            variant="secondary"
            onClick={() => {
              const d = DRILLS.find((x) => x.id === pick);
              if (d) setDrills((ds) => [...ds, toDrillItem(d, locale)]);
            }}
          >
            {t("addDrill")}
          </Button>
        </div>
      </div>
      <label className="block text-sm">
        <span className="block font-medium">{t("notes")}</span>
        <textarea name="notes" maxLength={5000} rows={2} defaultValue={initial?.notes ?? ""} className="w-full rounded-md bg-raised ring-1 ring-inset ring-border p-2" />
      </label>
      {error && <Alert>{tr(`errors.${error}`)}</Alert>}
      <Button type="submit" disabled={save.isPending}>{t("save")}</Button>
    </form>
  );
}

function AttendancePanel({ orgId, kind, id }: { orgId: string; kind: "session" | "match"; id: string }) {
  const t = useTranslations("training");
  const qc = useQueryClient();
  const path = { org_id: orgId, kind, target_id: id };
  const rows = useQuery({
    queryKey: ["attendance", kind, id],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/attendance/{kind}/{target_id}", { params: { path } })).data ?? [],
  });
  const save = useMutation({
    mutationFn: async (rec: Schemas["AttendanceRecord"]) =>
      api.PUT("/v1/orgs/{org_id}/attendance/{kind}/{target_id}", { params: { path }, body: { records: [rec] } }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["attendance", kind, id] }),
  });
  const list = rows.data ?? [];
  const yes = list.filter((r) => r.response === "yes").length;
  const no = list.filter((r) => r.response === "no").length;
  return (
    <div className="space-y-2">
      <p className="text-sm text-muted">{t("replies", { yes, no, open: list.length - yes - no })}</p>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-muted">
            <th className="py-1 font-normal">{t("player")}</th>
            <th className="py-1 font-normal">{t("reply")}</th>
            <th className="py-1 font-normal">{t("status")}</th>
          </tr>
        </thead>
        <tbody>
          {list.map((r) => (
            <tr key={r.player_id} className="border-t border-border/70">
              <td className="py-1">{r.number != null ? `#${r.number} ` : ""}{r.name}</td>
              <td className="py-1">{r.response ? t(`reply_${r.response}`) : "-"}</td>
              <td className="py-1">
                <select
                  aria-label={t("statusFor", { name: r.name })}
                  className={control}
                  value={r.status ?? ""}
                  onChange={(e) => save.mutate({ player_id: r.player_id, status: (e.target.value || null) as Status | null })}
                >
                  <option value="">-</option>
                  {STATUSES.map((s) => (
                    <option key={s} value={s}>{t(`status_${s}`)}</option>
                  ))}
                </select>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
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
            {s.location && ` · ${s.location}`} · {t("totalMinutes", { minutes: s.total_minutes })}
          </span>
        </div>
        {s.drills.length > 0 && <p className="text-sm">{s.drills.map((d) => d.name).join(" · ")}</p>}
        <div className="flex flex-wrap gap-3 text-sm">
          <a className="font-medium text-accent hover:underline" href={`/v1/orgs/${orgId}/sessions/${s.id}/pdf?lang=${locale}`}>{t("pdf")}</a>
          {canPlan && (
            <>
              <button type="button" className="font-medium text-accent hover:underline" onClick={() => setEditing(s.id)}>{t("edit")}</button>
              <button type="button" className="font-medium text-accent hover:underline" onClick={() => setOpen(open === s.id ? null : s.id)}>{t("attendance")}</button>
              <button type="button" className="text-error underline" onClick={() => remove.mutate(s.id)}>{t("delete")}</button>
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
        {canPlan && (
          <Button onClick={() => setEditing(editing === "new" ? null : "new")}>
            <Plus aria-hidden />
            {t("new")}
          </Button>
        )}
      </div>
      {editing === "new" && (
        <Card>
          <SessionForm orgId={orgId} teamId={teamId} onDone={done} />
        </Card>
      )}
      {error && <Alert>{tr(`errors.${error}`)}</Alert>}
      <section className="space-y-2" aria-labelledby="upcoming">
        <h3 id="upcoming" className="text-lg font-semibold">{t("upcoming")}</h3>
        {upcoming.length === 0 ? <EmptyState title={t("none")} /> : <ul className="border-t-2 border-foreground">{upcoming.map(item)}</ul>}
      </section>
      {past.length > 0 && (
        <section className="space-y-2" aria-labelledby="past">
          <h3 id="past" className="text-lg font-semibold">{t("past")}</h3>
          <ul className="border-t-2 border-foreground">{past.map(item)}</ul>
        </section>
      )}
      <FocusList focus={focus.data ?? []} />
      {canPlan && (
        <section className="grid gap-10 md:grid-cols-2 md:gap-x-12">
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
              <label className="flex min-h-10 cursor-pointer items-center gap-3 rounded-md px-1 text-[0.9375rem] ring-1 ring-inset ring-foreground/20 focus-within:ring-2 focus-within:ring-accent hover:ring-foreground/40">
                <span className="ml-1 rounded-sm bg-surface px-3 py-1 text-sm font-semibold">{tr("roster.csvChoose")}</span>
                <span className="min-w-0 truncate text-muted">{icsName ?? tr("roster.csvNone")}</span>
                <input name="ics" type="file" accept=".ics,text/calendar" required className="sr-only" aria-label={t("importTitle")} onChange={(e) => setIcsName(e.currentTarget.files?.[0]?.name ?? null)} />
              </label>
              <Button type="submit" variant="secondary">{t("import")}</Button>
              {imported && <p className="text-sm text-ok">{t("imported", imported)}</p>}
            </form>
          </Sheet>
        </section>
      )}
    </div>
  );
}
