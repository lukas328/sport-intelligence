import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { BrandMark } from "@/components/brand";
import { buttonClass } from "@/components/ui/button";

export default async function NotFound() {
  const t = await getTranslations("errors");
  return (
    <main id="main" className="grid min-h-dvh place-items-center px-6">
      <div className="max-w-sm text-center">
        <BrandMark className="mx-auto mb-6 size-12" />
        <p className="font-score text-6xl">404</p>
        <h1 className="mt-4 text-2xl font-bold">{t("notFoundTitle")}</h1>
        <p className="mt-2 text-muted">{t("notFoundBody")}</p>
        <Link href="/" className={`${buttonClass("primary")} mt-8`}>
          {t("home")}
        </Link>
      </div>
    </main>
  );
}
