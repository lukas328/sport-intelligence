import Link from "next/link";
import { messages, type Locale } from "@/lib/i18n";
import { STATUS_URL, SUPPORT_EMAIL } from "@/lib/site";

export function Footer({ locale }: { locale: Locale }) {
  const m = messages(locale);
  const col = (title: string, items: [string, string][]) => (
    <div>
      <h2 className="mb-2 text-sm font-semibold">{title}</h2>
      <ul className="space-y-1 text-sm text-muted">
        {items.map(([href, label]) => (
          <li key={href}>
            {href.startsWith("http") || href.startsWith("mailto:") ? (
              <a href={href} className="hover:underline">{label}</a>
            ) : (
              <Link href={`/${locale}/${href}/`} className="hover:underline">{label}</Link>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
  const support: [string, string][] = [
    ["hilfe", m.nav.help],
    ["aufnahme", m.nav.recording],
    ["kontakt", m.nav.contact],
    [`mailto:${SUPPORT_EMAIL}`, SUPPORT_EMAIL],
  ];
  if (STATUS_URL) support.push([STATUS_URL, m.footer.status]);
  return (
    <footer className="mt-16 border-t border-border bg-surface">
      <div className="mx-auto grid max-w-6xl gap-8 px-4 py-10 sm:grid-cols-3">
        {col(m.footer.product, [
          ["funktionen", m.nav.features],
          ["preise", m.nav.pricing],
          ["demo", m.nav.demo],
          ["blog", m.nav.blog],
        ])}
        {col(m.footer.support, support)}
        {col(m.footer.legal, [
          ["agb", m.footer.terms],
          ["datenschutz", m.footer.privacy],
          ["impressum", m.footer.imprint],
        ])}
      </div>
    </footer>
  );
}
