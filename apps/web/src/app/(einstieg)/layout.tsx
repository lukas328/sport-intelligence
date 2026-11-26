import { getTranslations } from "next-intl/server";
import type { ReactNode } from "react";
import { LanguageSwitch } from "@/components/language-switch";
import { SiteHomeMark } from "@/components/site-back";
import { EntryBack, HeadLink } from "./head-link";

/**
 * Einstieg (SPEC 7.12): a narrow head of its own, «Handball Intelligence · Einstieg» and
 * «Anmelden» (or the account in the onboarding), instead of the site bar. Outside the app: the
 * mark. The mark and «Zur Website» lead back to the website in the visitor's language
 * (BEFUNDE-2 L5): someone who came from there is never stuck here.
 */
export default async function EinstiegLayout({ children }: { children: ReactNode }) {
  const t = await getTranslations();
  return (
    <div className="flex min-h-dvh flex-col">
      <header className="border-b-2 border-ink">
        <div className="mx-auto flex h-14 w-full max-w-6xl items-center justify-between gap-3 px-4 sm:gap-4 md:px-8">
          <p className="m-0 flex min-w-0 items-center gap-1.5 text-[15px] font-bold">
            <SiteHomeMark className="hit inline-flex min-h-11 shrink-0 items-center gap-2.5 text-ink no-underline">
              {/* eslint-disable-next-line @next/next/no-img-element -- a static SVG mark */}
              <img src="/brand/favicon-32.svg" alt="" width={28} height={28} />
              <span className="max-sm:hidden">{t("app.name")}</span>
            </SiteHomeMark>
            <span className="truncate">
              <span aria-hidden className="max-sm:hidden">
                ·{" "}
              </span>
              {t("onboarding.stepTitle")}
            </span>
          </p>
          <span className="flex shrink-0 items-center gap-3 sm:gap-4">
            <EntryBack />
            <LanguageSwitch className="max-sm:hidden" />
            <HeadLink />
          </span>
        </div>
      </header>
      <main id="main" className="mx-auto w-full max-w-6xl flex-1 px-4 pt-6 pb-16 sm:pt-10 md:px-8">
        {children}
        <LanguageSwitch className="mt-10 sm:hidden" />
      </main>
    </div>
  );
}
