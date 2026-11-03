"use client";

import { ChevronLeft } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import type { MouseEvent } from "react";

/** "Back" above a detail page: browser history when we came from inside the app, else `fallback`. */
export function BackLink({ fallback, label }: { fallback: string; label?: string }) {
  const t = useTranslations("common");
  const router = useRouter();
  function onClick(e: MouseEvent<HTMLAnchorElement>) {
    if (typeof document !== "undefined" && document.referrer.startsWith(window.location.origin) && window.history.length > 1) {
      e.preventDefault();
      router.back();
    }
  }
  return (
    <Link href={fallback} onClick={onClick} className="-ml-1 mb-3 inline-flex items-center gap-1 rounded-full py-1 pr-3 pl-1 text-sm font-medium text-muted hover:bg-surface hover:text-foreground">
      <ChevronLeft aria-hidden className="size-4" />
      {label ?? t("back")}
    </Link>
  );
}
