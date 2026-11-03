"use client";

import { track } from "@/lib/analytics";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { useState, type FormEvent, type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { Alert, Card } from "@/components/ui/card";
import { Checkbox, Input } from "@/components/ui/field";
import { api } from "@/lib/client";
import { errorKey, fieldErrors, type ErrorKey } from "@/lib/errors";

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
  const router = useRouter();
  const [error, setError] = useState<ErrorKey | null>(null);
  const [fields, setFields] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
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
    router.push(invitationToken ? "/app" : "/onboarding");
    router.refresh();
  }

  return (
    <Card className="space-y-5">
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
        <Checkbox name="terms" label={t("auth.terms")} required />
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
    </Card>
  );
}
