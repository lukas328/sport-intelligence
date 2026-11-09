"use client";

import type { Schemas } from "@handball/api-client";
import { useTranslations } from "next-intl";
import { useQuery } from "@tanstack/react-query";
import { useRef, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/card";
import { Input, Select } from "@/components/ui/field";
import { api } from "@/lib/client";
import { errorKey, type ErrorKey } from "@/lib/errors";

const TEAM_ROLES = [
  "player",
  "goalkeeper",
  "coach",
  "analyst",
  "goalkeeper_coach",
  "athletic_coach",
  "team_manager",
  "parent",
] as const;

export function InviteForm({
  orgId,
  teams,
  isAdmin,
  onInvited,
}: {
  orgId: string;
  teams: { id: string; name: string }[];
  isAdmin: boolean;
  onInvited?: (email: string) => void;
}) {
  const t = useTranslations();
  const [error, setError] = useState<ErrorKey | null>(null);
  const [invited, setInvited] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const formRef = useRef<HTMLFormElement>(null);
  const [team, setTeam] = useState(teams[0]?.id ?? "org");
  const [role, setRole] = useState<string>("player");
  // parents are invited for one child of the team roster (guardianship); players and goalkeepers
  // for their own entry, so they see their dates and scenes from the first sign-in
  const linksEntry = role === "parent" || role === "player" || role === "goalkeeper";
  const children = useQuery({
    queryKey: ["invite-children", orgId, team],
    enabled: linksEntry && team !== "org",
    queryFn: async () => {
      const p = { org_id: orgId, team_id: team };
      const info = (await api.GET("/v1/orgs/{org_id}/teams/{team_id}", { params: { path: p } })).data;
      const season = info?.current_season?.id;
      if (!season) return [];
      const r = await api.GET("/v1/orgs/{org_id}/teams/{team_id}/seasons/{season_id}/roster", {
        params: { path: { ...p, season_id: season } },
      });
      return r.data ?? [];
    },
  });

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const email = String(f.get("email"));
    const target = String(f.get("team"));
    const body: Schemas["InvitationCreate"] =
      target === "org"
        ? { email, org_role: "org_admin" }
        : {
            email,
            team_id: target,
            team_role: String(f.get("role")) as (typeof TEAM_ROLES)[number],
            ...(f.get("role") === "parent" && f.get("child") ? { player_id: String(f.get("child")) } : {}),
            ...((f.get("role") === "player" || f.get("role") === "goalkeeper") && f.get("entry") ? { player_id: String(f.get("entry")) } : {}),
          };
    setBusy(true);
    const { error } = await api.POST("/v1/orgs/{org_id}/invitations", { params: { path: { org_id: orgId } }, body });
    setBusy(false);
    if (error) return setError(errorKey(error));
    setError(null);
    setInvited((l) => [...l, email]);
    formRef.current?.reset();
    onInvited?.(email);
  }

  return (
    <form ref={formRef} onSubmit={submit} className="space-y-3" aria-label={t("settings.inviteTitle")}>
      {error && <Alert>{t(`errors.${error}`)}</Alert>}
      <div className="grid gap-3 sm:grid-cols-3">
        <Input label={t("onboarding.inviteEmail")} name="email" type="email" required autoComplete="off" />
        <Select label={t("settings.team")} name="team" value={team} onChange={(e) => setTeam(e.target.value)}>
          {teams.map((team) => (
            <option key={team.id} value={team.id}>
              {team.name}
            </option>
          ))}
          {isAdmin && <option value="org">{t("settings.wholeClub")}</option>}
        </Select>
        <Select label={t("onboarding.inviteRole")} name="role" value={role} onChange={(e) => setRole(e.target.value)}>
          {TEAM_ROLES.map((r) => (
            <option key={r} value={r}>
              {t(`roles.${r}`)}
            </option>
          ))}
        </Select>
        {role === "parent" && team !== "org" && (
          <Select label={t("invite.child")} name="child" required hint={t("invite.childHint")}>
            {(children.data ?? []).map((c) => (
              <option key={c.player_id} value={c.player_id}>
                {c.jersey_number ? `#${c.jersey_number} ` : ""}
                {c.first_name} {c.last_name}
              </option>
            ))}
          </Select>
        )}
        {(role === "player" || role === "goalkeeper") && team !== "org" && (children.data ?? []).some((c) => !c.has_account) && (
          <Select label={t("invite.entry")} name="entry" defaultValue="" hint={t("invite.entryHint")}>
            <option value="">{t("invite.entryLater")}</option>
            {(children.data ?? [])
              .filter((c) => !c.has_account)
              .map((c) => (
                <option key={c.player_id} value={c.player_id}>
                  {c.jersey_number ? `#${c.jersey_number} ` : ""}
                  {c.first_name} {c.last_name}
                </option>
              ))}
          </Select>
        )}
      </div>
      <Button type="submit" variant="secondary" loading={busy}>
        {t("onboarding.inviteSend")}
      </Button>
      {invited.length > 0 && (
        <ul className="text-sm text-ok" role="status">
          {invited.map((m) => (
            <li key={m}>{t("onboarding.invited", { email: m })}</li>
          ))}
        </ul>
      )}
    </form>
  );
}
