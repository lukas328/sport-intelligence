"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useId, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Alert, Card } from "@/components/ui/card";
import { Checkbox, Input, Select } from "@/components/ui/field";
import { api } from "@/lib/client";
import { errorKey, fieldErrors, type ErrorKey } from "@/lib/errors";
import { kitWarnings, type KitKey } from "@/lib/kit";

const FORMATS = ["adult_2x30", "youth_2x25", "youth_2x20", "mini", "tournament"] as const;
const KIT_DEFAULTS: Record<KitKey, string> = {
  own: "#0b6bcb",
  own_gk: "#f59e0b",
  opponent: "#dc2626",
  opponent_gk: "#16a34a",
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
  const [format, setFormat] = useState<string | null>(null);
  const team = useQuery({
    queryKey: ["team", orgId, teamId],
    queryFn: async () =>
      (await api.GET("/v1/orgs/{org_id}/teams/{team_id}", { params: { path: { org_id: orgId, team_id: teamId } } })).data,
  });
  const chosenFormat = format ?? (team.data?.is_youth ? "youth_2x25" : "adult_2x30");
  const similar = kitWarnings(kits);
  const opponents = useQuery({
    queryKey: ["opponents", orgId],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/opponents", { params: { path: { org_id: orgId } } })).data ?? [],
  });

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const name = String(f.get("opponent")).trim();
    const known = opponents.data?.find((o) => o.name.toLowerCase() === name.toLowerCase());
    const optional = (k: string) => String(f.get(k) ?? "").trim() || null;
    setBusy(true);
    const { data, error } = await api.POST("/v1/orgs/{org_id}/teams/{team_id}/matches", {
      params: { path: { org_id: orgId, team_id: teamId } },
      body: {
        ...(known ? { opponent_id: known.id } : { opponent_name: name }),
        kickoff_at: new Date(String(f.get("kickoff"))).toISOString(),
        is_home: f.get("away") !== "on",
        competition: optional("competition"),
        venue: optional("venue"),
        kit_own: kits.own,
        kit_own_gk: kits.own_gk,
        kit_opponent: kits.opponent,
        kit_opponent_gk: kits.opponent_gk,
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

  return (
    <Card>
      <h2 className="mb-4 text-lg font-semibold">{t("matches.new")}</h2>
      {error && <Alert className="mb-4">{t(`errors.${error}`)}</Alert>}
      <form onSubmit={submit} className="grid gap-3 sm:grid-cols-2" aria-label={t("matches.new")}>
        <Input
          label={t("matches.opponent")}
          name="opponent"
          required
          list={listId}
          placeholder={t("matches.opponentPlaceholder")}
          autoComplete="off"
          error={fields.opponent_name}
        />
        <datalist id={listId}>
          {opponents.data?.map((o) => <option key={o.id} value={o.name} />)}
        </datalist>
        <Input label={t("matches.kickoff")} name="kickoff" type="datetime-local" required defaultValue={localNow()} />
        <Input label={`${t("matches.competition")} (${t("common.optional")})`} name="competition" />
        <Input label={`${t("matches.venue")} (${t("common.optional")})`} name="venue" />
        <div className="sm:col-span-2">
          <Checkbox name="away" label={t("matches.away")} />
        </div>
        <fieldset className="grid grid-cols-2 gap-3 sm:col-span-2 sm:grid-cols-4">
          <legend className="mb-1 text-sm font-medium">{t("matches.kits")}</legend>
          {(
            [
              ["own", "matches.kitOwn"],
              ["own_gk", "matches.kitOwnGk"],
              ["opponent", "matches.kitOpp"],
              ["opponent_gk", "matches.kitOppGk"],
            ] as const
          ).map(([k, label]) => (
            <Input
              key={k}
              label={t(label)}
              name={`kit_${k}`}
              type="color"
              value={kits[k]}
              onChange={(e) => setKits((v) => ({ ...v, [k]: e.target.value }))}
              className="h-10 p-1"
            />
          ))}
          <p className="col-span-full text-xs text-muted">{t("matches.kitsHint")}</p>
          {similar.length > 0 && (
            <p role="status" className="col-span-full rounded-md border-l-4 border-accent bg-surface px-3 py-2 text-sm" data-testid="kit-warning">
              {t("matchForm.kitWarning", {
                pairs: similar.map(([a, b]) => `${t(`matchForm.kit_${a}`)} / ${t(`matchForm.kit_${b}`)}`).join(", "),
              })}
            </p>
          )}
        </fieldset>
        <Select label={t("matchForm.format")} name="format" value={chosenFormat} onChange={(e) => setFormat(e.target.value)}>
          {FORMATS.map((k) => (
            <option key={k} value={k}>
              {t(`matchForm.format_${k}`)}
            </option>
          ))}
        </Select>
        <div className="sm:col-span-2">
          <Button type="submit" loading={busy}>
            {t("matches.create")}
          </Button>
        </div>
      </form>
    </Card>
  );
}
