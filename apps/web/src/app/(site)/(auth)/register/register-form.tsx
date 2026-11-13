"use client";

import { track } from "@/lib/analytics";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { useState, type FormEvent, type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/card";
import { Checkbox, Input } from "@/components/ui/field";
import { api } from "@/lib/client";
import { errorKey, fieldErrors, type ErrorKey } from "@/lib/errors";
import { enterApp } from "@/lib/nav";

export function RegisterForm({
  invitationToken,
  email,
  oauth,
}: {
  invitationToken?: string | undefined;
  email?: string | undefined;
  oauth?: ReactNode;
}) {
  const t = useTranslations();
  const locale = useLocale();
  const [error, setError] = useState<ErrorKey | null>(null);
  const [fields, setFields] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  // the legal pages live on the public site, per language
  const legal = (page: string) => `https://handball-ai.ch${locale === "de-CH" ? "" : `/${locale}`}/${page}`;

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    // checked here in the user's language before the server's English validators speak (UX test B25)
    const local: Record<string, string> = {};
    if (!String(form.get("name") ?? "").trim()) local.name = t("auth.needName");
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(form.get("email") ?? "").trim())) local.email = t("auth.needEmail");
    if (String(form.get("password") ?? "").length < 10) local.password = t("auth.needPassword");
    if (form.get("terms") !== "on") local.terms = t("auth.needTerms");
    if (Object.keys(local).length) {
      setError(null);
      setFields(local);
      return;
    }
    setBusy(true);
    setError(null);
    setFields({});
    const { error } = await api.POST("/v1/auth/register", {
      body: {
        name: String(form.get("name")),
        email: String(form.get("email")),
        password: String(form.get("password")),
        accept_terms: form.get("terms") === "on",
        locale: (["de-CH", "en", "fr"].includes(locale) ? locale : "de-CH") as "de-CH" | "en" | "fr",
        invitation_token: invitationToken ?? null,
      },
    });
    setBusy(false);
    if (!error) track("signed_up", { invited: Boolean(invitationToken) });
    if (error) {
      setError(errorKey(error));
      setFields(fieldErrors(error));
      return;
    }
    enterApp(invitationToken ? "/app" : "/onboarding");
  }

  return (
    <div className="space-y-5 border-t-2 border-ink pt-6">
      <h1 className="text-2xl font-bold sm:text-[1.75rem]">{t("auth.registerTitle")}</h1>
      {error && <Alert>{t(`errors.${error}`)}</Alert>}
      {oauth}
      <form onSubmit={submit} className="space-y-4" noValidate>
        <Input label={t("auth.name")} name="name" autoComplete="name" required autoFocus error={fields.name} />
        <Input
          label={t("auth.email")}
          name="email"
          type="email"
          autoComplete="email"
          required
          defaultValue={email}
          readOnly={Boolean(email)}
          error={fields.email}
        />
        <Input
          label={t("auth.password")}
          name="password"
          type="password"
          autoComplete="new-password"
          minLength={10}
          required
          hint={t("auth.passwordHint")}
          error={fields.password}
        />
        <Checkbox
          name="terms"
          required
          aria-invalid={fields.terms ? true : undefined}
          aria-describedby={fields.terms ? "terms-error" : undefined}
          label={t.rich("auth.terms", {
            terms: (c) => (
              <a href={legal("agb")} target="_blank" rel="noreferrer" className="font-medium underline underline-offset-4">
                {c}
              </a>
            ),
            privacy: (c) => (
              <a href={legal("datenschutz")} target="_blank" rel="noreferrer" className="font-medium underline underline-offset-4">
                {c}
              </a>
            ),
          })}
        />
        {fields.terms && (
          <p id="terms-error" className="-mt-2 text-sm font-medium text-error">
            {fields.terms}
          </p>
        )}
        <Button type="submit" loading={busy} className="w-full">
          {t("auth.submitRegister")}
        </Button>
      </form>
      <p className="text-sm">
        {t("auth.haveAccount")}{" "}
        <Link
          href={invitationToken ? `/login?next=/invite/${invitationToken}` : "/login"}
          className="font-medium text-accent hover:underline"
        >
          {t("auth.toLogin")}
        </Link>
      </p>
    </div>
  );
}
