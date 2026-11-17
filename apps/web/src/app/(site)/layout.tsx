import Link from "next/link";
import { cookies } from "next/headers";
import { getTranslations } from "next-intl/server";
import type { ReactNode } from "react";
import { BrandWordmark } from "@/components/brand";
import { LanguageSwitch } from "@/components/language-switch";
import { SiteBackLink, SiteHomeMark } from "@/components/site-back";
import { SiteLoginLink } from "@/components/site-login-link";

/**
 * Public pages, sign-in, onboarding and back office: a quiet header and centred content. Signed
 * out, the word mark and «Zur Website» lead back to the website in the visitor's language
 * (BEFUNDE-2 L5; on the phone the mark, and the sign-in pages name the website under the claim).
 */
export default async function SiteLayout({ children }: { children: ReactNode }) {
  const t = await getTranslations();
  const signedIn = Boolean((await cookies()).get("hb_session"));
  return (
    <div className="flex min-h-dvh flex-col">
      <header>
        <nav aria-label={t("shell.mainNav")} className="mx-auto flex w-full max-w-6xl items-center justify-between px-4 py-4 sm:px-6">
          {signedIn ? (
            <Link href="/" className="">
              <BrandWordmark name={t("app.name")} />
            </Link>
          ) : (
            <SiteHomeMark>
              <BrandWordmark name={t("app.name")} />
            </SiteHomeMark>
          )}
          <div className="flex items-center gap-1 text-sm">
            {!signedIn && <SiteBackLink className="mr-3 max-sm:hidden" />}
            <LanguageSwitch className="max-sm:hidden" />
            <SiteLoginLink signedIn={signedIn} label={signedIn ? t("nav.app") : t("nav.login")} />
          </div>
        </nav>
      </header>
      <main id="main" className="mx-auto w-full max-w-6xl flex-1 px-4 pt-6 pb-16 sm:px-6 sm:pt-10">
        {children}
      </main>
      {/* the service status is for those who look for it, not a word in the head (UX test H10) */}
      <footer className="mx-auto w-full max-w-6xl px-4 pb-6 sm:px-6">
        <Link href="/status" className="inline-flex min-h-11 items-center text-[15px] text-ink-2 underline underline-offset-4">
          {t("nav.status")}
        </Link>
      </footer>
    </div>
  );
}
