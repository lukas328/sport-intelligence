"use client";

import type { Schemas } from "@handball/api-client";
import { useQuery } from "@tanstack/react-query";
import { Check } from "lucide-react";
import { useRouter } from "next/navigation";
import { forgetClaim } from "./claim-storage";
import { useFormatter, useTranslations } from "next-intl";
import { type CSSProperties, useState } from "react";
import { Strip } from "@/components/anlauf/heads";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/client";
import { clubStyle, SHIRTS } from "@/lib/color";
import { cn } from "@/lib/utils";

type Claimed = Schemas["ClaimOut"];
type Suggestion = Schemas["SuggestionOut"];


const str = (v: unknown) => (typeof v === "string" ? v : "");
const num = (v: unknown) => (typeof v === "number" ? v : null);

/**
 * Einstieg, step 2 «Das seid ihr, oder?» (SPEC 7.12): what handball.ch delivered with ticks, the
 * shirt colour as eight shirts, and a preview of the last match's head and two squad rows that
 * take the colour at once. «Stimmt, weiter» keeps the colour, takes the players who played over
 * into the squad (the default of the official inbox) and opens Spiele; «Das ist nicht mein Team»
 * removes the team again and goes back to the search.
 */
export function ConfirmTeam({
  claimed,
  teamName,
  league,
  colour,
  onColour,
  onNotMine,
}: {
  claimed: Claimed;
  teamName: string;
  league: string;
  colour: string;
  onColour: (c: string) => void;
  onNotMine: () => void;
}) {
  const t = useTranslations("onboarding");
  const format = useFormatter();
  const router = useRouter();
  const [busy, setBusy] = useState<"confirm" | "back" | null>(null);
  const org = claimed.organization_id!;
  const team = claimed.team_id!;
  const path = { params: { path: { org_id: org, team_id: team } } };
  const suggestions = useQuery({
    queryKey: ["official-suggestions", team],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/teams/{team_id}/official/suggestions", path)).data ?? [],
  });
  const official = useQuery({
    queryKey: ["official", team],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/teams/{team_id}/official", path)).data ?? null,
  });
  const matches = useQuery({
    queryKey: ["matches", team],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/teams/{team_id}/matches", path)).data ?? [],
  });
  const adds: Suggestion[] = (suggestions.data ?? []).filter((s) => s.kind === "roster_add" && s.status === "open");
  const withNumbers = adds.length > 0 && adds.every((s) => num(s.payload.jersey_number) != null);
  const played = (matches.data ?? []).filter((m) => m.score_own != null && m.score_opponent != null);
  const last = [...played].sort((a, b) => b.kickoff_at.localeCompare(a.kickoff_at))[0];
  const standing = (official.data?.standing ?? []) as { teamId?: number; rank?: number }[];
  const rank = standing.find((r) => r.teamId != null && r.teamId === official.data?.official_team_id)?.rank;
  const rows = [...adds].sort((a, b) => (num(b.payload.appearances) ?? 0) - (num(a.payload.appearances) ?? 0)).slice(0, 2);
  const facts = [
    adds.length > 0 && t("players", { n: adds.length, numbers: withNumbers ? "all" : "some" }),
    (matches.data?.length ?? 0) > 0 && t("fixtures", { n: matches.data!.length, played: played.length }),
    rank != null && t("rank", { rank }),
  ].filter(Boolean) as string[];

  async function confirm() {
    setBusy("confirm");
    await api.PATCH("/v1/orgs/{org_id}", { params: { path: { org_id: org } }, body: { primary_color: colour } });
    // the players who played this season come into the squad; the rest waits in the inbox
    for (const s of adds.filter((x) => (num(x.payload.appearances) ?? 0) > 0)) {
      await api.POST("/v1/orgs/{org_id}/teams/{team_id}/official/suggestions/{suggestion_id}/accept", { params: { path: { org_id: org, team_id: team, suggestion_id: s.id } }, body: null });
    }
    forgetClaim();
    router.push(`/app/${org}/teams/${team}/matches`);
    router.refresh();
  }

  async function notMine() {
    setBusy("back");
    await api.DELETE("/v1/orgs/{org_id}/teams/{team_id}", path);
    setBusy(null);
    onNotMine();
  }

  const result = last ? (last.score_own! > last.score_opponent! ? t("won") : last.score_own! < last.score_opponent! ? t("lost") : t("draw")) : null;
  const actions = (
    <div className="flex flex-wrap gap-3 max-md:flex-col">
      <Button onClick={() => void confirm()} loading={busy === "confirm"} disabled={busy != null} data-testid="confirm-team">
        {t("confirm")}
      </Button>
      <Button variant="secondary" onClick={() => void notMine()} loading={busy === "back"} disabled={busy != null}>
        {t("notMine")}
      </Button>
    </div>
  );

  return (
    <div className="grid gap-x-16 gap-y-10 md:grid-cols-[minmax(0,1fr)_minmax(0,460px)]" data-testid="claim-done">
      <div className="min-w-0">
        <p className="text-[15px] font-semibold text-ink-2">{t("fromOfficial")}</p>
        <h2 className="mt-1 text-[30px] leading-tight md:text-[34px]">{teamName}</h2>
        {league && <p className="mt-1 text-[15px] text-ink-2">{league}</p>}
        <ul className="mt-4 mb-10 list-none p-0" aria-live="polite">
          {facts.map((f) => (
            <li key={f} className="flex min-h-[50px] items-center gap-4 border-t border-rule text-[17px]">
              <Check aria-hidden className="size-5 shrink-0 text-ok" strokeWidth={2.5} />
              {f}
            </li>
          ))}
        </ul>
        <fieldset className="m-0 border-0 p-0">
          <legend className="font-slant mb-3 w-full border-b-2 border-ink pb-2.5 text-[22px] md:text-2xl">{t("shirtTitle")}</legend>
          <div className="grid w-fit grid-cols-4 gap-3 sm:flex sm:flex-wrap">
            {SHIRTS.map(([key, hex]) => (
              <label key={key} className={cn("grid size-[52px] cursor-pointer place-items-center border-2 has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-ink", colour === hex ? "border-ink" : "border-transparent")}>
                <input type="radio" name="shirt" value={hex} checked={colour === hex} onChange={() => onColour(hex)} className="sr-only" aria-label={t(`shirt.${key}`)} />
                <svg aria-hidden viewBox="0 0 24 24" className="size-10">
                  <path d="M8 3 4.2 4.8 2 9l3.2 1.6L6.4 9v12h11.2V9l1.2 1.6L22 9l-2.2-4.2L16 3c-.9 1.4-2.3 2.2-4 2.2S8.9 4.4 8 3Z" fill={hex} stroke="var(--ink)" strokeOpacity={0.35} strokeWidth="1" strokeLinejoin="round" />
                </svg>
              </label>
            ))}
          </div>
          <p className="mt-3 text-[15px] text-ink-2">{t("crestLater")}</p>
        </fieldset>
        <div className="mt-8 max-md:hidden">
          {actions}
          <p className="mt-4 text-[15px] text-ink-2">{t("next")}</p>
        </div>
      </div>

      {/* the preview takes the picked colour at once: the head of the last match, two rows */}
      <div className="club min-w-0" style={clubStyle(colour) as CSSProperties}>
        <p className="mb-2 text-[15px] font-semibold text-ink-2">{last ? t("previewTitle") : t("previewNone")}</p>
        <Strip
          name={
            <>
              <small className="mb-2 block font-sans text-[15px] font-semibold not-italic">
                {last ? t("previewAgainst", { day: format.dateTime(new Date(last.kickoff_at), { weekday: "long" }), opp: last.opponent_name ?? "" }) : teamName}
              </small>
              {result}
            </>
          }
          own={last?.score_own ?? null}
          opp={last?.score_opponent ?? null}
        />
        <ul className="mt-4 list-none p-0">
          {rows.map((s) => (
            <li key={s.id} className="grid min-h-[76px] grid-cols-[64px_minmax(0,1fr)_auto] items-center gap-x-3 border-t border-rule py-3">
              <span className="font-num text-right text-[44px] leading-[.8] text-club-text">{num(s.payload.jersey_number) ?? "?"}</span>
              <span className="min-w-0">
                <span className="font-slant block text-[19px] leading-tight">{`${str(s.payload.first_name)} ${str(s.payload.last_name)}`}</span>
                {num(s.payload.appearances) != null && <span className="text-[15px] text-ink-2">{t("appearances", { n: num(s.payload.appearances)! })}</span>}
              </span>
              <span className="text-[15px] font-bold text-ink-2">{str(s.payload.position)}</span>
            </li>
          ))}
        </ul>
      </div>
      <div className="md:hidden">{actions}</div>
    </div>
  );
}
