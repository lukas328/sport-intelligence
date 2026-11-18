import Link from "next/link";
import { StartLink } from "@/components/kit";
import { HeaderShell, MenuDisclosure } from "@/components/header-shell";
import { LangMenu, LangSwitch, NavLinks } from "@/components/nav-links";
import { APP_LOCALE, LOCALE_NAMES, LOCALES, messages, type Locale } from "@/lib/i18n";
import { loginUrl } from "@/lib/site";
import { GUIDES } from "../../content/ratgeber";

/**
 * The top bar (BEFUNDE-3 U2): one bar, no strip above it. The one-colour word mark, «Start» and
 * five destinations, then the language as a compact menu («DE»), «Anmelden» as a text link and
 * «Kostenlos starten». On the phone and the tablet the bar is slim and pinned (U12) and the
 * destinations sit behind «Menü» (a word, not a symbol alone), the language first in it as three
 * big buttons; the menu closes on a tap on a link and on every page change (U10).
 */
export function Header({ locale }: { locale: Locale }) {
  const t = messages(locale).nav;
  // the way home first (L2), then four steps of a visitor's question, the guides before the
  // questions (W17, BEFUNDE-3 U8);
  // «Filmen» lives in the footer and under «So funktioniert es»
  const links: [string, string][] = [
    ["", t.homeLink],
    ["so-funktioniert-es", t.how],
    ["demo", t.demo],
    ["preise", t.pricing],
    ["ratgeber", t.guides],
    ["hilfe", t.faq],
  ];
  const app = APP_LOCALE[locale];
  const names = Object.fromEntries(LOCALES.map((l) => [l, LOCALE_NAMES[l]]));
  const missing = Object.fromEntries(
    GUIDES.map((g) => [g.slug, LOCALES.filter((l) => !g.locales.includes(l))]),
  );
  return (
    <HeaderShell>
      <a
        href="#main"
        className="sr-only bg-ink px-4 py-3 font-bold text-ground focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50"
      >
        {t.skip}
      </a>
      <div className="wrap flex min-h-16 items-center gap-x-3 py-1.5 lg:min-h-[5rem] lg:gap-x-1.5 lg:py-2 lg:max-xl:px-6! xl:gap-x-3">
        <Link
          href={`/${locale}/`}
          className="inline-flex shrink-0 items-center lg:py-1"
          aria-label={t.home}
        >
          {/* docs/design/brand2/taktik/final/wortmarke-zweizeilig.svg, a vector at its own size: at
              least 140 px wide (brand rule), here 148 to 159 px */}
          <img
            src="/brand/wortmarke-zweizeilig.svg"
            alt=""
            width={1456}
            height={512}
            className="h-[3.25rem] w-auto xl:h-14"
          />
        </Link>
        {/* from a laptop on, «Start» and the five destinations stand in the bar (S1, L2) */}
        <nav aria-label={t.main} className="hidden min-w-0 flex-1 lg:block">
          <NavLinks locale={locale} links={links} />
        </nav>
        <div className="ml-auto hidden shrink-0 items-center lg:flex lg:pl-2 xl:gap-x-1 xl:pl-4">
          <LangMenu locale={locale} names={names} label={t.language} missing={missing} />
          <a
            href={loginUrl(app)}
            className="inline-flex min-h-12 items-center px-1.5 text-base font-semibold whitespace-nowrap underline decoration-2 underline-offset-[6px] hover:decoration-[3px] xl:px-2 xl:text-[1.0625rem]"
          >
            {t.login}
          </a>
          <StartLink appLocale={app} className="btn btn-ink ml-1.5 min-h-12 whitespace-nowrap max-xl:px-3.5">
            {t.start}
          </StartLink>
        </div>
        <StartLink appLocale={app} className="btn btn-ink ml-auto hidden min-h-12 md:max-lg:inline-flex">
          {t.start}
        </StartLink>
        <MenuDisclosure label={t.menu} className="group ml-auto md:ml-0 lg:hidden">
          <div className="cloth absolute inset-x-0 top-full max-h-[calc(100dvh-4rem)] overflow-y-auto overscroll-contain border-b-2 border-ink">
            <nav aria-label={t.main} className="wrap py-4">
              {/* the language first, clearly visible (L3) */}
              <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-b-2 border-ink pb-4">
                <span className="text-base font-semibold text-ink-2">{t.language}</span>
                <LangSwitch locale={locale} names={names} label={t.language} missing={missing} />
              </div>
              <NavLinks locale={locale} links={links} stacked />
              <div className="mt-4 flex flex-col gap-3 border-t-2 border-ink pt-4 sm:flex-row">
                <StartLink appLocale={app} className="btn btn-ink">
                  {t.start}
                </StartLink>
                <a href={loginUrl(app)} className="btn btn-line">
                  {t.login}
                </a>
              </div>
            </nav>
          </div>
        </MenuDisclosure>
      </div>
    </HeaderShell>
  );
}
