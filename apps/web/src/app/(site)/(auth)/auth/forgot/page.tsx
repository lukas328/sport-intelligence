"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { useState, type FormEvent } from "react";
import { Button, buttonClass } from "@/components/ui/button";
import { Alert } from "@/components/ui/card";
import { Input } from "@/components/ui/field";
import { api } from "@/lib/client";
import { errorKey, type ErrorKey } from "@/lib/errors";
import { supportMail, useMailEnabled, useSiteConfig } from "@/lib/site-config";

/** «Passwort vergessen»: a link by mail, or, while no mail goes out, the honest way through the
 * support (finding L2). */
export default function ForgotPage() {
  const t = useTranslations();
  const mail = useMailEnabled();
  const site = useSiteConfig();
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<ErrorKey | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    const { error } = await api.POST("/v1/auth/password/forgot", {
      body: { email: String(new FormData(e.currentTarget).get("email")) },
    });
    setBusy(false);
    if (error) return setError(errorKey(error));
    setSent(true);
  }

  return (
    <div className="space-y-5 border-t-2 border-ink pt-6">
      <h1 className="text-2xl font-bold sm:text-[1.75rem]">{t("auth.forgotTitle")}</h1>
      {error && <Alert>{t(`errors.${error}`)}</Alert>}
      {mail === null ? (
        <span aria-hidden className="block h-24 animate-pulse bg-rule" />
      ) : !mail ? (
        <div className="space-y-4" data-testid="forgot-support">
          <p className="text-[17px]">{t("auth.forgotNoMail")}</p>
          <a href={supportMail(site?.support_email, t("auth.forgotSubject"), t("auth.forgotBody"))} className={buttonClass("primary")}>
            {t("auth.forgotWrite")}
          </a>
          <p className="text-[15px] text-ink-2">{t("auth.forgotAddress", { email: site?.support_email ?? "support@handball-intelligence.com" })}</p>
        </div>
      ) : sent ? (
        <Alert kind="success">{t("auth.forgotSent")}</Alert>
      ) : (
        <form onSubmit={submit} className="space-y-4">
          <p className="text-sm text-muted">{t("auth.forgotIntro")}</p>
          <Input label={t("auth.email")} name="email" type="email" autoComplete="email" required autoFocus />
          <Button type="submit" loading={busy} className="w-full">
            {t("auth.forgotSubmit")}
          </Button>
        </form>
      )}
      <Link href="/login" className="text-sm font-medium text-accent hover:underline">
        {t("auth.toLogin")}
      </Link>
    </div>
  );
}
