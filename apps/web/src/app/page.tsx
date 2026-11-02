import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { CourtSvg } from "@/components/court-svg";

export default async function HomePage() {
  const t = await getTranslations();
  return (
    <div className="space-y-8">
      <section className="space-y-3">
        <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">{t("app.tagline")}</h1>
        <p className="max-w-2xl text-lg text-muted">{t("app.description")}</p>
        <p className="text-sm text-muted">{t("home.foundation")}</p>
        <Link
          href="/register"
          className="inline-block rounded-md bg-accent px-4 py-2 text-sm font-medium text-accent-contrast"
        >
          {t("home.cta")}
        </Link>
      </section>
      <CourtSvg label={t("home.courtLabel")} />
    </div>
  );
}
