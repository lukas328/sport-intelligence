"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { api } from "@/lib/client";
import { useSiteConfig } from "@/lib/site-config";

const KEY = "hb_email_banner_later_until";
const DAYS = 3 * 24 * 3600 * 1000;

/**
 * «Bestätige deine E-Mail-Adresse» (finding L14): one quiet line under the frame while the address
 * is not confirmed, only when mails actually go out (otherwise there is nothing to confirm with).
 * «Später» puts it away for three days in this browser.
 */
export function EmailBanner() {
  const t = useTranslations("shell");
  const site = useSiteConfig();
  const [hidden, setHidden] = useState(true);
  const [state, setState] = useState<"idle" | "sent" | "failed">("idle");
  useEffect(() => {
    try {
      setHidden(Number(window.localStorage.getItem(KEY) ?? 0) > Date.now());
    } catch {
      setHidden(false);
    }
  }, []);
  if (hidden || !site?.mail_enabled) return null;
  return (
    <div className="border-b border-rule bg-surface" data-testid="email-banner">
      <p className="mx-auto m-0 flex max-w-[1440px] flex-wrap items-center gap-x-4 gap-y-1 px-4 py-2 text-[15px] md:px-8" role="status">
        <span className="mr-auto">{state === "sent" ? t("emailSent") : state === "failed" ? t("emailFailed") : t("emailUnconfirmed")}</span>
        {state !== "sent" && (
          <button
            type="button"
            className="min-h-11 cursor-pointer font-bold underline decoration-[1.5px] underline-offset-4"
            onClick={async () => {
              const { error } = await api.POST("/v1/me/email/verify");
              setState(error ? "failed" : "sent");
            }}
          >
            {t("emailResend")}
          </button>
        )}
        <button
          type="button"
          className="min-h-11 cursor-pointer text-ink-2 underline decoration-[1.5px] underline-offset-4"
          onClick={() => {
            try {
              window.localStorage.setItem(KEY, String(Date.now() + DAYS));
            } catch {
              /* storage unavailable: hidden until the page reloads */
            }
            setHidden(true);
          }}
        >
          {t("later")}
        </button>
      </p>
    </div>
  );
}
