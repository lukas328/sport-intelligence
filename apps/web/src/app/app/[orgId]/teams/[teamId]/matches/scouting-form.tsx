"use client";

import type { Schemas } from "@handball/api-client";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useId, useState, type FormEvent } from "react";
import { DateTimeField } from "@/components/domain/date-time-field";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/card";
import { Input } from "@/components/ui/field";
import { api } from "@/lib/client";
import { SHIRTS } from "@/lib/color";
import { combine, formatDate } from "@/lib/date-input";
import { errorKey, type ErrorKey } from "@/lib/errors";
import { cn } from "@/lib/utils";

type Match = Schemas["MatchSummary"];

/**
 * «Gegner beobachten» (K3): a video of an opponent playing another team, our team does not play.
 * Who plays and their shirt colours, then the upload. The analysis treats the other team as the
 * own side (both colours go to it); what it finds goes to the opponent's page and the
 * preparation report, never into our season. Who plays at home decides the order everywhere
 * (`is_home`: the other team, the data's own side, at home); by default the first named team, the
 * observed opponent (UI check 20.11.).
 */
export function ScoutingForm({ orgId, teamId, matches }: { orgId: string; teamId: string; matches: Match[] }) {
  const t = useTranslations("scoutingUpload");
  const tr = useTranslations();
  const router = useRouter();
  const listId = useId();
  const opponents = useQuery({
    queryKey: ["opponents", orgId],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/opponents", { params: { path: { org_id: orgId } } })).data ?? [],
  });
  // the next opponents from the schedule first: that is whom a coach watches
  const now = Date.now();
  const next = matches
    .filter((m) => m.kind === "match" && Date.parse(m.kickoff_at) > now && m.opponent_name)
    .sort((a, b) => a.kickoff_at.localeCompare(b.kickoff_at))
    .map((m) => m.opponent_name);
  const names = [...new Set([...next, ...(opponents.data ?? []).map((o) => o.name)])];
  const [opponent, setOpponent] = useState(next[0] ?? "");
  const [other, setOther] = useState("");
  const [home, setHome] = useState<"opponent" | "other">("opponent");
  const [day, setDay] = useState(() => formatDate(new Date()));
  const [oppColour, setOppColour] = useState<string | null>(null);
  const [otherColour, setOtherColour] = useState<string | null>(null);
  const [error, setError] = useState<ErrorKey | "colours" | "date" | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    const when = combine(day, "12:00");
    if (!when) return setError("date");
    if (!oppColour || !otherColour) return setError("colours");
    setBusy(true);
    const known = opponents.data?.find((o) => o.name.toLowerCase() === opponent.trim().toLowerCase());
    const { data, error: problem } = await api.POST("/v1/orgs/{org_id}/teams/{team_id}/matches", {
      params: { path: { org_id: orgId, team_id: teamId } },
      body: {
        kind: "scouting",
        ...(known ? { opponent_id: known.id } : { opponent_name: opponent.trim() }),
        scouting_other: other.trim(),
        is_home: home === "other",
        kickoff_at: when.toISOString(),
        // the other team takes our side in the analysis: its shirt is the own kit
        kit_own: otherColour,
        kit_opponent: oppColour,
      },
    });
    setBusy(false);
    if (problem || !data) return setError(errorKey(problem));
    router.push(`/app/${orgId}/matches/${data.id}?tab=video#upload`);
  }

  return (
    <form onSubmit={submit} className="space-y-5" aria-label={t("title")} data-testid="scouting-form">
      <p className="m-0 max-w-[62ch] text-[17px]">{t("intro")}</p>
      <datalist id={listId}>
        {names.map((n) => (
          <option key={n} value={n} />
        ))}
      </datalist>
      <div className="grid gap-4 sm:grid-cols-2">
        <Input label={t("opponent")} value={opponent} onChange={(e) => setOpponent(e.target.value)} list={listId} required autoComplete="off" placeholder={t("opponentPlaceholder")} data-testid="scouting-opponent" />
        <Input label={t("other")} value={other} onChange={(e) => setOther(e.target.value)} list={listId} required autoComplete="off" placeholder={t("otherPlaceholder")} data-testid="scouting-other" />
      </div>
      <fieldset className="m-0 border-0 p-0" data-testid="scouting-home">
        <legend className="mb-2 text-[17px] font-bold">{t("home")}</legend>
        <div className="flex flex-wrap gap-x-6 gap-y-1">
          {(["opponent", "other"] as const).map((k) => (
            <label key={k} className="flex min-h-11 cursor-pointer items-center gap-2 text-[17px]">
              <input type="radio" name="home" value={k} checked={home === k} onChange={() => setHome(k)} className="size-5 accent-ink" data-testid={`scouting-home-${k}`} />
              {(k === "opponent" ? opponent : other).trim() || t(k === "opponent" ? "opponentShort" : "otherShort")}
            </label>
          ))}
        </div>
        <p className="m-0 mt-1 text-[15px] text-ink-2">{t("homeWhy")}</p>
      </fieldset>
      <div className="max-w-xs">
        <DateTimeField date={day} onDate={setDay} dateLabel={t("date")} required />
      </div>
      <Colours legend={t("colourOf", { team: opponent.trim() || t("opponentShort") })} value={oppColour} onChange={setOppColour} name="opp" />
      <Colours legend={t("colourOf", { team: other.trim() || t("otherShort") })} value={otherColour} onChange={setOtherColour} name="other" />
      <p className="m-0 max-w-[62ch] text-[15px] text-ink-2">{t("colourWhy")}</p>
      {error && <Alert>{error === "colours" ? t("colourMissing") : error === "date" ? tr("dateField.invalid") : tr(`errors.${error}`)}</Alert>}
      <Button type="submit" size="lg" loading={busy} data-testid="scouting-submit">
        {t("submit")}
      </Button>
    </form>
  );
}

/** Eight shirts and «andere Farbe»: what a coach sees in the video, without a colour picker first. */
function Colours({ legend, value, onChange, name }: { legend: string; value: string | null; onChange: (v: string) => void; name: string }) {
  const t = useTranslations();
  const known = SHIRTS.some(([, hex]) => hex === value);
  return (
    <fieldset className="m-0 border-0 p-0">
      <legend className="mb-2 text-[17px] font-bold">{legend}</legend>
      <div className="flex flex-wrap gap-2">
        {SHIRTS.map(([key, hex]) => (
          <label key={key} className={cn("grid size-12 cursor-pointer place-items-center border-2 has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-ink", value === hex ? "border-ink" : "border-transparent")}>
            <input type="radio" name={name} className="sr-only" checked={value === hex} onChange={() => onChange(hex)} aria-label={t(`onboarding.shirt.${key}`)} />
            <i aria-hidden className="block size-9 shadow-[0_0_0_1px_var(--rule)]" style={{ background: hex }} />
          </label>
        ))}
        <label className={cn("flex h-12 cursor-pointer items-center gap-2 border-2 px-2 text-[15px] font-bold", value && !known ? "border-ink" : "border-transparent")}>
          <input type="color" value={value && !known ? value : SHIRTS[3][1]} onChange={(e) => onChange(e.target.value)} className={cn("size-8 cursor-pointer border-0 bg-transparent p-0", !(value && !known) && "opacity-40")} aria-label={t("scoutingUpload.otherColour")} />
          {t("scoutingUpload.otherColour")}
        </label>
      </div>
    </fieldset>
  );
}
