"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useState, type FormEvent, type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { Alert, Card } from "@/components/ui/card";
import { Input } from "@/components/ui/field";
import { api } from "@/lib/client";
import { errorKey, type ErrorKey } from "@/lib/errors";
import { safeNext } from "@/lib/nav";

type Mode = "password" | "magic" | "totp" | "magic-sent";

export function LoginForm({ oauth }: { oauth?: ReactNode }) {
  const t = useTranslations();
  const router = useRouter();
  const params = useSearchParams();
  const next = safeNext(params.get("next"));
  const [mode, setMode] = useState<Mode>(params.get("totp") ? "totp" : "password");
  const [error, setError] = useState<ErrorKey | null>(params.get("error") ? errorKey({ type: `x:${params.get("error")}` }) : null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    setBusy(true);
    setError(null);
    try {
      if (mode === "password") {
        const { data, error } = await api.POST("/v1/auth/login", {
          body: { email: String(form.get("email")), password: String(form.get("password")) },
        });
        if (error) return setError(errorKey(error));
        if (data.status === "totp_required") return setMode("totp");
        router.push(next);
        router.refresh();
      } else if (mode === "totp") {
        const { error } = await api.POST("/v1/auth/login/totp", { body: { code: String(form.get("code")) } });
        if (error) return setError(errorKey(error));
        router.push(next);
        router.refresh();
      } else if (mode === "magic") {
        const { error } = await api.POST("/v1/auth/magic-link", { body: { email: String(form.get("email")) } });
        if (error) return setError(errorKey(error));
        setMode("magic-sent");
      }
    } finally {
      setBusy(false);
    }
  }

  const title = mode === "totp" ? t("auth.totpTitle") : mode.startsWith("magic") ? t("auth.magicTitle") : t("auth.loginTitle");
  return (
    <Card className="space-y-5">
      <h1 className="text-2xl font-semibold">{title}</h1>
      {error && <Alert>{t(`errors.${error}`)}</Alert>}
      {mode === "password" && oauth}
      {mode === "magic-sent" ? (
        <Alert kind="success">{t("auth.magicSent")}</Alert>
      ) : (
        <form onSubmit={submit} className="space-y-4" noValidate>
          {mode === "totp" ? (
            <>
              <p className="text-sm text-muted">{t("auth.totpIntro")}</p>
              <Input
                label={t("auth.totpCode")}
                name="code"
                inputMode="numeric"
                autoComplete="one-time-code"
                pattern="[0-9]*"
                maxLength={6}
                required
                autoFocus
              />
            </>
          ) : (
            <>
              {mode === "magic" && <p className="text-sm text-muted">{t("auth.magicIntro")}</p>}
              <Input label={t("auth.email")} name="email" type="email" autoComplete="email" required autoFocus />
              {mode === "password" && (
                <>
                  <Input label={t("auth.password")} name="password" type="password" autoComplete="current-password" required />
                  <Link href="/auth/forgot" className="block text-sm text-accent underline underline-offset-4">
                    {t("auth.forgot")}
                  </Link>
                </>
              )}
            </>
          )}
          <Button type="submit" loading={busy} className="w-full">
            {mode === "totp" ? t("auth.totpSubmit") : mode === "magic" ? t("auth.magicSubmit") : t("auth.submitLogin")}
          </Button>
        </form>
      )}
      {mode !== "totp" && (
        <div className="flex flex-col gap-2 text-sm">
          <button
            type="button"
            className="text-left text-accent underline underline-offset-4"
            onClick={() => {
              setError(null);
              setMode(mode === "password" ? "magic" : "password");
            }}
          >
            {mode === "password" ? t("auth.useMagic") : t("auth.usePassword")}
          </button>
          <p>
            {t("auth.noAccount")}{" "}
            <Link href="/register" className="text-accent underline underline-offset-4">
              {t("auth.toRegister")}
            </Link>
          </p>
        </div>
      )}
    </Card>
  );
}
