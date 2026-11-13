"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/card";
import { Input } from "@/components/ui/field";
import { api } from "@/lib/client";
import { errorKey, type ErrorKey } from "@/lib/errors";

export default function ForgotPage() {
  const t = useTranslations();
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
      {sent ? (
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
