"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";
import { Alert } from "@/components/ui/card";
import { api } from "@/lib/client";
import { errorKey, type ErrorKey } from "@/lib/errors";
import { enterApp } from "@/lib/nav";
import { buttonClass } from "@/components/ui/button";
import { ENTRY_EMAIL, remembered } from "@/lib/offline";

export function ConsumeMagicLink() {
  const t = useTranslations();
  const params = useSearchParams();
  const token = params.get("token");
  // the public entry's link goes on to where it left off (an app path only)
  const raw = params.get("next");
  const next = raw && raw.startsWith("/") && !raw.startsWith("//") ? raw : "/app";
  const [error, setError] = useState<ErrorKey | null>(token ? null : "invalid-token");
  const started = useRef(false);
  // the address the entry sent the link to, kept on this phone
  const [email] = useState(() => (typeof window === "undefined" ? undefined : remembered<string>(ENTRY_EMAIL)));
  const [sent, setSent] = useState(false);
  async function again() {
    const r = await api.POST("/v1/auth/start", { body: { email: email!, locale: (document.documentElement.lang || "de-CH") as "de-CH", next } });
    if (!r.error) setSent(true);
  }

  useEffect(() => {
    if (!token || started.current) return;
    started.current = true;
    api.POST("/v1/auth/magic-link/consume", { body: { token } }).then(async ({ data, error }) => {
      if (error) {
        // opened a second time while signed in: straight on (UX test N22)
        if ((await api.GET("/v1/me")).data) return enterApp(next, { replace: true });
        return setError(errorKey(error));
      }
      enterApp(data.status === "totp_required" ? `/login?totp=1&next=${encodeURIComponent(next)}` : next, { replace: true });
    });
  }, [token, next]);

  return (
    <div className="space-y-4 border-t-2 border-ink pt-6">
      <h1 className="text-2xl font-bold sm:text-[1.75rem]">{t("auth.magicTitle")}</h1>
      {error ? (
        <>
          <Alert>{t(`errors.${error}`)}</Alert>
          {/* a new link to the same address, with the same team choice (UX test N22) */}
          {email && (
            <div className="space-y-2">
              {sent ? (
                <p role="status" className="text-[17px]">{t("entry.sentText", { email })}</p>
              ) : (
                <button type="button" className={buttonClass("primary")} onClick={() => void again()} data-testid="magic-again">
                  {t("auth.newLink", { email })}
                </button>
              )}
            </div>
          )}
          <Link href="/login" className="inline-flex min-h-11 items-center text-[15px] font-bold text-ink underline decoration-[1.5px] underline-offset-4">
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
