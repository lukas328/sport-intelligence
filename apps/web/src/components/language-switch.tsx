"use client";

import { useRouter } from "next/navigation";
import { useLocale } from "next-intl";
import { LOCALE_COOKIE, locales, type Locale } from "@/i18n/config";
import { cn } from "@/lib/utils";

/** The languages written out in their own language (UX test B06). */
export const LANGUAGE_NAMES: Record<Locale, string> = { "de-CH": "Deutsch", fr: "Français", en: "English" };

export function setLanguage(l: Locale) {
  document.cookie = `${LOCALE_COOKIE}=${l}; path=/; max-age=${60 * 60 * 24 * 365}; samesite=lax`;
}

/** Three words, the current one in ink: «Deutsch · Français · English». */
export function LanguageSwitch({ className }: { className?: string }) {
  const router = useRouter();
  const current = useLocale() as Locale;
  return (
    <span className={cn("flex items-center gap-1 text-[13px]", className)} role="group" aria-label="Sprache · Langue · Language" data-testid="language-switch">
      {locales.map((l) => (
        <button
          key={l}
          type="button"
          lang={l}
          aria-pressed={l === current}
          onClick={() => {
            setLanguage(l);
            router.refresh();
          }}
          className={cn("min-h-11 cursor-pointer bg-transparent px-1.5", l === current ? "font-bold text-ink underline decoration-[1.5px] underline-offset-4" : "text-ink-2 hover:text-ink")}
        >
          {LANGUAGE_NAMES[l]}
        </button>
      ))}
    </span>
  );
}
