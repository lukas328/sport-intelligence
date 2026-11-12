import Link from "next/link";
import { LangLinks } from "@/components/nav-links";
import { LOCALE_NAMES, LOCALES, messages, type Locale } from "@/lib/i18n";
import { STATUS_URL, SUPPORT_EMAIL } from "@/lib/site";

export function Footer({ locale }: { locale: Locale }) {
  const m = messages(locale);
  const col = (title: string, items: [string, string][]) => (
    <div>
      <h2 className="font-slant text-[1.375rem]">{title}</h2>
      <ul className="mt-2">
        {items.map(([href, label]) => (
          <li key={href}>
            {href.startsWith("http") || href.startsWith("mailto:") ? (
              <a href={href} className="inline-flex min-h-12 items-center underline-offset-4 hover:underline">
                {label}
              </a>
            ) : (
              <Link href={`/${locale}/${href}/`} className="inline-flex min-h-12 items-center underline-offset-4 hover:underline">
                {label}
              </Link>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
  const support: [string, string][] = [
    ["hilfe", m.nav.faq],
    ["daten", m.nav.data],
    ["kontakt", m.nav.about],
    [`mailto:${SUPPORT_EMAIL}`, SUPPORT_EMAIL],
  ];
  if (STATUS_URL) support.push([STATUS_URL, m.footer.status]);
  return (
    <footer className="mt-24 border-t-2 border-ink">
      <div className="wrap grid gap-10 py-12 sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <img src="/brand/wortmarke-quer-einfarbig.svg" alt="Handball Intelligence" width={2150} height={512} className="h-12 w-auto" />
          <p className="mt-4 max-w-[18rem] text-base text-ink-2">{m.footer.note}</p>
        </div>
        {col(m.footer.product, [
          ["so-funktioniert-es", m.nav.how],
          ["aufnahme", m.nav.filming],
          ["demo", m.nav.demo],
          ["preise", m.nav.pricing],
          ["blog", m.nav.blog],
        ])}
        {col(m.footer.support, support)}
        <div>
          {col(m.footer.legal, [
            ["agb", m.footer.terms],
            ["datenschutz", m.footer.privacy],
            ["impressum", m.footer.imprint],
          ])}
          <nav aria-label={m.nav.language} className="mt-6">
            <h2 className="font-slant text-[1.375rem]">{m.nav.language}</h2>
            <LangLinks locale={locale} names={Object.fromEntries(LOCALES.map((l) => [l, LOCALE_NAMES[l]]))} />
          </nav>
        </div>
      </div>
    </footer>
  );
}
