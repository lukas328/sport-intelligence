"use client";

import type { Schemas } from "@handball/api-client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/field";
import { api } from "@/lib/client";
import { errorKey, type ErrorKey } from "@/lib/errors";

type Entry = Schemas["RosterEntryOut"];
type Member = Schemas["TeamMemberOut"];

/** The team's members, for staff: whose account belongs to which squad entry. */
export function useTeamMembers(orgId: string, teamId: string, enabled: boolean) {
  return useQuery({
    queryKey: ["team-members", teamId],
    enabled,
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/teams/{team_id}/members", { params: { path: { org_id: orgId, team_id: teamId } } })).data ?? [],
  });
}

function useLink(orgId: string, teamId: string, rosterKey: unknown[]) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (v: { playerId: string; userId: string | null }) => {
      const path = { org_id: orgId, team_id: teamId, player_id: v.playerId };
      const r = v.userId
        ? await api.PUT("/v1/orgs/{org_id}/teams/{team_id}/players/{player_id}/account", { params: { path }, body: { user_id: v.userId } })
        : await api.DELETE("/v1/orgs/{org_id}/teams/{team_id}/players/{player_id}/account", { params: { path } });
      if (r.error) throw r.error;
    },
    onSuccess: () => void qc.invalidateQueries({ queryKey: rosterKey }),
  });
}

/**
 * Players and goalkeepers who joined the team but whose account belongs to no squad entry: they
 * see no dates and none of their scenes. One line each, with the free entries to pick from.
 */
export function UnlinkedAccounts({ orgId, teamId, entries, members, rosterKey }: { orgId: string; teamId: string; entries: Entry[]; members: Member[]; rosterKey: unknown[] }) {
  const t = useTranslations();
  const link = useLink(orgId, teamId, rosterKey);
  const [error, setError] = useState<ErrorKey | null>(null);
  const linked = new Set(entries.map((e) => e.account_user_id).filter(Boolean));
  const open = members.filter((m) => (m.role === "player" || m.role === "goalkeeper") && !linked.has(m.user_id));
  const free = entries.filter((e) => !e.has_account);
  if (open.length === 0 || free.length === 0) return null;
  return (
    <section className="space-y-2" aria-labelledby="unlinked-title" data-testid="unlinked-accounts">
      <h3 id="unlinked-title" className="text-sm font-semibold">
        {t("accountLink.title", { n: open.length })}
      </h3>
      <p className="text-sm text-muted">{t("accountLink.hint")}</p>
      <ul className="border-t border-foreground/15">
        {open.map((m) => (
          <li key={m.user_id} className="border-b border-foreground/15 py-2.5">
            <form
              className="flex flex-wrap items-end gap-x-3 gap-y-2"
              aria-label={t("accountLink.formFor", { name: m.name })}
              onSubmit={(e) => {
                e.preventDefault();
                const playerId = String(new FormData(e.currentTarget).get("entry") ?? "");
                if (!playerId) return;
                setError(null);
                link.mutate({ playerId, userId: m.user_id }, { onError: (err) => setError(errorKey(err)) });
              }}
            >
              <span className="min-w-0 flex-1 basis-40">
                <span className="block font-medium">{m.name}</span>
                <span className="block text-xs text-muted">{t(`roles.${m.role}`)}</span>
              </span>
              <Select label={t("accountLink.entry")} name="entry" defaultValue={free.find((e) => `${e.first_name} ${e.last_name}` === m.name)?.player_id ?? ""}>
                <option value="">{t("accountLink.pick")}</option>
                {free.map((e) => (
                  <option key={e.player_id} value={e.player_id}>
                    {e.jersey_number ? `#${e.jersey_number} ` : ""}
                    {e.first_name} {e.last_name}
                  </option>
                ))}
              </Select>
              <Button type="submit" size="sm" variant="secondary" className="max-sm:min-h-11" loading={link.isPending && link.variables?.userId === m.user_id}>
                {t("accountLink.link")}
              </Button>
            </form>
          </li>
        ))}
      </ul>
      {error && <p className="text-sm text-error">{t(`errors.${error}`)}</p>}
    </section>
  );
}

/** In a squad row's panel: whose account the entry belongs to, and the way to undo it. */
export function AccountLine({ orgId, teamId, entry, members, rosterKey }: { orgId: string; teamId: string; entry: Entry; members: Member[]; rosterKey: unknown[] }) {
  const t = useTranslations();
  const link = useLink(orgId, teamId, rosterKey);
  if (!entry.account_user_id) return null;
  const who = members.find((m) => m.user_id === entry.account_user_id);
  return (
    <p className="flex flex-wrap items-center gap-x-3 basis-full text-sm" data-testid="account-line">
      <span className="text-muted">{t("accountLink.linked", { name: who?.name ?? who?.email ?? "?" })}</span>
      <Button type="button" size="sm" variant="quiet" loading={link.isPending} onClick={() => link.mutate({ playerId: entry.player_id, userId: null })}>
        {t("accountLink.unlink")}
      </Button>
    </p>
  );
}
