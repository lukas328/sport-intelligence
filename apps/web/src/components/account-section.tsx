"use client";

import type { Schemas } from "@handball/api-client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useFormatter, useTranslations } from "next-intl";
import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/card";
import { Input } from "@/components/ui/field";
import { api } from "@/lib/client";
import { errorKey, type ErrorKey } from "@/lib/errors";

type Me = Schemas["MeOut"];

function deviceName(ua: string | null | undefined, fallback: string): string {
  if (!ua) return fallback;
  const os = /iPhone|iPad|Android|Mac OS X|Windows|Linux/.exec(ua)?.[0]?.replace("Mac OS X", "macOS");
  const browser = /Edg|Firefox|Chrome|Safari/.exec(ua)?.[0]?.replace("Edg", "Edge");
  return [browser, os].filter(Boolean).join(" · ") || fallback;
}

export function AccountSection({ me }: { me: Me }) {
  const t = useTranslations();
  const format = useFormatter();
  const qc = useQueryClient();
  const [pwError, setPwError] = useState<ErrorKey | null>(null);
  const [pwDone, setPwDone] = useState(false);
  const [resent, setResent] = useState(false);
  const [resendError, setResendError] = useState<ErrorKey | null>(null);
  const [hasPassword, setHasPassword] = useState(me.has_password);
  // a long list of old sign-ins made the page thousands of pixels long: this device and the latest few
  const [allSessions, setAllSessions] = useState(false);
  const sessions = useQuery({
    queryKey: ["sessions"],
    queryFn: async () => (await api.GET("/v1/me/sessions")).data ?? [],
  });
  const revoke = useMutation({
    mutationFn: async (id: string) => api.DELETE("/v1/me/sessions/{session_id}", { params: { path: { session_id: id } } }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["sessions"] }),
  });
  const revokeOthers = useMutation({
    mutationFn: async () => api.POST("/v1/me/sessions/revoke-others"),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["sessions"] }),
  });

  async function changePassword(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const f = new FormData(form);
    const { error } = await api.POST("/v1/me/password", {
      body: {
        current_password: hasPassword ? String(f.get("current")) : null,
        new_password: String(f.get("new")),
      },
    });
    if (error) {
      setPwDone(false);
      return setPwError(errorKey(error));
    }
    setPwError(null);
    setPwDone(true);
    setHasPassword(true);
    form.reset();
    void qc.invalidateQueries({ queryKey: ["sessions"] });
  }

  const others = (sessions.data ?? []).filter((s) => !s.current).length;
  return (
    <section aria-labelledby="account-title" className="space-y-3">
      <h2 id="account-title" className="text-lg font-semibold">
        {t("account.title")}
      </h2>
      {!me.email_verified && (
        <Alert kind="info">
          {t("account.emailUnverified")}{" "}
          {resent ? (
            t("account.resent")
          ) : (
            <button
              type="button"
              className="underline underline-offset-4"
              onClick={async () => {
                const { error } = await api.POST("/v1/me/email/verify");
                if (error) return setResendError(errorKey(error));
                setResendError(null);
                setResent(true);
              }}
            >
              {t("account.resend")}
            </button>
          )}
          {resendError && <span className="block mt-1">{t(`errors.${resendError}`)}</span>}
        </Alert>
      )}
      <div className="border-t border-foreground/15 pt-5 space-y-3">
        <h3 className="font-semibold">{t("account.passwordTitle")}</h3>
        {me.linked_providers.length > 0 && (
          <p className="text-sm text-muted">
            {t("account.linked", { providers: me.linked_providers.map((p) => t(`account.method_${p as "google"}`)).join(", ") })}
          </p>
        )}
        {!hasPassword && <p className="text-sm text-muted">{t("account.setPasswordIntro")}</p>}
        {pwError && <Alert>{t(`errors.${pwError}`)}</Alert>}
        {pwDone && <Alert kind="success">{t("account.passwordChanged")}</Alert>}
        <form onSubmit={changePassword} className="grid gap-3 sm:grid-cols-2" aria-label={t("account.passwordTitle")}>
          {hasPassword && (
            <Input label={t("account.currentPassword")} name="current" type="password" autoComplete="current-password" required />
          )}
          <Input
            label={t("auth.newPassword")}
            name="new"
            type="password"
            autoComplete="new-password"
            minLength={10}
            required
            hint={t("auth.passwordHint")}
          />
          <div className="sm:col-span-2">
            <Button type="submit" variant="secondary">
              {hasPassword ? t("account.changePassword") : t("account.setPassword")}
            </Button>
          </div>
        </form>
      </div>
      <div className="border-t border-foreground/15 pt-5 space-y-3">
        <h3 className="font-semibold">{t("account.sessionsTitle")}</h3>
        <ul className="divide-y divide-border/70 text-sm" data-testid="sessions">
          {[...(sessions.data ?? [])]
            .sort((a, b) => Number(b.current) - Number(a.current))
            .slice(0, allSessions ? undefined : 5)
            .map((s) => (
            <li key={s.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
              <span>
                <span className="font-medium">{deviceName(s.user_agent, t("account.unknownDevice"))}</span>{" "}
                <span className="text-muted">
                  {t(`account.method_${s.method as "password"}`)} ·{" "}
                  {t("account.lastSeen", {
                    date: format.dateTime(new Date(s.last_seen_at ?? s.created_at), { dateStyle: "medium", timeStyle: "short" }),
                  })}
                </span>
              </span>
              {s.current ? (
                <span className="text-xs font-medium text-ok">{t("account.thisDevice")}</span>
              ) : (
                <Button variant="ghost" className="min-h-8 px-2 py-1" onClick={() => revoke.mutate(s.id)}>
                  {t("account.signOutDevice")}
                </Button>
              )}
            </li>
          ))}
        </ul>
        {!allSessions && (sessions.data ?? []).length > 5 && (
          <button type="button" className="block min-h-8 text-sm font-medium underline underline-offset-4" onClick={() => setAllSessions(true)}>
            {t("account.sessionsAll", { n: (sessions.data ?? []).length })}
          </button>
        )}
        {others > 0 && (
          <Button variant="secondary" onClick={() => revokeOthers.mutate()} loading={revokeOthers.isPending}>
            {t("account.signOutOthers")}
          </Button>
        )}
      </div>
    </section>
  );
}
