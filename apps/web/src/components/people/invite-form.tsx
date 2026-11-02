"use client";

import type { Schemas } from "@handball/api-client";
import { useTranslations } from "next-intl";
import { useRef, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/card";
import { Input, Select } from "@/components/ui/field";
import { api } from "@/lib/client";
import { errorKey, type ErrorKey } from "@/lib/errors";

const TEAM_ROLES = ["player", "goalkeeper", "coach", "analyst"] as const;

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

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const email = String(f.get("email"));
    const target = String(f.get("team"));
    const body: Schemas["InvitationCreate"] =
      target === "org"
        ? { email, org_role: "org_admin" }
        : { email, team_id: target, team_role: String(f.get("role")) as (typeof TEAM_ROLES)[number] };
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
        <Select label={t("settings.team")} name="team" defaultValue={teams[0]?.id ?? "org"}>
          {teams.map((team) => (
            <option key={team.id} value={team.id}>
              {team.name}
            </option>
          ))}
          {isAdmin && <option value="org">{t("settings.wholeClub")}</option>}
        </Select>
        <Select label={t("onboarding.inviteRole")} name="role" defaultValue="player">
          {TEAM_ROLES.map((r) => (
            <option key={r} value={r}>
              {t(`roles.${r}`)}
            </option>
          ))}
        </Select>
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
