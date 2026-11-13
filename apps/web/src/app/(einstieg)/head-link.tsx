"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";

/** The public entry offers «Anmelden»; the onboarding of a signed-in coach «Abbrechen» to the app. */
export function HeadLink() {
  const t = useTranslations();
  const entry = usePathname().startsWith("/einstieg");
  return (
    <Link href={entry ? "/login" : "/app"} className="min-h-11 content-center text-[15px] font-bold text-ink underline decoration-[1.5px] underline-offset-4">
      {entry ? t("entry.login") : t("onboarding.cancel")}
    </Link>
  );
}
