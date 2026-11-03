"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";
import { Alert, Card } from "@/components/ui/card";
import { api } from "@/lib/client";
import { errorKey, type ErrorKey } from "@/lib/errors";

export function ConsumeMagicLink() {
  const t = useTranslations();
  const router = useRouter();
  const token = useSearchParams().get("token");
  const [error, setError] = useState<ErrorKey | null>(token ? null : "invalid-token");
  const started = useRef(false);

  useEffect(() => {
    if (!token || started.current) return;
    started.current = true;
    api.POST("/v1/auth/magic-link/consume", { body: { token } }).then(({ data, error }) => {
      if (error) return setError(errorKey(error));
      router.replace(data.status === "totp_required" ? "/login?totp=1" : "/app");
      router.refresh();
    });
  }, [token, router]);

  return (
    <Card className="space-y-4">
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
    </Card>
  );
}
