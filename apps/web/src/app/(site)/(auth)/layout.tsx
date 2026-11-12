import { getTranslations } from "next-intl/server";
import type { ReactNode } from "react";

/** Sign-in and registration: the claim slanted with the Keil (Anlauf), the form beside it. */
export default async function AuthLayout({ children }: { children: ReactNode }) {
  const t = await getTranslations("app");
  return (
    <div className="mx-auto grid w-full max-w-5xl gap-6 lg:grid-cols-[1.05fr_1fr] lg:gap-10">
      <section className="relative px-1 pt-2 pb-10 lg:min-h-[30rem] lg:pt-10">
        {/* the only place before the app that shows the brand: the word mark large, two-coloured */}
        <img src="/brand/wortmarke-zweizeilig.svg" alt={t("name")} width={256} height={90} className="mb-8 h-[72px] w-auto sm:h-[90px]" />
        <p className="font-slant max-w-[22rem] text-[2.5rem] leading-[0.95] sm:text-[3.25rem]">{t("tagline")}</p>
        <p className="mt-4 hidden max-w-[22rem] text-[17px] text-ink-2 lg:block">{t("description")}</p>
        <span aria-hidden data-keil="" className="absolute right-0 bottom-0 left-0 h-3.5 bg-club shadow-[inset_0_0_0_1.5px_var(--club-edge)] [clip-path:polygon(0_0,100%_78%,100%_100%,0_100%)] md:h-[22px]" />
      </section>
      <div className="w-full max-w-[28rem] lg:self-center">{children}</div>
    </div>
  );
}
