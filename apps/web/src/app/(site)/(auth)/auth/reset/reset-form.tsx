"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Alert, Card } from "@/components/ui/card";
import { Input } from "@/components/ui/field";
import { api } from "@/lib/client";
import { errorKey, type ErrorKey } from "@/lib/errors";

export function ResetForm() {
  const t = useTranslations();
  const router = useRouter();
  const token = useSearchParams().get("token") ?? "";
  const [error, setError] = useState<ErrorKey | null>(token ? null : "invalid-token");
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    const { data, error } = await api.POST("/v1/auth/password/reset", {
      body: { token, password: String(new FormData(e.currentTarget).get("password")) },
    });
    setBusy(false);
    if (error) return setError(errorKey(error));
    router.replace(data.status === "totp_required" ? "/login?totp=1" : "/app");
    router.refresh();
  }

  return (
    <Card className="space-y-5">
      <h1 className="text-2xl font-bold sm:text-[1.75rem]">{t("auth.resetTitle")}</h1>
      {error && <Alert>{t(`errors.${error}`)}</Alert>}
      <form onSubmit={submit} className="space-y-4">
        <Input
          label={t("auth.newPassword")}
          name="password"
          type="password"
          autoComplete="new-password"
          minLength={10}
          required
          autoFocus
          hint={t("auth.passwordHint")}
        />
        <Button type="submit" loading={busy} disabled={!token} className="w-full">
          {t("auth.resetSubmit")}
        </Button>
      </form>
    </Card>
  );
}
