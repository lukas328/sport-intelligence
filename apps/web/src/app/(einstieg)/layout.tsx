import Link from "next/link";
import { getTranslations } from "next-intl/server";
import type { ReactNode } from "react";

/**
 * Einstieg (SPEC 7.12): a narrow head of its own, «Handball Intelligence · Einstieg» and
 * «Abbrechen», instead of the site bar. Outside the app: the two-coloured mark.
 */
export default async function EinstiegLayout({ children }: { children: ReactNode }) {
  const t = await getTranslations();
  return (
    <div className="flex min-h-dvh flex-col">
      <header className="border-b-2 border-ink">
        <div className="mx-auto flex h-14 w-full max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
          <p className="m-0 flex items-center gap-2.5 text-[15px] font-bold">
            <img src="/brand/favicon-32.svg" alt="" width={28} height={28} />
            <span>
              <span className="max-sm:hidden">{t("app.name")} · </span>
              {t("onboarding.stepTitle")}
            </span>
          </p>
          <Link href="/" className="min-h-11 content-center text-[15px] font-bold text-ink underline decoration-[1.5px] underline-offset-4">
            {t("onboarding.cancel")}
          </Link>
        </div>
      </header>
      <main id="main" className="mx-auto w-full max-w-6xl flex-1 px-4 pt-6 pb-16 sm:px-6 sm:pt-10">
        {children}
      </main>
    </div>
  );
}
