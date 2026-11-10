"use client";

import type { Schemas } from "@handball/api-client";
import { useMutation } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { Alert } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/field";
import { api } from "@/lib/client";

type Team = Schemas["TeamOut"];

/**
 * "Teamfunktionen" per team (ADR 029): training, dates, RSVP, tasks and the player and parent
 * areas. Off hides them from the navigation and the search; nothing is deleted.
 */
export function TeamFeaturesSection({ orgId, teams }: { orgId: string; teams: Team[] }) {
  const t = useTranslations("settings");
  const te = useTranslations("errors");
  const router = useRouter();
  const [state, setState] = useState<Record<string, boolean>>(() => Object.fromEntries(teams.map((x) => [x.id, x.settings.team_features ?? false])));
  const save = useMutation({
    mutationFn: async ({ teamId, on }: { teamId: string; on: boolean }) => {
      const { error } = await api.PATCH("/v1/orgs/{org_id}/teams/{team_id}", {
        params: { path: { org_id: orgId, team_id: teamId } },
        body: { settings: { team_features: on } },
      });
      if (error) throw new Error("save");
    },
    onMutate: ({ teamId, on }) => setState((s) => ({ ...s, [teamId]: on })),
    onError: (_e, { teamId, on }) => setState((s) => ({ ...s, [teamId]: !on })),
    onSuccess: () => router.refresh(),
  });
  if (teams.length === 0) return null;
  return (
    <section id="team-features" aria-labelledby="team-features-title" className="space-y-3">
      <h2 id="team-features-title" className="text-lg font-semibold">
        {t("teamFeatures")}
      </h2>
      <div className="space-y-4 border-t border-foreground/15 pt-5">
        <p className="text-sm text-muted">{t("teamFeaturesHint")}</p>
        {save.isError && <Alert>{te("generic")}</Alert>}
        <ul className="space-y-3" data-testid="team-features">
          {teams.map((x) => (
            <li key={x.id}>
              <Checkbox
                label={x.name}
                checked={state[x.id] ?? false}
                disabled={save.isPending}
                onChange={(e) => save.mutate({ teamId: x.id, on: e.currentTarget.checked })}
              />
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
