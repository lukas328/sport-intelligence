"use client";

import type { Schemas } from "@handball/api-client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useFormatter, useTranslations } from "next-intl";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Alert, EmptyState } from "@/components/ui/card";
import { api } from "@/lib/client";
import { errorKey, type ErrorKey } from "@/lib/errors";

type Purpose = Schemas["ConsentKind"];
export const PURPOSES: Purpose[] = ["analysis", "highlights_internal", "highlights_public", "public_profile", "training_data"];
/** Youth protection (addendum 01, 4.9): nothing public for youth players. */
const PUBLIC: Purpose[] = ["highlights_public", "public_profile"];

export function MyConsents({ orgId }: { orgId: string }) {
  const t = useTranslations();
  const format = useFormatter();
  const qc = useQueryClient();
  const [error, setError] = useState<ErrorKey | null>(null);
  const key = ["my-consents", orgId];
  const q = useQuery({
    queryKey: key,
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/me/consents", { params: { path: { org_id: orgId } } })).data ?? [],
  });
  const toggle = useMutation({
    mutationFn: async ({ player, kind, give }: { player: string; kind: Purpose; give: boolean }) => {
      const path = { org_id: orgId, player_id: player };
      const r = give
        ? await api.POST("/v1/orgs/{org_id}/me/consents/{player_id}", { params: { path }, body: { kind } })
        : await api.DELETE("/v1/orgs/{org_id}/me/consents/{player_id}/{kind}", { params: { path: { ...path, kind } } });
      if (r.error) throw r.error;
    },
    onSuccess: () => (setError(null), void qc.invalidateQueries({ queryKey: key })),
    onError: (e) => setError(errorKey(e)),
  });

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold sm:text-[1.75rem]">{t("consents.title")}</h1>
      <p className="max-w-prose text-muted">{t("consents.intro")}</p>
      {error && <Alert>{t(`errors.${error}`)}</Alert>}
      {q.data && q.data.length === 0 && <EmptyState title={t("consents.none")} />}
      {(q.data ?? []).map((s) => {
        const youth = s.teams.some((team) => team.is_youth) || s.minor === true;
        const childLocked = s.relation === "self" && s.minor === true;
        return (
          <section key={s.player_id} className="space-y-3 rounded-2xl bg-raised ring-1 ring-border/70 p-4" aria-labelledby={`subject-${s.player_id}`}>
            <div>
              <h2 id={`subject-${s.player_id}`} className="text-lg font-semibold">
                {s.first_name} {s.last_name}
                <span className="ml-2 text-sm font-normal text-muted">{t(`consents.${s.relation as "self"}`)}</span>
              </h2>
              {s.teams.length > 0 && <p className="text-sm text-muted">{t("consents.teams", { teams: s.teams.map((x) => x.name).join(", ") })}</p>}
              {childLocked && <p className="text-sm">{t("consents.minor")}</p>}
            </div>
            <ul className="divide-y divide-border/70">
              {PURPOSES.map((p) => {
                const active = s.active.includes(p);
                const locked = childLocked || (youth && PUBLIC.includes(p) && !active);
                return (
                  <li key={p} className="flex flex-wrap items-center gap-3 py-3">
                    <div className="min-w-0 flex-1">
                      <p className="font-medium">{t(`consents.purpose_${p}`)}</p>
                      <p className="text-sm text-muted">{t(`consents.purpose_${p}_help`)}</p>
                    </div>
                    <span className={active ? "text-sm font-medium text-ok" : "text-sm text-muted"}>
                      {active ? t("consents.given") : youth && PUBLIC.includes(p) ? t("consents.youthLocked") : t("consents.notGiven")}
                    </span>
                    {!locked && (
                      <Button
                        variant={active ? "ghost" : "secondary"}
                        loading={toggle.isPending && toggle.variables?.player === s.player_id && toggle.variables.kind === p}
                        onClick={() => toggle.mutate({ player: s.player_id, kind: p, give: !active })}
                        aria-label={`${active ? t("consents.revoke") : t("consents.give")}: ${t(`consents.purpose_${p}`)}`}
                      >
                        {active ? t("consents.revoke") : t("consents.give")}
                      </Button>
                    )}
                  </li>
                );
              })}
            </ul>
            {s.history.length > 0 && (
              <details>
                <summary className="cursor-pointer text-sm">{t("consents.history")}</summary>
                <ul className="mt-2 space-y-1 text-sm text-muted">
                  {s.history.map((c) => (
                    <li key={c.id}>
                      {t("consents.historyItem", {
                        purpose: t(`consents.purpose_${c.kind}`),
                        date: format.dateTime(new Date(c.given_at), { dateStyle: "medium" }),
                        name: c.given_by_name,
                      })}
                      {c.revoked_at && `, ${t("consents.revokedOn", { date: format.dateTime(new Date(c.revoked_at), { dateStyle: "medium" }) })}`}
                    </li>
                  ))}
                </ul>
              </details>
            )}
          </section>
        );
      })}
    </div>
  );
}
