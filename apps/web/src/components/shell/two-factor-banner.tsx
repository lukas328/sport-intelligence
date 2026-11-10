"use client";

import { ShieldAlert, X } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

const KEY = "hb_2fa_banner_closed";

/** Slim reminder for admins of clubs that require 2FA; can be closed for this browser session. */
export function TwoFactorBanner({ orgId }: { orgId: string }) {
  const t = useTranslations();
  const [closed, setClosed] = useState(false);
  useEffect(() => {
    try {
      setClosed(window.sessionStorage.getItem(KEY) === orgId);
    } catch {
      /* storage unavailable: keep showing */
    }
  }, [orgId]);
  if (closed) return null;
  return (
    <div role="status" className="flex min-h-10 items-center gap-3 bg-raised px-4 text-sm shadow-[inset_0_-1px_0_var(--border)] sm:px-6 lg:px-10">
      <ShieldAlert aria-hidden className="size-4 shrink-0 text-accent" />
      <p className="min-w-0 flex-1 truncate py-2">
        {t("settings.twoFactorRequired")}{" "}
        <Link href={`/app/${orgId}/me/security`} className="font-semibold text-accent hover:underline">
          {t("settings.twoFactorStart")}
        </Link>
      </p>
      <button
        type="button"
        aria-label={t("common.close")}
        className="grid size-8 shrink-0 place-items-center rounded-md text-muted hover:bg-surface hover:text-foreground"
        onClick={() => {
          setClosed(true);
          try {
            window.sessionStorage.setItem(KEY, orgId);
          } catch {
            /* ignore */
          }
        }}
      >
        <X aria-hidden className="size-4" />
      </button>
    </div>
  );
}
