import Link from "next/link";
import { cookies } from "next/headers";
import { getTranslations } from "next-intl/server";
import type { ReactNode } from "react";
import { BrandWordmark } from "@/components/brand";
import { buttonClass } from "@/components/ui/button";

/** Public pages, sign-in, onboarding and back office: a quiet header and centred content. */
export default async function SiteLayout({ children }: { children: ReactNode }) {
  const t = await getTranslations();
  const signedIn = Boolean((await cookies()).get("hb_session"));
  return (
    <div className="flex min-h-dvh flex-col">
      <header>
        <nav aria-label={t("shell.mainNav")} className="mx-auto flex w-full max-w-6xl items-center justify-between px-4 py-4 sm:px-6">
          <Link href="/" className="rounded-lg">
            <BrandWordmark name={t("app.name")} />
          </Link>
          <div className="flex items-center gap-1 text-sm">
            <Link href="/status" className="rounded-full px-3 py-2 text-muted hover:bg-surface hover:text-foreground">
              {t("nav.status")}
            </Link>
            <Link href={signedIn ? "/app" : "/login"} className={buttonClass("secondary", "sm")}>
              {signedIn ? t("nav.app") : t("nav.login")}
            </Link>
          </div>
        </nav>
      </header>
      <main id="main" className="mx-auto w-full max-w-6xl flex-1 px-4 pt-6 pb-16 sm:px-6 sm:pt-10">
        {children}
      </main>
    </div>
  );
}
