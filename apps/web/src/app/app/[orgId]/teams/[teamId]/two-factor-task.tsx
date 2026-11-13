"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { linkClass, SectionHead } from "@/components/anlauf/blocks";
import { useTwoFactorReminder } from "@/components/shell/two-factor-reminder";

/** The two-factor reminder as a quiet task on the team page, once there is something to protect
 * (UX test H13); «Später» puts it away for seven days. */
export function TwoFactorTask({ orgId }: { orgId: string }) {
  const t = useTranslations("shell");
  const r = useTwoFactorReminder();
  if (!r.due) return null;
  return (
    <section aria-labelledby="two-factor" data-testid="two-factor-task">
      <SectionHead as="h2" title={<span id="two-factor">{t("twoFactorTitle")}</span>} />
      <p className="m-0 text-[17px] leading-snug">{t("twoFactorWhy")}</p>
      <p className="mt-3 flex flex-wrap gap-x-5">
        <Link href={`/app/${orgId}/me/security`} className={linkClass}>
          {t("twoFactorDue")}
        </Link>
        <button type="button" onClick={r.later} className="min-h-11 cursor-pointer border-0 bg-transparent p-0 text-[15px] text-ink-2 underline underline-offset-4">
          {t("twoFactorLater")}
        </button>
      </p>
    </section>
  );
}
