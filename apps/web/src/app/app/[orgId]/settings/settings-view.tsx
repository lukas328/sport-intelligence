"use client";

// Sections of "Ich" and "Verein" (me/, club/); the single settings page they came from redirects.

import type { Schemas } from "@handball/api-client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useFormatter, useLocale, useTranslations } from "next-intl";
import QRCode from "qrcode";
import { useEffect, useState, type CSSProperties, type FormEvent } from "react";
import { Strip } from "@/components/anlauf/heads";
import { ClubColourPicker } from "@/components/anlauf/club-colour-picker";
import { clubStyle, DEFAULT_CLUB } from "@/lib/color";
import { InviteForm } from "@/components/people/invite-form";
import { TeamPeople } from "@/components/people/team-people";
import { personRole } from "@/lib/roles";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/card";
import { Input, Select } from "@/components/ui/field";
import { COUNTRIES, countryName, currencyOf } from "@/lib/country";
import { api } from "@/lib/client";
import { errorKey, type ErrorKey } from "@/lib/errors";
import { FileField } from "@/components/ui/file-field";

type Org = Schemas["OrgOut"];
type Team = Schemas["TeamOut"];
type Me = Schemas["MeOut"];

export function ClubSection({ org }: { org: Org }) {
  const t = useTranslations();
  const router = useRouter();
  const [error, setError] = useState<ErrorKey | null>(null);
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);
  // null: the club has not chosen its colour (decision E8) and shows the neutral slate
  const [chosen, setChosen] = useState<string | null>(org.color_chosen ? org.primary_color : null);
  const colour = chosen ?? DEFAULT_CLUB;
  const [second, setSecond] = useState(org.secondary_color);
  const [country, setCountry] = useState(org.country);
  const locale = useLocale();

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    setBusy(true);
    setSaved(false);
    setError(null);
    const { error } = await api.PATCH("/v1/orgs/{org_id}", {
      params: { path: { org_id: org.id } },
      body: {
        name: String(f.get("name")),
        ...(chosen ? { primary_color: chosen } : {}),
        secondary_color: String(f.get("secondary_color")),
        ...(country !== org.country ? { country } : {}),
      },
    });
    const logo = f.get("logo");
    let logoError: unknown = null;
    if (!error && logo instanceof File && logo.size > 0) {
      const body = new FormData();
      body.append("file", logo);
      logoError = (
        await api.PUT("/v1/orgs/{org_id}/logo", {
          params: { path: { org_id: org.id } },
          body: body as unknown as { file: string },
          bodySerializer: (b) => b as unknown as FormData,
        })
      ).error;
    }
    setBusy(false);
    if (error || logoError) return setError(errorKey(error ?? logoError));
    setSaved(true);
    router.refresh();
  }

  return (
    <section aria-labelledby="club" className="space-y-3">
      {/* «Verein» stands in the page head already: this section says what it holds (UX test B43) */}
      <h2 id="club" className="text-lg font-semibold">
        {t("settings.clubLook")}
      </h2>
      <div className="border-t border-foreground/15 pt-5">
        <form onSubmit={submit} className="space-y-6">
          {error && <Alert>{t(`errors.${error}`)}</Alert>}
          {saved && <Alert kind="success">{t("common.saved")}</Alert>}
          <Input label={t("onboarding.clubName")} name="name" defaultValue={org.name} required />
          {/* «Vereinsfarbe wählen» on the club's pages leads here (#vereinsfarbe) */}
          <ClubColourPicker id="vereinsfarbe" value={chosen} onChange={setChosen} legend={t("settings.clubColour")} note={chosen ? undefined : t("settings.clubColourNone")} />
          {/* the preview: the head of a match in the picked colour */}
          <div className="club" style={clubStyle(colour, second) as CSSProperties} data-testid="club-preview">
            <p className="mb-2 text-[15px] font-semibold text-ink-2">{t("settings.clubPreview")}</p>
            <Strip name={org.name} sub={t("settings.clubPreviewSub")} own={null} opp={null} pending={<>&nbsp;</>} />
          </div>
          <details>
            <summary className="min-h-11 cursor-pointer content-center text-[15px] font-bold underline decoration-[1.5px] underline-offset-4">{t("settings.ownColours")}</summary>
            <div className="grid grid-cols-2 gap-3 pt-3">
              <Input label={t("onboarding.primaryColor")} type="color" value={colour} onChange={(e) => setChosen(e.target.value)} className="h-11 w-24 p-1" />
              <Input label={t("onboarding.secondaryColor")} name="secondary_color" type="color" value={second} onChange={(e) => setSecond(e.target.value)} className="h-11 w-24 p-1" />
            </div>
          </details>
          {/* the country sets the currency of the billing (CHF in CH and LI, else EUR) */}
          <Select label={t("settings.country")} name="country" value={country} onChange={(e) => setCountry(e.target.value)} hint={t("settings.countryHint", { currency: currencyOf(country) })} data-testid="club-country">
            {[...new Set([...COUNTRIES, org.country])].map((c) => (
              <option key={c} value={c}>
                {countryName(c, locale)}
              </option>
            ))}
          </Select>
          <FileField label={t("onboarding.logo")} name="logo" accept="image/png,image/jpeg,image/webp" hint={t("onboarding.logoHint")} button={t("file.choose")} empty={t("file.none")} />
          <Button type="submit" loading={busy}>
            {t("common.save")}
          </Button>
        </form>
      </div>
    </section>
  );
}

export function PeopleSection({
  orgId,
  isAdmin,
  teams,
  allTeams,
}: {
  orgId: string;
  isAdmin: boolean;
  teams: { id: string; name: string }[];
  allTeams: Team[];
}) {
  const t = useTranslations();
  const tp = useTranslations("people");
  const format = useFormatter();
  const qc = useQueryClient();
  const teamName = (id: string | null | undefined) => allTeams.find((x) => x.id === id)?.name ?? "";
  const me = useQuery({ queryKey: ["me"], queryFn: async () => (await api.GET("/v1/me")).data });
  // club admins without a team: Trainer of the club (K18)
  const members = useQuery({
    queryKey: ["members", orgId],
    enabled: isAdmin,
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/members", { params: { path: { org_id: orgId } } })).data ?? [],
  });
  const clubOnly = (members.data ?? []).filter((m) => m.org_role === "org_admin" && Object.keys(m.team_roles).length === 0);
  const [roleError, setRoleError] = useState<ErrorKey | null>(null);
  const stepDown = useMutation({
    mutationFn: async (userId: string) => {
      const r = await api.PATCH("/v1/orgs/{org_id}/members/{user_id}", {
        params: { path: { org_id: orgId, user_id: userId } },
        body: { org_role: "member" },
      });
      if (r.error) throw r.error;
    },
    // stepping down: reload, the admin areas are gone
    onSuccess: () => void (window.location.href = `/app/${orgId}`),
    onError: (e) => setRoleError(errorKey(e)),
  });
  const invitations = useQuery({
    queryKey: ["invitations", orgId],
    queryFn: async () => {
      if (isAdmin)
        return (await api.GET("/v1/orgs/{org_id}/invitations", { params: { path: { org_id: orgId } } })).data ?? [];
      const lists = await Promise.all(
        teams.map(
          async (tm) =>
            (await api.GET("/v1/orgs/{org_id}/invitations", { params: { path: { org_id: orgId }, query: { team_id: tm.id } } }))
              .data ?? [],
        ),
      );
      return lists.flat();
    },
  });
  const revoke = useMutation({
    mutationFn: async (id: string) =>
      api.DELETE("/v1/orgs/{org_id}/invitations/{invitation_id}", {
        params: { path: { org_id: orgId, invitation_id: id } },
      }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["invitations", orgId] }),
  });
  const pending = (invitations.data ?? []).filter((i) => !i.accepted_at && !i.revoked_at);
  const meIsAdmin = me.data?.organizations.find((o) => o.id === orgId)?.role === "org_admin";

  return (
    <section aria-labelledby="people" className="space-y-3">
      <h2 id="people" className="text-lg font-semibold">
        {t("settings.people")}
      </h2>
      <p className="m-0 max-w-[65ch] text-[15px] text-ink-2">{tp("rolesIntro")}</p>
      {roleError && <Alert>{t(`errors.${roleError}`)}</Alert>}
      {teams.map((tm) => (
        <div key={tm.id} className="space-y-3 border-t border-foreground/15 pt-5">
          <h3 className="font-semibold">{tm.name}</h3>
          <TeamPeople orgId={orgId} teamId={tm.id} isAdmin={isAdmin} meId={me.data?.id ?? null} />
        </div>
      ))}
      {isAdmin && clubOnly.length > 0 && (
        <div className="space-y-3 border-t border-foreground/15 pt-5">
          <h3 className="font-semibold">{tp("clubOnly")}</h3>
          <ul className="m-0 list-none divide-y divide-rule p-0">
            {clubOnly.map((m) => (
              <li key={m.user_id} className="flex min-h-14 flex-wrap items-center justify-between gap-3 py-2">
                <span className="min-w-0">
                  <span className="block font-bold">{m.name}</span>
                  <span className="block truncate text-[15px] text-ink-2">{m.email}</span>
                </span>
                <span className="flex items-center gap-3 text-[15px] text-ink-2">
                  {t("personRoles.trainer")}
                  {m.user_id === me.data?.id && (
                    <Button variant="quiet" size="sm" onClick={() => stepDown.mutate(m.user_id)}>
                      {t("members.stepDown")}
                    </Button>
                  )}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
      <div id="invite" className="scroll-mt-24 space-y-3 border-t border-foreground/15 pt-5">
        <h3 className="font-semibold">{t("settings.inviteTitle")}</h3>
        <InviteForm
          orgId={orgId}
          teams={teams.map((tm) => ({ ...tm, team_features: allTeams.find((x) => x.id === tm.id)?.settings.team_features ?? false }))}
          isAdmin={Boolean(isAdmin && meIsAdmin !== false)}
          onInvited={() => void qc.invalidateQueries({ queryKey: ["invitations", orgId] })}
        />
      </div>
      <div className="space-y-3 border-t border-foreground/15 pt-5">
        <h3 className="font-semibold">{t("settings.invitationsTitle")}</h3>
        {pending.length === 0 ? (
          <p className="text-sm text-muted">{t("settings.noInvitations")}</p>
        ) : (
          <ul className="divide-y divide-border/70 text-sm" data-testid="pending-invitations">
            {pending.map((i) => {
              const role = personRole(i.org_role, i.team_role);
              return (
                <li key={i.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
                  <span>
                    <span className="font-medium">{i.email}</span>{" "}
                    <span className="text-muted">
                      {[teamName(i.team_id), role ? t(`personRoles.${role}`) : null].filter(Boolean).join(": ")} ·{" "}
                      {t("settings.expires", { date: format.dateTime(new Date(i.expires_at), { dateStyle: "medium" }) })}
                    </span>
                  </span>
                  <Button variant="ghost" className="hit min-h-8 px-2 py-1" onClick={() => revoke.mutate(i.id)}>
                    {t("settings.revoke")}
                  </Button>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </section>
  );
}

export function SecuritySection({ me, isAdmin }: { me: Me; isAdmin: boolean }) {
  const t = useTranslations();
  const router = useRouter();
  const [setup, setSetup] = useState<Schemas["TotpSetupOut"] | null>(null);
  const [qr, setQr] = useState<string>("");
  const [error, setError] = useState<ErrorKey | null>(null);
  const [enabled, setEnabled] = useState(me.totp_enabled);
  const [busy, setBusy] = useState(false);
  const [codes, setCodes] = useState<string[] | null>(null);

  useEffect(() => {
    if (setup) void QRCode.toString(setup.otpauth_uri, { type: "svg", margin: 1, width: 180 }).then(setQr);
  }, [setup]);

  async function confirm(e: FormEvent<HTMLFormElement>, path: "/v1/me/totp/enable" | "/v1/me/totp/disable") {
    e.preventDefault();
    const code = String(new FormData(e.currentTarget).get("code"));
    setBusy(true);
    const res = await api.POST(path, { body: { code } });
    setBusy(false);
    if (res.error) return setError(errorKey(res.error));
    setError(null);
    setSetup(null);
    setEnabled(path.endsWith("enable"));
    if (path === "/v1/me/totp/enable") setCodes((res.data as { recovery_codes: string[] }).recovery_codes);
    router.refresh();
  }

  async function regenerate(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const code = String(new FormData(e.currentTarget).get("code"));
    const { data, error } = await api.POST("/v1/me/totp/recovery-codes", { body: { code } });
    if (error) return setError(errorKey(error));
    setError(null);
    setCodes(data.recovery_codes);
    router.refresh();
  }

  return (
    <section id="security" aria-labelledby="security-title" className="space-y-3">
      <h2 id="security-title" className="text-lg font-semibold">
        {t("settings.security")}
      </h2>
      <div className="border-t border-foreground/15 pt-5 space-y-4">
        <h3 className="font-semibold">{t("settings.twoFactorTitle")}</h3>
        {error && <Alert>{t(`errors.${error}`)}</Alert>}
        <p className="text-sm text-muted" data-testid="totp-state">
          {enabled ? t("settings.twoFactorOn") : t("settings.twoFactorOff")}
          {!enabled && isAdmin && ` ${t("settings.twoFactorAdmins")}`}
        </p>
        {!enabled && !setup && (
          <Button
            variant="secondary"
            onClick={async () => {
              const { data, error } = await api.POST("/v1/me/totp/setup");
              if (error) return setError(errorKey(error));
              setSetup(data);
            }}
          >
            {t("settings.twoFactorStart")}
          </Button>
        )}
        {setup && (
          <form onSubmit={(e) => confirm(e, "/v1/me/totp/enable")} className="space-y-3">
            <p className="text-sm">{t("settings.twoFactorScan")}</p>
            {/* QR is generated locally from our own otpauth URI */}
            <div className="w-fit bg-white p-2" aria-hidden dangerouslySetInnerHTML={{ __html: qr }} />
            <p className="text-sm">
              {t("settings.twoFactorSecret")}: <code className="break-all" data-testid="totp-secret">{setup.secret}</code>
            </p>
            <Input label={t("auth.totpCode")} name="code" inputMode="numeric" autoComplete="one-time-code" maxLength={6} required />
            <Button type="submit" loading={busy}>
              {t("settings.twoFactorConfirm")}
            </Button>
          </form>
        )}
        {codes && (
          <div className="space-y-2 bg-surface p-4" data-testid="recovery-codes">
            <p className="text-sm font-medium">{t("settings.recoveryTitle")}</p>
            <p className="text-sm text-muted">{t("settings.recoveryHint")}</p>
            <ul className="grid grid-cols-2 gap-1 font-mono text-sm sm:grid-cols-5">
              {codes.map((c) => (
                <li key={c}>{c}</li>
              ))}
            </ul>
            <Button variant="secondary" onClick={() => void navigator.clipboard?.writeText(codes.join("\n"))}>
              {t("share.copy")}
            </Button>
          </div>
        )}
        {enabled && !codes && (
          <p className="text-sm text-muted">{t("settings.recoveryLeft", { count: me.recovery_codes_left ?? 0 })}</p>
        )}
        {enabled && (
          <form onSubmit={regenerate} className="flex flex-wrap items-end gap-3" aria-label={t("settings.recoveryNew")}>
            <Input label={t("auth.totpCode")} name="code" inputMode="numeric" autoComplete="one-time-code" maxLength={6} required />
            <Button type="submit" variant="secondary">
              {t("settings.recoveryNew")}
            </Button>
          </form>
        )}
        {enabled && (
          <form onSubmit={(e) => confirm(e, "/v1/me/totp/disable")} className="flex flex-wrap items-end gap-3">
            <Input label={t("auth.totpCode")} name="code" inputMode="numeric" autoComplete="one-time-code" maxLength={6} required />
            <Button type="submit" variant="secondary" loading={busy}>
              {t("settings.twoFactorDisable")}
            </Button>
          </form>
        )}
      </div>
    </section>
  );
}
