import { SearchX } from "lucide-react";
import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { buttonClass } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/card";

export default async function NotFound() {
  const t = await getTranslations("errors");
  return (
    <EmptyState
      icon={<SearchX />}
      title={t("notFoundTitle")}
      action={
        <Link href="/app" className={buttonClass("secondary")}>
          {t("home")}
        </Link>
      }
    >
      {t("notFoundBody")}
    </EmptyState>
  );
}
