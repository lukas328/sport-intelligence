import Link from "next/link";
import { Clapperboard, Smartphone, Zap } from "lucide-react";
import { getTranslations } from "next-intl/server";
import { CourtSvg } from "@/components/court-svg";
import { buttonClass } from "@/components/ui/button";

export default async function HomePage() {
  const t = await getTranslations();
  const features = [
    { Icon: Zap, title: t("home.f1Title"), body: t("home.f1") },
    { Icon: Clapperboard, title: t("home.f2Title"), body: t("home.f2") },
    { Icon: Smartphone, title: t("home.f3Title"), body: t("home.f3") },
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
      <ul className="grid gap-4 sm:grid-cols-3">
        {features.map(({ Icon, title, body }) => (
          <li key={title} className="space-y-3 rounded-2xl bg-raised p-6 ring-1 ring-border/70">
            <span className="grid size-10 place-items-center rounded-xl bg-accent/10 text-accent">
              <Icon aria-hidden className="size-5" />
            </span>
            <h2 className="text-lg font-bold">{title}</h2>
            <p className="text-sm text-muted">{body}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}
