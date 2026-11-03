import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { CourtSvg } from "@/components/court-svg";
import { buttonClass } from "@/components/ui/button";

export default async function HomePage() {
  const t = await getTranslations();
  const features = [
    { title: t("home.f1Title"), body: t("home.f1") },
    { title: t("home.f2Title"), body: t("home.f2") },
    { title: t("home.f3Title"), body: t("home.f3") },
  ];
  return (
    <div className="space-y-16 sm:space-y-24">
      <section className="grid items-center gap-10 lg:grid-cols-[1.1fr_1fr]">
        <div className="space-y-6">
          <h1 className="text-4xl font-extrabold sm:text-[3.5rem]">{t("app.tagline")}</h1>
          <p className="max-w-xl text-lg text-muted">{t("app.description")}</p>
          <div className="flex flex-wrap gap-3">
            <Link href="/register" className={buttonClass("primary", "lg")}>
              {t("home.cta")}
            </Link>
            <Link href="/login" className={buttonClass("secondary", "lg")}>
              {t("home.login")}
            </Link>
          </div>
          <p className="text-sm text-muted">{t("home.foundation")}</p>
        </div>
        <div className="rounded-3xl bg-raised p-3 shadow-sm ring-1 ring-border/70 sm:p-4">
          <CourtSvg label={t("home.courtLabel")} />
        </div>
      </section>
      <ul className="grid gap-x-10 gap-y-8 border-t border-border pt-10 sm:grid-cols-3">
        {features.map(({ title, body }) => (
          <li key={title} className="space-y-2">
            <h2 className="text-lg font-bold">{title}</h2>
            <p className="text-[0.9375rem] text-muted">{body}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}
