import { getTranslations } from "next-intl/server";
import type { ReactNode } from "react";
import { CourtLines } from "@/components/domain/court-lines";

/** Sign-in and registration: the product's stage on one side, the form on the other. */
export default async function AuthLayout({ children }: { children: ReactNode }) {
  const t = await getTranslations("app");
  return (
    <div className="mx-auto grid w-full max-w-5xl gap-6 lg:grid-cols-[1.05fr_1fr] lg:gap-10">
      <section className="relative overflow-hidden bg-club px-6 py-8 text-club-ink sm:px-10 lg:min-h-[34rem] lg:py-12">
        <CourtLines className="absolute -right-6 -bottom-6 hidden aspect-square h-[44%] lg:block" />
        <div className="relative max-w-[22rem]">
          <p className="text-[2.5rem] leading-[0.95] font-display sm:text-[3.25rem]">{t("tagline")}</p>
          <p className="mt-4 hidden text-lg lg:block">{t("description")}</p>
        </div>
      </section>
      <div className="w-full max-w-[28rem] lg:self-center">{children}</div>
    </div>
  );
}
