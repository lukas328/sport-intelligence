"use client";

// Sections of "Ich" and "Verein" (me/, club/); the single settings page they came from redirects.

import type { Schemas } from "@handball/api-client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useFormatter, useTranslations } from "next-intl";
import QRCode from "qrcode";
import { useEffect, useState, type CSSProperties, type FormEvent } from "react";
import { Strip } from "@/components/anlauf/heads";
import { ShirtPicker } from "@/components/anlauf/shirt-picker";
import { clubStyle } from "@/lib/color";
import { InviteForm } from "@/components/people/invite-form";
import { Button } from "@/components/ui/button";
import { Alert, EmptyState } from "@/components/ui/card";
import { Input } from "@/components/ui/field";
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
  const [colour, setColour] = useState(org.primary_color);
  const [second, setSecond] = useState(org.secondary_color);

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
        primary_color: String(f.get("primary_color")),
        secondary_color: String(f.get("secondary_color")),
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
          <ShirtPicker value={colour} onChange={setColour} legend={t("onboarding.shirtTitle")} />
          <input type="hidden" name="primary_color" value={colour} />
          {/* the preview: the head of a match in the picked colour */}
          <div className="club" style={clubStyle(colour, second) as CSSProperties} data-testid="club-preview">
            <p className="mb-2 text-[15px] font-semibold text-ink-2">{t("settings.clubPreview")}</p>
            <Strip name={org.name} sub={t("settings.clubPreviewSub")} own={null} opp={null} pending={<>&nbsp;</>} />
          </div>
          <details>
            <summary className="min-h-11 cursor-pointer content-center text-[15px] font-bold underline decoration-[1.5px] underline-offset-4">{t("settings.ownColours")}</summary>
            <div className="grid grid-cols-2 gap-3 pt-3">
              <Input label={t("onboarding.primaryColor")} type="color" value={colour} onChange={(e) => setColour(e.target.value)} className="h-11 w-24 p-1" />
              <Input label={t("onboarding.secondaryColor")} name="secondary_color" type="color" value={second} onChange={(e) => setSecond(e.target.value)} className="h-11 w-24 p-1" />
            </div>
          </details>
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
  const format = useFormatter();
  const qc = useQueryClient();
  const teamName = (id: string | null | undefined) => allTeams.find((x) => x.id === id)?.name ?? "";
  const members = useQuery({
    queryKey: ["members", orgId],
    enabled: isAdmin,
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/members", { params: { path: { org_id: orgId } } })).data ?? [],
  });
  const me = useQuery({ queryKey: ["me"], queryFn: async () => (await api.GET("/v1/me")).data });
  const [roleError, setRoleError] = useState<ErrorKey | null>(null);
  const setRole = useMutation({
    mutationFn: async ({ userId, role }: { userId: string; role: "org_admin" | "member" }) => {
      const r = await api.PATCH("/v1/orgs/{org_id}/members/{user_id}", {
        params: { path: { org_id: orgId, user_id: userId } },
        body: { org_role: role },
      });
      if (r.error) throw r.error;
      return role;
    },
    onSuccess: (role, v) => {
      setRoleError(null);
      // stepping down: reload, the admin areas are gone
      if (role === "member" && v.userId === me.data?.id) return void (window.location.href = `/app/${orgId}`);
      void qc.invalidateQueries({ queryKey: ["members", orgId] });
    },
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

  return (
    <section aria-labelledby="people" className="space-y-3">
      <h2 id="people" className="text-lg font-semibold">
        {t("settings.people")}
      </h2>
      {isAdmin && (
        <div className="border-t border-foreground/15 pt-5 space-y-3">
          <h3 className="font-semibold">{t("settings.membersTitle")}</h3>
          {roleError && <Alert>{t(`errors.${roleError}`)}</Alert>}
          {members.data && members.data.length > 0 ? (
            <ul className="divide-y divide-border/70 text-sm">
              {members.data.map((m) => (
                <li key={m.user_id} className="flex flex-wrap justify-between gap-2 py-2">
                  <span>
                    <span className="font-medium">{m.name}</span> <span className="text-muted">{m.email}</span>
                  </span>
                  <span className="text-muted">
                    {[
                      m.org_role === "org_admin" ? t("roles.org_admin") : null,
                      ...Object.entries(m.team_roles).map(([tid, r]) => `${teamName(tid)}: ${t(`roles.${r}`)}`),
                    ]
                      .filter(Boolean)
                      .join(" · ")}
                  </span>
                  {m.org_role === "org_admin" && m.user_id === me.data?.id ? (
                    <Button variant="ghost" className="min-h-8 px-2 py-1" onClick={() => setRole.mutate({ userId: m.user_id, role: "member" })}>
                      {t("members.stepDown")}
                    </Button>
                  ) : m.org_role !== "org_admin" ? (
                    <Button variant="ghost" className="min-h-8 px-2 py-1" onClick={() => setRole.mutate({ userId: m.user_id, role: "org_admin" })}>
                      {t("members.makeAdmin")}
                    </Button>
                  ) : null}
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState title={t("settings.membersEmpty")} />
          )}
        </div>
      )}
      <div className="border-t border-foreground/15 pt-5 space-y-3">
        <h3 className="font-semibold">{t("settings.inviteTitle")}</h3>
        <InviteForm
          orgId={orgId}
          teams={teams}
          isAdmin={isAdmin}
          onInvited={() => void qc.invalidateQueries({ queryKey: ["invitations", orgId] })}
        />
      </div>
      <div className="border-t border-foreground/15 pt-5 space-y-3">
        <h3 className="font-semibold">{t("settings.invitationsTitle")}</h3>
        {pending.length === 0 ? (
          <p className="text-sm text-muted">{t("settings.noInvitations")}</p>
        ) : (
          <ul className="divide-y divide-border/70 text-sm" data-testid="pending-invitations">
            {pending.map((i) => (
              <li key={i.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
                <span>
                  <span className="font-medium">{i.email}</span>{" "}
                  <span className="text-muted">
                    {i.team_role ? `${teamName(i.team_id)}: ${t(`roles.${i.team_role}`)}` : t("roles.org_admin")} ·{" "}
                    {t("settings.expires", { date: format.dateTime(new Date(i.expires_at), { dateStyle: "medium" }) })}
                  </span>
                </span>
                <Button variant="ghost" className="min-h-8 px-2 py-1" onClick={() => revoke.mutate(i.id)}>
                  {t("settings.revoke")}
                </Button>
              </li>
            ))}
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
