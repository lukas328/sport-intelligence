"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { useConfirm } from "@/components/ui/confirm";
import { Input, Select } from "@/components/ui/field";
import { useShell } from "@/components/shell/context";
import { api } from "@/lib/client";
import { errorKey, type ErrorKey } from "@/lib/errors";
import { useTeamDrills, type TeamDrill } from "@/lib/team-drills";

const FOCI = ["finishing", "wings", "back_court", "pivot", "seven_m", "goalkeeping", "passing", "transition_defence", "fast_break", "defence", "powerplay"] as const;

/**
 * The club's own drills above the library: the team's own (editable) and those other teams
 * share in the club (read-only). Staff add one with "Neue Übung" and decide whether the club
 * may use it.
 */
export function ClubDrills({ orgId, focus }: { orgId: string; focus: string[] }) {
  const t = useTranslations("drills");
  const locale = useLocale();
  const { team, mode } = useShell();
  const staff = mode === "staff";
  const drills = useTeamDrills(orgId, team?.id, locale);
  const [editing, setEditing] = useState<TeamDrill | "new" | null>(null);
  const confirm = useConfirm();
  const qc = useQueryClient();
  const remove = useMutation({
    mutationFn: async (id: string) => {
      const r = await api.DELETE("/v1/orgs/{org_id}/drills/{drill_id}", { params: { path: { org_id: orgId, drill_id: id } } });
      if (r.error) throw r.error;
    },
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["team-drills"] }),
  });
  if (!team) return null;
  const club = (drills.data ?? []).filter((d) => d.source === "club" && (focus.length === 0 || d.focus.some((f) => focus.includes(f))));
  if (!staff && club.length === 0) return null;
  return (
    <section className="space-y-3" aria-labelledby="club-drills" data-testid="club-drills">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <h2 id="club-drills" className="text-xl">{t("own")}</h2>
        {staff && editing !== "new" && (
          <Button size="sm" onClick={() => setEditing("new")} data-testid="drill-new">
            {t("new")}
          </Button>
        )}
      </div>
      {editing === "new" && <DrillForm orgId={orgId} teamId={team.id} onDone={() => setEditing(null)} />}
      {club.length === 0 ? (
        editing !== "new" && <p className="text-sm text-muted">{t("ownNone")}</p>
      ) : (
        <ul className="border-t-2 border-foreground">
          {club.map((d) => (
            <li key={d.id} className="space-y-1.5 border-b border-foreground/15 py-4" data-testid="club-drill">
              <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                <h3 className="text-lg leading-tight">{d.name}</h3>
                <span className="text-[0.8125rem] text-muted">
                  {[...d.focus.filter((f) => (FOCI as readonly string[]).includes(f)).map((f) => t(`focus_${f as (typeof FOCI)[number]}`)), t("minutes", { minutes: d.minutes }), d.players && t("players", { players: d.players }), d.level && t(`level_${d.level}`)]
                    .filter(Boolean)
                    .join(" · ")}
                </span>
              </div>
              <p className="text-xs text-muted">{d.own ? (d.shared ? t("ownShared") : t("ownOnly")) : t("sharedBy", { team: d.team_name ?? "" })}</p>
              {d.setup && (
                <p className="text-sm">
                  <span className="font-semibold">{t("setup")}: </span>
                  {d.setup}
                </p>
              )}
              {d.coaching && (
                <p className="text-sm">
                  <span className="font-semibold">{t("coaching")}: </span>
                  {d.coaching}
                </p>
              )}
              {d.editable && (
                <div className="flex flex-wrap gap-3 pt-1 text-sm">
                  <button type="button" className="font-medium underline underline-offset-2" onClick={() => setEditing(editing === d ? null : d)}>
                    {t("edit")}
                  </button>
                  <button
                    type="button"
                    className="ml-auto text-muted underline underline-offset-2 hover:text-foreground"
                    onClick={async () => (await confirm({ title: t("deleteConfirm", { name: d.name }), confirm: t("delete"), danger: true })) && remove.mutate(d.id)}
                  >
                    {t("delete")}
                  </button>
                </div>
              )}
              {editing !== "new" && editing?.id === d.id && <DrillForm orgId={orgId} teamId={team.id} initial={d} onDone={() => setEditing(null)} />}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function DrillForm({ orgId, teamId, initial, onDone }: { orgId: string; teamId: string; initial?: TeamDrill; onDone: () => void }) {
  const t = useTranslations("drills");
  const tr = useTranslations();
  const qc = useQueryClient();
  const [error, setError] = useState<ErrorKey | null>(null);
  const [busy, setBusy] = useState(false);
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const body = {
      name: String(f.get("name")).trim(),
      minutes: Number(f.get("minutes")),
      players: String(f.get("players") ?? "").trim() || null,
      level: (String(f.get("level") ?? "") || null) as "basic" | "advanced" | null,
      focus: f.getAll("focus").map(String),
      setup: String(f.get("setup") ?? "").trim() || null,
      coaching: String(f.get("coaching") ?? "").trim() || null,
      shared: f.get("shared") === "on",
    };
    setBusy(true);
    const r = initial
      ? await api.PUT("/v1/orgs/{org_id}/drills/{drill_id}", { params: { path: { org_id: orgId, drill_id: initial.id } }, body })
      : await api.POST("/v1/orgs/{org_id}/teams/{team_id}/drills", { params: { path: { org_id: orgId, team_id: teamId } }, body });
    setBusy(false);
    if (r.error) return setError(errorKey(r.error));
    await qc.invalidateQueries({ queryKey: ["team-drills"] });
    onDone();
  }
  const area = "w-full rounded-sm bg-raised px-3 py-2 text-[0.9375rem] ring-1 ring-foreground/20 ring-inset focus-visible:ring-2 focus-visible:ring-accent focus-visible:outline-none";
  return (
    <form onSubmit={submit} className="space-y-3 border-l-2 border-foreground/20 py-1 pl-4" aria-label={initial ? t("editTitle", { name: initial.name }) : t("new")} data-testid="drill-form">
      <div className="grid gap-3 sm:grid-cols-[minmax(0,2fr)_repeat(3,minmax(0,1fr))]">
        <Input label={t("name")} name="name" required maxLength={120} defaultValue={initial?.name ?? ""} />
        <Input label={t("minutesLabel")} name="minutes" type="number" min={1} max={180} required defaultValue={initial?.minutes ?? 15} />
        <Input label={`${t("playersLabel")} (${tr("common.optional")})`} name="players" placeholder="6-12" maxLength={20} defaultValue={initial?.players ?? ""} />
        <Select label={t("levelLabel")} name="level" defaultValue={initial?.level ?? ""}>
          <option value="">-</option>
          <option value="basic">{t("level_basic")}</option>
          <option value="advanced">{t("level_advanced")}</option>
        </Select>
      </div>
      <fieldset>
        <legend className="text-sm font-medium">{t("focusLabel")}</legend>
        <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1">
          {FOCI.map((f) => (
            <label key={f} className="flex min-h-9 items-center gap-1.5 text-sm">
              <input type="checkbox" name="focus" value={f} defaultChecked={initial?.focus.includes(f)} className="size-4 accent-[var(--foreground)]" />
              {t(`focus_${f}`)}
            </label>
          ))}
        </div>
      </fieldset>
      <label className="block text-sm font-medium">
        {t("setup")}
        <textarea name="setup" rows={2} maxLength={2000} defaultValue={initial?.setup ?? ""} className={`mt-1 ${area}`} />
      </label>
      <label className="block text-sm font-medium">
        {t("coaching")}
        <textarea name="coaching" rows={2} maxLength={2000} defaultValue={initial?.coaching ?? ""} className={`mt-1 ${area}`} />
      </label>
      <label className="flex min-h-9 items-center gap-2 text-sm font-medium">
        <input type="checkbox" name="shared" defaultChecked={initial?.shared ?? false} className="size-4 accent-[var(--foreground)]" />
        {t("shareLabel")}
      </label>
      {error && <p className="text-sm text-error">{tr(`errors.${error}`)}</p>}
      <div className="flex flex-wrap gap-2">
        <Button type="submit" size="sm" loading={busy}>
          {t("save")}
        </Button>
        <Button type="button" size="sm" variant="quiet" onClick={onDone}>
          {t("cancel")}
        </Button>
      </div>
    </form>
  );
}
