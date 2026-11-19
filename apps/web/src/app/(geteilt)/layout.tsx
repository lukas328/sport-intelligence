import { getLocale, getTranslations } from "next-intl/server";
import type { ReactNode } from "react";
import { serverApi } from "@/lib/api";
import { DEFAULT_SITE_URL, sitePage } from "@/lib/site";

/**
 * A shared link (SPEC 7.8, K20): no site bar, no login wall, the page brings the club's own
 * narrow head. Underneath, discreetly, where it was made: a link to the website in the viewer's
 * language that carries `?src=shared`, so a sign-up from here is counted (website review).
 */
export default async function SharedLayout({ children }: { children: ReactNode }) {
  const t = await getTranslations("share");
  const locale = await getLocale();
  const site = (await (await serverApi()).GET("/v1/public/config")).data?.site_url || DEFAULT_SITE_URL;
  const href = `${sitePage(site, locale)}?src=shared`;
  return (
    <>
      <main id="main" className="mx-auto min-h-[calc(100dvh-5rem)] w-full max-w-6xl px-4 pb-12 sm:px-6">
        {children}
      </main>
      <footer className="mx-auto w-full max-w-6xl px-4 py-5 text-sm text-muted sm:px-6" data-testid="made-with">
        <a href={href} className="underline decoration-1 underline-offset-4 hover:text-ink">
          {t("madeWith")}
        </a>
      </footer>
    </>
  );
}
