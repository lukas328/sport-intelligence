import { getLocale, getTranslations } from "next-intl/server";
import { serverApi } from "@/lib/api";
import { sitePage } from "@/lib/site";
import type { ReactNode } from "react";
import { LanguageSwitch } from "@/components/language-switch";

/** Sign-in and registration: the claim slanted with the Keil (Anlauf), the form beside it. */
export default async function AuthLayout({ children }: { children: ReactNode }) {
  const t = await getTranslations("app");
  const ta = await getTranslations("auth");
  const locale = await getLocale();
  // the website's address from the configuration, with its language path (UX test N06)
  const site = (await (await serverApi()).GET("/v1/public/config")).data?.site_url ?? null;
  return (
    <div className="mx-auto grid w-full max-w-5xl gap-6 lg:grid-cols-[1.05fr_1fr] lg:gap-10">
      <section className="relative px-1 pt-2 pb-10 lg:min-h-[30rem] lg:pt-10">
        {/* the only place before the app that shows the brand: the word mark large, two-coloured */}
        {/* eslint-disable-next-line @next/next/no-img-element -- a static SVG mark */}
        <img src="/brand/wortmarke-zweizeilig.svg" alt={t("name")} width={256} height={90} className="mb-8 h-[72px] w-auto sm:h-[90px]" />
        {/* one sentence and the way to the website; the product is explained there (UX test Z2) */}
        <p className="font-slant max-w-[22rem] text-[2.5rem] leading-[0.95] sm:text-[3.25rem]">{ta("claim")}</p>
        {site && (
          <a href={sitePage(site, locale)} className="mt-4 inline-flex min-h-11 items-center text-[17px] font-bold text-ink underline decoration-[1.5px] underline-offset-4">
            {ta("toSite", { site: site.replace(/^https?:\/\//, "") })}
          </a>
        )}
        <span aria-hidden data-keil="" className="absolute right-0 bottom-0 left-0 h-3.5 bg-club shadow-[inset_0_0_0_1.5px_var(--club-edge)] [clip-path:polygon(0_0,100%_78%,100%_100%,0_100%)] md:h-[22px]" />
      </section>
      <div className="w-full max-w-[28rem] lg:self-center">
        {children}
        {/* on phones the language sits under the form (the head has no room) */}
        <LanguageSwitch className="mt-6 sm:hidden" />
      </div>
    </div>
  );
}
