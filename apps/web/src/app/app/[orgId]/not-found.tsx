import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { PageHead } from "@/components/anlauf/heads";
import { buttonClass } from "@/components/ui/button";

/** 404 inside the app: in the app frame, the page head with the Keil, one way back (UX test B53). */
export default async function NotFound() {
  const t = await getTranslations("errors");
  return (
    <section className="space-y-6" data-testid="app-not-found">
      <PageHead title={t("notFoundTitle")} />
      <p className="max-w-[60ch] text-[17px] text-ink-2">{t("notFoundBody")}</p>
      <Link href="/app" className={buttonClass("primary")}>
        {t("home")}
      </Link>
    </section>
  );
}
