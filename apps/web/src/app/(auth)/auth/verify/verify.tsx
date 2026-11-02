"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";
import { Alert, Card } from "@/components/ui/card";
import { api } from "@/lib/client";
import { errorKey, type ErrorKey } from "@/lib/errors";

export function VerifyEmail() {
  const t = useTranslations();
  const token = useSearchParams().get("token");
  const [state, setState] = useState<"busy" | "ok" | ErrorKey>(token ? "busy" : "invalid-token");
  const started = useRef(false);
  useEffect(() => {
    if (!token || started.current) return;
    started.current = true;
    api.POST("/v1/auth/email/verify", { body: { token } }).then(({ error }) => setState(error ? errorKey(error) : "ok"));
  }, [token]);
  return (
    <Card className="space-y-4">
      <h1 className="text-2xl font-semibold">{t("auth.verifyTitle")}</h1>
      {state === "busy" ? (
        <p role="status" className="text-muted">
          {t("auth.verifyBusy")}
        </p>
      ) : state === "ok" ? (
        <Alert kind="success">{t("auth.verifyOk")}</Alert>
      ) : (
        <Alert>{t(`errors.${state}`)}</Alert>
      )}
      <Link href="/app" className="text-sm text-accent underline underline-offset-4">
        {t("auth.toApp")}
      </Link>
    </Card>
  );
}
