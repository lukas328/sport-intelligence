"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { OnboardingAccount } from "./onboarding-account";

/** The public entry offers «Anmelden»; the onboarding of a signed-in coach the account (Abmelden,
 * Konto löschen, Datenschutz) and «Abbrechen» to the app when there is a club (L7). */
export function HeadLink() {
  const t = useTranslations();
  const entry = usePathname().startsWith("/einstieg");
  if (!entry) return <OnboardingAccount />;
  return (
    <Link href="/login" className="min-h-11 content-center text-[15px] font-bold text-ink underline decoration-[1.5px] underline-offset-4">
      {t("entry.login")}
    </Link>
  );
}
