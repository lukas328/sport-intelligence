"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";
import { Alert } from "@/components/ui/card";
import { api } from "@/lib/client";
import { errorKey, type ErrorKey } from "@/lib/errors";
import { enterApp } from "@/lib/nav";

export function ConsumeMagicLink() {
  const t = useTranslations();
  const token = useSearchParams().get("token");
  const [error, setError] = useState<ErrorKey | null>(token ? null : "invalid-token");
  const started = useRef(false);

  useEffect(() => {
    if (!token || started.current) return;
    started.current = true;
    api.POST("/v1/auth/magic-link/consume", { body: { token } }).then(({ data, error }) => {
      if (error) return setError(errorKey(error));
      enterApp(data.status === "totp_required" ? "/login?totp=1" : "/app", { replace: true });
    });
  }, [token]);

  return (
    <div className="space-y-4 border-t-2 border-ink pt-6">
      <h1 className="text-2xl font-bold sm:text-[1.75rem]">{t("auth.magicTitle")}</h1>
      {error ? (
        <>
          <Alert>{t(`errors.${error}`)}</Alert>
          <Link href="/login" className="text-sm font-medium text-accent hover:underline">
            {t("auth.toLogin")}
          </Link>
        </>
      ) : (
        <p role="status" className="text-muted">
          {t("auth.magicConsuming")}
        </p>
      )}
    </div>
  );
}
