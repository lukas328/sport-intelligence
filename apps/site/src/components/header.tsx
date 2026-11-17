import Link from "next/link";
import { StartLink } from "@/components/kit";
import { LangSwitch, NavLinks } from "@/components/nav-links";
import { APP_LOCALE, LOCALE_NAMES, LOCALES, messages, type Locale } from "@/lib/i18n";
import { loginUrl } from "@/lib/site";
import { GUIDES } from "../../content/ratgeber";

/**
 * The top bar: the one-colour word mark, «Start» and five destinations and «Kostenlos starten»,
 * from a laptop (1024 px) on with a slim ink strip above for the language switch DE · FR · EN and
 * «Anmelden» (BEFUNDE-2 S1, L2, L3; in one row they would not fit at 1024 px). On the phone and the tablet the destinations sit behind «Menü» (a word,
 * not a symbol alone), the language switch first in it, as three big buttons; a <details>
 * element needs no script.
 */
export function Header({ locale }: { locale: Locale }) {
  const t = messages(locale).nav;
  // the way home first (L2), then four steps of a visitor's question and the guides (W17);
  // «Filmen» lives in the footer and under «So funktioniert es»
  const links: [string, string][] = [
    ["", t.homeLink],
    ["so-funktioniert-es", t.how],
    ["demo", t.demo],
    ["preise", t.pricing],
    ["hilfe", t.faq],
    ["ratgeber", t.guides],
  ];
  const app = APP_LOCALE[locale];
  const names = Object.fromEntries(LOCALES.map((l) => [l, LOCALE_NAMES[l]]));
  const missing = Object.fromEntries(
    GUIDES.map((g) => [g.slug, LOCALES.filter((l) => !g.locales.includes(l))]),
  );
  return (
    <header className="relative z-10 border-b-2 border-ink">
      <a
        href="#main"
        className="sr-only bg-ink px-4 py-3 font-bold text-ground focus:not-sr-only focus:absolute focus:top-2 focus:left-2"
      >
        {t.skip}
      </a>
      {/* from a laptop on, a slim strip above the bar: the language and «Anmelden» (L3, S1) */}
      <div className="hidden bg-ink text-ground lg:block">
        <div className="wrap flex items-center justify-end gap-6">
          <LangSwitch locale={locale} names={names} label={t.language} missing={missing} dark />
          <a
            href={loginUrl(app)}
            className="inline-flex min-h-11 items-center px-1 text-base font-semibold underline decoration-2 underline-offset-[6px] hover:decoration-[3px]"
          >
            {t.login}
          </a>
        </div>
      </div>
      <div className="wrap flex min-h-[5rem] flex-wrap items-center gap-x-4 gap-y-2 py-2 lg:flex-nowrap lg:gap-x-2 xl:gap-x-4">
        <Link
          href={`/${locale}/`}
          className="inline-flex shrink-0 items-center py-1"
          aria-label={t.home}
        >
          {/* docs/design/brand2/taktik/final/wortmarke-zweizeilig.svg, a vector at its own size: at
              least 140 px wide (brand rule), here 145 to 205 px */}
          <img
            src="/brand/wortmarke-zweizeilig.svg"
            alt=""
            width={1456}
            height={512}
            className="h-16 w-auto lg:h-14 xl:h-16"
          />
        </Link>
        {/* from a laptop on, «Start», the five destinations and «Anmelden» stand in the bar (S1, L2) */}
        <nav aria-label={t.main} className="hidden min-w-0 flex-1 lg:block">
          <NavLinks locale={locale} links={links} />
        </nav>
        <div className="ml-auto hidden shrink-0 items-center lg:flex">
          <StartLink appLocale={app} className="btn btn-ink whitespace-nowrap max-xl:px-4">
            {t.start}
          </StartLink>
        </div>
        <StartLink appLocale={app} className="btn btn-ink ml-auto hidden md:max-lg:inline-flex">
          {t.start}
        </StartLink>
        <details className="group ml-auto md:ml-0 lg:hidden">
          <summary className="btn btn-line list-none px-5">{t.menu}</summary>
          <div className="absolute inset-x-0 top-full border-b-2 border-ink bg-ground">
            <nav aria-label={t.main} className="wrap py-4">
              {/* the language first, clearly visible (L3) */}
              <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-b-2 border-ink pb-4">
                <span className="text-base font-semibold text-ink-2">{t.language}</span>
                <LangSwitch
                  locale={locale}
                  names={names}
                  label={t.language}
                  missing={missing}
                  big
                />
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
        </details>
      </div>
    </header>
  );
}
