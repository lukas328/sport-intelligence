"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useOptionalShell } from "@/components/shell/context";
import { useId, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { KitFields } from "@/components/domain/kit-fields";
import { Alert } from "@/components/ui/card";
import { Input, Select } from "@/components/ui/field";
import { cn } from "@/lib/utils";
import { api } from "@/lib/client";
import { errorKey, fieldErrors, type ErrorKey } from "@/lib/errors";
import type { Kits } from "@/lib/kit";

const FORMATS = ["adult_2x30", "youth_2x25", "youth_2x20", "mini", "tournament"] as const;
const KIT_DEFAULTS: Kits = {
  own: "#0b6bcb",
  own_gk: "#f59e0b",
  opponent: "#dc2626",
  opponent_gk: "#16a34a",
  referee: null,
};

function localNow(): string {
  const d = new Date();
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 16);
}

export function NewMatchForm({ orgId, teamId }: { orgId: string; teamId: string }) {
  const t = useTranslations();
  const router = useRouter();
  const listId = useId();
  const [error, setError] = useState<ErrorKey | null>(null);
  const [fields, setFields] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [kits, setKits] = useState(KIT_DEFAULTS);
  // the opponent's colour counts as said only when somebody picked it (never a default: unknown stays unknown)
  const [opponentPicked, setOpponentPicked] = useState(false);
  const shell = useOptionalShell();
  const trainingAllowed = shell?.teams.find((x) => x.id === teamId)?.team_features ?? false;
  const [training, setTraining] = useState(false);
  const [away, setAway] = useState(false);
  const [format, setFormat] = useState<string | null>(null);
  const team = useQuery({
    queryKey: ["team", orgId, teamId],
    queryFn: async () =>
      (await api.GET("/v1/orgs/{org_id}/teams/{team_id}", { params: { path: { org_id: orgId, team_id: teamId } } })).data,
  });
  const chosenFormat = format ?? (team.data?.is_youth ? "youth_2x25" : "adult_2x30");
  const opponents = useQuery({
    queryKey: ["opponents", orgId],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/opponents", { params: { path: { org_id: orgId } } })).data ?? [],
  });

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const name = String(f.get("opponent") ?? "").trim();
    const known = opponents.data?.find((o) => o.name.toLowerCase() === name.toLowerCase());
    const optional = (k: string) => String(f.get(k) ?? "").trim() || null;
    setBusy(true);
    const { data, error } = await api.POST("/v1/orgs/{org_id}/teams/{team_id}/matches", {
      params: { path: { org_id: orgId, team_id: teamId } },
      body: {
        ...(training ? { kind: "training" as const } : known ? { opponent_id: known.id } : { opponent_name: name }),
        kickoff_at: new Date(String(f.get("kickoff"))).toISOString(),
        is_home: !away,
        competition: optional("competition"),
        venue: optional("venue"),
        kit_own: kits.own,
        kit_own_gk: kits.own_gk,
        ...(opponentPicked ? { kit_opponent: kits.opponent } : {}),
        kit_opponent_gk: kits.opponent_gk,
        kit_referee: kits.referee,
        format: chosenFormat as (typeof FORMATS)[number],
      },
    });
    setBusy(false);
    if (error || !data) {
      setFields(fieldErrors(error));
      return setError(errorKey(error));
    }
    router.push(`/app/${orgId}/matches/${data.id}`);
  }

  const segment = (on: boolean) =>
    cn(
      "flex-1 cursor-pointer px-4 py-1.5 text-center text-sm font-medium transition-colors has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-accent",
      on ? "bg-raised text-foreground ring-1 ring-border/60" : "text-muted hover:text-foreground",
    );
  return (
    <div>
      {error && <Alert className="mb-4">{t(`errors.${error}`)}</Alert>}
      <form onSubmit={submit} className="grid gap-4 sm:grid-cols-2" aria-label={t("matches.new")}>
        {/* a training only with the team functions (UX test B37): the product's scope is the match */}
        {trainingAllowed && (
        <fieldset className="sm:col-span-2">
          <legend className="sr-only">{t("matchForm.isTraining")}</legend>
          <div className="flex max-w-xs gap-0.5 bg-surface p-1">
            <label className={segment(!training)}>
              <input type="radio" name="kind" className="sr-only" checked={!training} onChange={() => setTraining(false)} />
              {t("matches.kindMatch")}
            </label>
            <label className={segment(training)}>
              <input type="radio" name="kind" className="sr-only" checked={training} onChange={() => setTraining(true)} />
              {t("matches.kindTraining")}
            </label>
          </div>
        </fieldset>
        )}
        {!training && (
          <div className="sm:col-span-2">
            <Input
              label={t("matches.opponent")}
              name="opponent"
              required
              list={listId}
              placeholder={t("matches.opponentPlaceholder")}
              autoComplete="off"
              error={fields.opponent_name}
              className="min-h-12 text-base"
            />
            <datalist id={listId}>
              {opponents.data?.map((o) => <option key={o.id} value={o.name} />)}
            </datalist>
          </div>
        )}
        <Input label={t("matches.kickoff")} name="kickoff" type="datetime-local" required defaultValue={localNow()} />
        {!training ? (
          <fieldset className="space-y-1">
            <legend className="mb-1 block text-[0.9375rem] font-medium">{t("matches.homeAway")}</legend>
            <div className="flex gap-0.5 bg-surface p-1">
              <label className={segment(!away)}>
                <input type="radio" name="side" className="sr-only" checked={!away} onChange={() => setAway(false)} />
                {t("matches.homeShort")}
              </label>
              <label className={segment(away)}>
                <input type="radio" name="side" className="sr-only" checked={away} onChange={() => setAway(true)} />
                {t("matches.awayShort")}
              </label>
            </div>
          </fieldset>
        ) : (
          <span />
        )}
        {/* opponent and date are enough; the rest can be said later (UX test H07) */}
        <details className="sm:col-span-2">
          <summary className="min-h-11 cursor-pointer content-center text-[15px] font-semibold">{t("matches.moreDetails")}</summary>
          <div className="mt-3 grid gap-4 sm:grid-cols-2">
            <Input label={`${t("matches.competition")} (${t("common.optional")})`} name="competition" />
            <Input label={`${t("matches.venue")} (${t("common.optional")})`} name="venue" />
            <Select label={t("matchForm.format")} name="format" value={chosenFormat} onChange={(e) => setFormat(e.target.value)}>
              {FORMATS.map((k) => (
                <option key={k} value={k}>
                  {t(`matchForm.format_${k}`)}
                </option>
              ))}
            </Select>
            <fieldset className="sm:col-span-2">
              <legend className="mb-2 block text-[0.9375rem] font-medium">{t("matches.kits")}</legend>
              <KitFields
                kits={kits}
                onChange={(next) => {
                  if (next.opponent !== kits.opponent) setOpponentPicked(true);
                  setKits(next);
                }}
              />
            </fieldset>
          </div>
        </details>
        <div className="pt-2 sm:col-span-2">
          <Button type="submit" size="lg" loading={busy}>
            {t("matches.create")}
          </Button>
        </div>
      </form>
    </div>
  );
}
