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
import { modeFor, navFor } from "@/lib/nav-model";
import { canGive, PERSON_ROLES, storedRoles, type PersonRole } from "@/lib/roles";
import { cn } from "@/lib/utils";

type Sent = { email: string; link: string; mailed: boolean };

/**
 * Inviting someone (findings K17, K18): one of the four roles, each with one sentence of what the
 * person sees and may do, and «So sieht es …»: the destinations the person will have. After
 * sending, the link to pass on in the team chat (the only way while no mail goes out, L2).
 */
export function InviteForm({
  orgId,
  teams,
  isAdmin,
  onInvited,
  initialRole = "co_trainer",
  initialTeam,
}: {
  orgId: string;
  teams: { id: string; name: string; team_features?: boolean }[];
  isAdmin: boolean;
  onInvited?: (email: string) => void;
  initialRole?: PersonRole;
  initialTeam?: string;
}) {
  const t = useTranslations();
  const tr = useTranslations("people");
  const [error, setError] = useState<ErrorKey | null>(null);
  const [emailError, setEmailError] = useState<string | null>(null);
  const [sent, setSent] = useState<Sent[]>([]);
  const [busy, setBusy] = useState(false);
  const formRef = useRef<HTMLFormElement>(null);
  const [team, setTeam] = useState(initialTeam ?? teams[0]?.id ?? "");
  const roles = PERSON_ROLES.filter((r) => canGive(isAdmin ? "org_admin" : "member", r));
  const [role, setRole] = useState<PersonRole>(
    roles.includes(initialRole) ? initialRole : "co_trainer",
  );
  const teamFeatures = teams.find((x) => x.id === team)?.team_features ?? false;
  // parents are invited for one child of the roster (guardianship); players for their own entry,
  // so they see their scenes from the first sign-in
  const linksEntry = role === "parent" || role === "player";
  const children = useQuery({
    queryKey: ["invite-children", orgId, team],
    enabled: linksEntry && Boolean(team),
    queryFn: async () => {
      const p = { org_id: orgId, team_id: team };
      const info = (await api.GET("/v1/orgs/{org_id}/teams/{team_id}", { params: { path: p } }))
        .data;
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
    const email = String(f.get("email") ?? "").trim();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return setEmailError(t("auth.needEmail"));
    setEmailError(null);
    const stored = storedRoles(role);
    const child = String(f.get("child") ?? "");
    const entry = String(f.get("entry") ?? "");
    const body: Schemas["InvitationCreate"] = {
      email,
      team_id: team,
      team_role: stored.team_role,
      org_role: stored.org_role,
      ...(role === "parent" && child ? { player_id: child } : {}),
      ...(role === "player" && entry ? { player_id: entry } : {}),
    };
    setBusy(true);
    const { data, error } = await api.POST("/v1/orgs/{org_id}/invitations", {
      params: { path: { org_id: orgId } },
      body,
    });
    setBusy(false);
    if (error || !data) return setError(errorKey(error));
    setError(null);
    setSent((l) => [{ email, link: data.link, mailed: data.mailed }, ...l]);
    formRef.current?.reset();
    onInvited?.(email);
  }

  // a parent is invited for a child of the squad: without one there is nobody to choose
  const noChild = role === "parent" && children.isSuccess && (children.data ?? []).length === 0;
  const mode = modeFor(storedRoles(role).org_role, storedRoles(role).team_role);
  const preview = navFor(mode, orgId, team || null, { teamFunctions: teamFeatures }).map((i) =>
    t(`shell.${i.key}`),
  );
  if (role === "trainer") preview.push(t("shell.club"));

  return (
    <div className="space-y-5">
      {/* what went out stands on top, where the eye is after sending */}
      {sent.length > 0 && (
        <ul className="m-0 list-none space-y-3 p-0" role="status" data-testid="invite-sent">
          {sent.map((s) => (
            <SentLine key={s.link} s={s} />
          ))}
        </ul>
      )}
      <form
        ref={formRef}
        onSubmit={submit}
        className="space-y-5"
        aria-label={t("settings.inviteTitle")}
        noValidate
      >
        {error && <Alert>{t(`errors.${error}`)}</Alert>}
        <div className="grid gap-3 sm:grid-cols-2">
          <Input
            label={t("onboarding.inviteEmail")}
            name="email"
            type="email"
            required
            autoComplete="off"
            inputMode="email"
            error={emailError ?? undefined}
          />
          {teams.length > 1 && (
            <Select
              label={t("settings.team")}
              name="team"
              value={team}
              onChange={(e) => setTeam(e.target.value)}
            >
              {teams.map((x) => (
                <option key={x.id} value={x.id}>
                  {x.name}
                </option>
              ))}
            </Select>
          )}
        </div>
        <fieldset className="m-0 border-0 p-0">
          <legend className="mb-2 text-[15px] font-bold">{tr("roleLegend")}</legend>
          <div className="grid gap-2 sm:grid-cols-2" data-testid="invite-roles">
            {roles.map((r) => (
              <label
                key={r}
                className={cn(
                  "flex cursor-pointer gap-3 border-2 px-3 py-2.5 has-[:focus-visible]:outline-3 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-ink",
                  role === r ? "border-ink" : "border-rule",
                )}
              >
                <input
                  type="radio"
                  name="role"
                  value={r}
                  checked={role === r}
                  onChange={() => setRole(r)}
                  className="mt-1 size-4 shrink-0 accent-[var(--ink)]"
                />
                <span>
                  <span className="block font-bold">{t(`personRoles.${r}`)}</span>
                  <span className="block text-[15px] leading-snug text-ink-2">
                    {tr(`roleText_${r}`)}
                  </span>
                </span>
              </label>
            ))}
          </div>
        </fieldset>
        {/* who the person is in the squad: only for players and parents */}
        {(role === "parent" || role === "player") && (
          <div className="grid gap-3 sm:grid-cols-2">
            {role === "parent" && noChild && (
              <p className="m-0 self-end text-[15px] text-ink-2 sm:col-span-2">
                {tr("parentNeedsChild")}
              </p>
            )}
            {role === "parent" && !noChild && (
              <Select label={t("invite.child")} name="child" required hint={t("invite.childHint")}>
                {(children.data ?? []).map((c) => (
                  <option key={c.player_id} value={c.player_id}>
                    {c.jersey_number ? `#${c.jersey_number} ` : ""}
                    {c.first_name} {c.last_name}
                  </option>
                ))}
              </Select>
            )}
            {role === "player" && (children.data ?? []).some((c) => !c.has_account) && (
              <Select
                label={t("invite.entry")}
                name="entry"
                defaultValue=""
                hint={t("invite.entryHint")}
              >
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
        )}
        {/* «So sieht es …»: what the person will have, and what not */}
        <div
          className="border-l-4 border-rule pl-3"
          data-testid="invite-preview"
          aria-live="polite"
        >
          <p className="m-0 text-[15px] font-bold">
            {tr("previewTitle", { role: t(`personRoles.${role}`) })}
          </p>
          <p className="mt-1 mb-0 font-slant text-[17px]">{preview.join(" · ")}</p>
          <p className="mt-1 mb-0 text-[15px] text-ink-2">{tr(`roleNot_${role}`)}</p>
        </div>
        <Button
          type="submit"
          loading={busy}
          disabled={role === "parent" && noChild}
          data-testid="invite-send"
        >
          {t("onboarding.inviteSend")}
        </Button>
      </form>
    </div>
  );
}

/** «Eingeladen»: by mail, and the link to pass on (copy) in the team chat. */
function SentLine({ s }: { s: Sent }) {
  const tr = useTranslations("people");
  const [copied, setCopied] = useState<"yes" | "no" | null>(null);
  return (
    <li className="border-t border-rule pt-3 [overflow-wrap:anywhere]">
      <p className="m-0 text-[15px] font-bold text-ok">
        {s.mailed ? tr("sentMail", { email: s.email }) : tr("sentNoMail", { email: s.email })}
      </p>
      <p className="mt-1 mb-0 text-[15px]">{s.mailed ? tr("linkAlso") : tr("linkOnly")}</p>
      <div className="mt-2 flex flex-wrap items-center gap-3">
        <Button
          size="sm"
          variant="secondary"
          onClick={async () => {
            try {
              await navigator.clipboard.writeText(s.link);
              setCopied("yes");
            } catch {
              setCopied("no");
            }
          }}
        >
          {copied === "yes" ? tr("copied") : tr("copy")}
        </Button>
        {copied === "no" && <code className="text-[14px]">{s.link}</code>}
      </div>
    </li>
  );
}
