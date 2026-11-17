import { getTranslations } from "next-intl/server";
import type { ReactNode } from "react";
import { serverApi } from "@/lib/api";

/**
 * A shared link (SPEC 7.8, K20): no site bar, no login wall, the page brings the club's own
 * narrow head. Underneath, quietly, where it was made (with a link to the website).
 */
export default async function SharedLayout({ children }: { children: ReactNode }) {
  const t = await getTranslations("share");
  const site = (await (await serverApi()).GET("/v1/public/config")).data?.site_url ?? "https://handball-intelligence.com";
  const href = `${site.replace(/\/$/, "")}/?utm_source=share&utm_medium=chat`;
  return (
    <>
      <main id="main" className="mx-auto min-h-[calc(100dvh-5rem)] w-full max-w-6xl px-4 pb-12 sm:px-6">
        {children}
      </main>
      <footer className="mx-auto w-full max-w-6xl border-t border-rule px-4 py-5 text-[15px] text-ink-2 sm:px-6" data-testid="made-with">
        <a href={href} className="font-semibold text-ink-2 underline decoration-1 underline-offset-4 hover:text-ink">
          {t("madeWith")}
        </a>
        <span className="ml-2">{t("madeWithHint")}</span>
      </footer>
    </>
  );
}
