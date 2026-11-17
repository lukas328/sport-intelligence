"use client";

import type { Schemas } from "@handball/api-client";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { TeamLifeDialog, TeamLifeOffDialog, useTeamLife } from "./team-life";

type Team = Schemas["TeamOut"];

/**
 * «Teamleben» per team (ADR 029, finding K16): dates with RSVP, training, tasks and the areas of
 * players and parents in one place. Switching on explains first what comes; switching off hides
 * it from the navigation and the search, nothing is deleted. The same switch sits on the Team
 * page, where coaches look for it.
 */
export function TeamFeaturesSection({ orgId, teams }: { orgId: string; teams: Team[] }) {
  const t = useTranslations("teamLife");
  if (teams.length === 0) return null;
  return (
    <section id="team-features" aria-labelledby="team-features-title" className="space-y-3">
      <h2 id="team-features-title" className="text-lg font-semibold">
        {t("name")}
      </h2>
      <div className="space-y-4 border-t border-foreground/15 pt-5">
        <p className="max-w-[65ch] text-[15px] text-ink-2">{t("clubHint")}</p>
        <ul className="m-0 list-none divide-y divide-rule p-0" data-testid="team-features">
          {teams.map((x) => (
            <TeamRow key={x.id} orgId={orgId} team={x} />
          ))}
        </ul>
      </div>
    </section>
  );
}

function TeamRow({ orgId, team }: { orgId: string; team: Team }) {
  const t = useTranslations("teamLife");
  const { on, save } = useTeamLife(orgId, team.id, team.settings.team_features ?? false);
  const [ask, setAsk] = useState(false);
  const [askOff, setAskOff] = useState(false);
  return (
    <li className="flex min-h-14 flex-wrap items-center justify-between gap-3 py-2">
      <span>
        <span className="block font-bold">{team.name}</span>
        <span className="block text-[15px] text-ink-2">{on ? t("stateOn") : t("stateOff")}</span>
      </span>
      {on ? (
        <Button variant="quiet" size="sm" onClick={() => setAskOff(true)} aria-label={`${t("switchOff")}: ${team.name}`}>
          {t("switchOff")}
        </Button>
      ) : (
        <Button variant="secondary" size="sm" onClick={() => setAsk(true)} aria-label={`${t("switchOnShort")}: ${team.name}`} data-testid="team-life-open">
          {t("switchOnShort")}
        </Button>
      )}
      <TeamLifeDialog
        open={ask}
        onOpenChange={setAsk}
        teamName={team.name}
        busy={save.isPending}
        failed={save.isError}
        onConfirm={() => save.mutate(true, { onSuccess: () => setAsk(false) })}
      />
      <TeamLifeOffDialog open={askOff} onOpenChange={setAskOff} busy={save.isPending} onConfirm={() => save.mutate(false, { onSuccess: () => setAskOff(false) })} />
    </li>
  );
}
