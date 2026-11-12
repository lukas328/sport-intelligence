"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { analyticsConfigured, consent, setConsent } from "@/lib/analytics";

/** Asks once whether anonymous usage statistics may be collected (4.12). */
export function ConsentBanner() {
  const t = useTranslations("consentBanner");
  const [ask, setAsk] = useState(false);
  useEffect(() => setAsk(analyticsConfigured() && consent() === null), []);
  if (!ask) return null;
  const choose = (v: "yes" | "no") => {
    setConsent(v);
    setAsk(false);
  };
  return (
    <div role="dialog" aria-label={t("title")} className="fixed inset-x-0 bottom-0 z-50 border-t border-border/70 bg-raised p-4">
      <div className="mx-auto flex max-w-4xl flex-wrap items-center gap-3">
        <p className="min-w-0 flex-1 text-sm">{t("text")}</p>
        <button type="button" className="ring-1 ring-inset ring-border px-3 py-2 text-sm" onClick={() => choose("no")}>
          {t("no")}
        </button>
        <button type="button" className="bg-accent px-3 py-2 text-sm text-accent-contrast" onClick={() => choose("yes")}>
          {t("yes")}
        </button>
      </div>
    </div>
  );
}
