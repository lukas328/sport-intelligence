"use client";

import type { Schemas } from "@handball/api-client";
import { useRouter, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useCallback, useEffect, useRef, useState } from "react";
import { buttonClass } from "@/components/ui/button";
import { api } from "@/lib/client";
import { SHIRTS } from "@/lib/color";
import { FARBE } from "../entry-view";

type Suggestion = Schemas["SuggestionOut"];
const num = (v: unknown) => (typeof v === "number" ? v : null);

/**
 * The end of the public entry, signed in by the mail link: take over the chosen team (or make one
 * from its name) with the colour the coach tapped, take the players who played this season into
 * the squad, and go to Spiele. A club already in the app gets an access request instead.
 */
export function SaveTeam() {
  const t = useTranslations("entry");
  const params = useSearchParams();
  const router = useRouter();
  const [state, setState] = useState<"saving" | "access" | "failed">("saving");
  const started = useRef(false);
  const colour = FARBE[params.get("farbe") ?? ""] ?? SHIRTS[0][1];
  const second = colour === SHIRTS[4][1] || colour === SHIRTS[2][1] ? SHIRTS[3][1] : SHIRTS[4][1];

  const run = useCallback(async () => {
    setState("saving");
    const me = await api.GET("/v1/me");
    if (!me.data) {
      router.replace(`/login?next=${encodeURIComponent(`/einstieg/speichern?${params.toString()}`)}`);
      return;
    }
    const clubId = Number(params.get("club"));
    const teamId = Number(params.get("team"));
    const name = params.get("name");
    if (clubId && teamId) {
      const r = await api.POST("/v1/official/teams/{official_id}/claim", { params: { path: { official_id: teamId } }, body: { club_id: clubId } });
      if (r.error || !r.data) return setState("failed");
      if (r.data.status === "access_requested" || !r.data.organization_id || !r.data.team_id) {
        return setState("access");
      }
      const org = r.data.organization_id;
      const team = r.data.team_id;
      await api.PATCH("/v1/orgs/{org_id}", { params: { path: { org_id: org } }, body: { primary_color: colour, secondary_color: second } });
      // the players who played this season come into the squad; the rest waits in the inbox
      const s = await api.GET("/v1/orgs/{org_id}/teams/{team_id}/official/suggestions", { params: { path: { org_id: org, team_id: team } } });
      const adds = ((s.data ?? []) as Suggestion[]).filter((x) => x.kind === "roster_add" && x.status === "open" && (num(x.payload.appearances) ?? 0) > 0);
      for (const x of adds) {
        await api.POST("/v1/orgs/{org_id}/teams/{team_id}/official/suggestions/{suggestion_id}/accept", { params: { path: { org_id: org, team_id: team, suggestion_id: x.id } }, body: null });
      }
      router.replace(`/app/${org}/teams/${team}/matches`);
      return;
    }
    if (name) {
      const o = await api.POST("/v1/orgs", { body: { name, country: "CH", primary_color: colour, secondary_color: second } });
      if (o.error || !o.data) return setState("failed");
      const tm = await api.POST("/v1/orgs/{org_id}/teams", { params: { path: { org_id: o.data.id } }, body: { name, gender: "mixed" } });
      if (tm.error || !tm.data) return setState("failed");
      router.replace(`/app/${o.data.id}/teams/${tm.data.id}/matches`);
      return;
    }
    router.replace("/einstieg");
  }, [params, router, colour, second]);

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    void run();
  }, [run]);

  return (
    <section className="mx-auto max-w-xl space-y-4" aria-live="polite" data-testid="entry-saving">
      {state === "saving" && <p className="text-[19px]">{t("saving")}</p>}
      {state === "access" && <p className="text-[19px]">{t("savedAccess")}</p>}
      {state === "failed" && (
        <>
          <p className="text-[19px] font-bold">{t("savingFailed")}</p>
          <button type="button" className={buttonClass("primary")} onClick={() => void run()}>
            {t("retry")}
          </button>
        </>
      )}
    </section>
  );
}
