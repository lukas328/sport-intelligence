"use client";

import type { Schemas } from "@handball/api-client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useFormatter, useTranslations } from "next-intl";
import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { useConfirm } from "@/components/ui/confirm";
import { Input, Select } from "@/components/ui/field";
import { api } from "@/lib/client";
import { errorKey, type ErrorKey } from "@/lib/errors";
import { holidaysBetween } from "@/lib/holidays";

type Slot = Schemas["TrainingSlotOut"];
type Season = Schemas["SeasonOut"];

const WEEKDAYS = [1, 2, 3, 4, 5, 6, 7] as const;

/**
 * The team's regular training times of a season ("Di 19:00 bis 20:30, Halle Seefeld") and the
 * one action that turns them into units: from today to the end of the season, public holidays
 * preselected to skip. Running it again creates nothing twice (the API keeps existing units).
 */
export function TrainingSlots({ orgId, teamId, season, onGenerated }: { orgId: string; teamId: string; season: Season; onGenerated: () => void }) {
  const t = useTranslations("slots");
  const tr = useTranslations();
  const format = useFormatter();
  const qc = useQueryClient();
  const confirm = useConfirm();
  const path = { org_id: orgId, team_id: teamId, season_id: season.id };
  const key = ["training-slots", teamId, season.id];
  const slots = useQuery({
    queryKey: key,
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/teams/{team_id}/seasons/{season_id}/training-slots", { params: { path } })).data ?? [],
  });
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState<ErrorKey | null>(null);
  const [result, setResult] = useState<{ created: number; kept: number; skipped: number } | null>(null);
  const today = new Date().toISOString().slice(0, 10);
  const from = today > season.starts_on ? today : season.starts_on;
  // only the holidays that fall on a training day matter
  const days = new Set((slots.data ?? []).map((s) => s.weekday));
  const isoDay = (d: string) => ((new Date(`${d}T12:00:00Z`).getUTCDay() + 6) % 7) + 1;
  const holidays = holidaysBetween(from, season.ends_on).filter((h) => days.has(isoDay(h.date)));
  const [skipOff, setSkipOff] = useState<string[]>([]);
  const [skipExtra, setSkipExtra] = useState<string[]>([]);
  const skip = [...new Set([...holidays.map((h) => h.date).filter((d) => !skipOff.includes(d)), ...skipExtra])];
  const setSkip = (f: (s: string[]) => string[]) => {
    const next = f(skip);
    setSkipOff(holidays.map((h) => h.date).filter((d) => !next.includes(d)));
    setSkipExtra(next.filter((d) => !holidays.some((h) => h.date === d)));
  };
  const [extra, setExtra] = useState("");
  const dayLabel = (iso: string) => format.dateTime(new Date(`${iso}T12:00:00`), { weekday: "short", day: "numeric", month: "short" });
  const weekday = (n: number) => format.dateTime(new Date(Date.UTC(2024, 0, n, 12)), { weekday: "short" }); // 1 Jan 2024 was a Monday

  const remove = useMutation({
    mutationFn: async (id: string) => {
      const r = await api.DELETE("/v1/orgs/{org_id}/training-slots/{slot_id}", { params: { path: { org_id: orgId, slot_id: id } } });
      if (r.error) throw r.error;
    },
    onSuccess: () => void qc.invalidateQueries({ queryKey: key }),
    onError: (e) => setError(errorKey(e)),
  });
  const generate = useMutation({
    mutationFn: async () => {
      const r = await api.POST("/v1/orgs/{org_id}/teams/{team_id}/seasons/{season_id}/training-slots/generate", {
        params: { path },
        body: { from, to: season.ends_on, skip_dates: skip },
      });
      if (r.error) throw r.error;
      return r.data;
    },
    onSuccess: (r) => {
      setResult({ created: r.created, kept: r.kept, skipped: r.skipped });
      onGenerated();
    },
    onError: (e) => setError(errorKey(e)),
  });

  async function add(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const r = await api.POST("/v1/orgs/{org_id}/teams/{team_id}/seasons/{season_id}/training-slots", {
      params: { path },
      body: {
        weekday: Number(f.get("weekday")),
        start_time: String(f.get("start_time")),
        duration_min: Number(f.get("duration_min")),
        location: String(f.get("location") ?? "").trim() || null,
        title: String(f.get("title") ?? "").trim() || null,
      },
    });
    if (r.error) return setError(errorKey(r.error));
    setError(null);
    setAdding(false);
    await qc.invalidateQueries({ queryKey: key });
  }

  const list: Slot[] = slots.data ?? [];
  return (
    <section className="space-y-3" aria-labelledby="slots-title" data-testid="training-slots">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <h3 id="slots-title" className="text-lg font-semibold">
          {t("title", { season: season.label })}
        </h3>
        {!adding && (
          <Button size="sm" variant="secondary" onClick={() => setAdding(true)}>
            {t("add")}
          </Button>
        )}
      </div>
      {list.length === 0 && !adding && <p className="text-sm text-muted">{t("none")}</p>}
      {list.length > 0 && (
        <ul className="border-t-2 border-foreground">
          {list.map((s) => (
            <li key={s.id} className="flex flex-wrap items-baseline gap-x-3 gap-y-1 border-b border-foreground/15 py-2.5" data-testid="training-slot">
              <span className="w-10 font-semibold">{weekday(s.weekday)}</span>
              <span className="font-score tabular-nums">
                {s.start_time.slice(0, 5)} {t("to")} {s.end_time.slice(0, 5)}
              </span>
              <span className="min-w-0 flex-1 text-sm text-muted">{[s.title, s.location].filter(Boolean).join(" · ")}</span>
              <button
                type="button"
                className="text-sm text-muted underline underline-offset-2 hover:text-foreground"
                onClick={async () => (await confirm({ title: t("deleteConfirm"), confirm: t("delete"), danger: true })) && remove.mutate(s.id)}
              >
                {t("delete")}
              </button>
            </li>
          ))}
        </ul>
      )}
      {adding && (
        <form onSubmit={add} className="space-y-3 border-l-2 border-foreground/20 py-1 pl-4" aria-label={t("add")}>
          <div className="grid gap-3 sm:grid-cols-5">
            <Select label={t("weekday")} name="weekday" defaultValue="2">
              {WEEKDAYS.map((n) => (
                <option key={n} value={n}>
                  {format.dateTime(new Date(Date.UTC(2024, 0, n, 12)), { weekday: "long" })}
                </option>
              ))}
            </Select>
            <Input label={t("start")} name="start_time" type="time" required defaultValue="19:00" />
            <Input label={t("duration")} name="duration_min" type="number" min={15} max={300} step={15} required defaultValue={90} />
            <Input label={`${t("location")} (${tr("common.optional")})`} name="location" maxLength={120} />
            <Input label={`${t("titleLabel")} (${tr("common.optional")})`} name="title" maxLength={120} />
          </div>
          <div className="flex flex-wrap gap-2">
            <Button type="submit" size="sm">
              {t("save")}
            </Button>
            <Button type="button" size="sm" variant="quiet" onClick={() => setAdding(false)}>
              {t("cancel")}
            </Button>
          </div>
        </form>
      )}
      {list.length > 0 && from <= season.ends_on && (
        <div className="space-y-2 border-t border-foreground/15 pt-3" data-testid="slots-generate">
          <p className="text-sm">{t("generateHint", { from: dayLabel(from), to: dayLabel(season.ends_on) })}</p>
          <fieldset>
            <legend className="text-sm font-medium">{t("skip")}</legend>
            <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1">
              {[...new Set([...holidays.map((h) => h.date), ...skip])].sort().map((d) => {
                const h = holidays.find((x) => x.date === d);
                return (
                  <label key={d} className="flex min-h-9 items-center gap-1.5 text-sm">
                    <input
                      type="checkbox"
                      className="size-4 accent-[var(--foreground)]"
                      checked={skip.includes(d)}
                      onChange={(e) => setSkip((s) => (e.target.checked ? [...s, d] : s.filter((x) => x !== d)))}
                    />
                    {dayLabel(d)}
                    {h && <span className="text-muted">{` · ${t(`holiday_${h.key}`)}`}</span>}
                  </label>
                );
              })}
            </div>
            <div className="mt-2 flex flex-wrap items-end gap-2">
              <Input label={t("skipAdd")} type="date" min={from} max={season.ends_on} value={extra} onChange={(e) => setExtra(e.target.value)} />
              <Button type="button" size="sm" variant="secondary" disabled={!extra} onClick={() => (setSkip((s) => [...new Set([...s, extra])]), setExtra(""))}>
                {t("skipAddButton")}
              </Button>
            </div>
          </fieldset>
          <Button onClick={() => generate.mutate()} loading={generate.isPending} data-testid="slots-generate-button">
            {t("generate")}
          </Button>
          {result && (
            <p className="text-sm" role="status">
              {t("generated", result)}
            </p>
          )}
        </div>
      )}
      {error && <p className="text-sm text-error">{tr(`errors.${error}`)}</p>}
    </section>
  );
}
