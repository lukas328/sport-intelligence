import { legalBody, mdxComponents } from "@/lib/content";
import { messages, type Locale } from "@/lib/i18n";
import { COMPANY, SUPPORT_EMAIL } from "@/lib/site";

const TITLE = { agb: "terms", datenschutz: "privacy", impressum: "imprint" } as const;

/** Legal pages are drafts until reviewed (OPEN_QUESTIONS Q-ADD-3) and say so. */
export async function LegalPage({ locale, page }: { locale: Locale; page: keyof typeof TITLE }) {
  const m = messages(locale);
  const Body = await legalBody(locale, page);
  return (
    <article className="max-w-3xl">
      <h1 className="text-3xl font-bold">{m.footer[TITLE[page]]}</h1>
      <p role="note" className="mt-4 rounded-xl ring-1 ring-inset ring-border bg-surface p-3 text-sm">{m.legal.draft}</p>
      {page === "impressum" ? (
        <section className="mt-6">
          <h2 className="text-xl font-semibold">{m.legal.company}</h2>
          {COMPANY.name ? (
            <address className="mt-2 whitespace-pre-line not-italic">
              {COMPANY.name}
              {"\n"}
              {COMPANY.address}
              {COMPANY.uid ? `\n${m.legal.uid}: ${COMPANY.uid}` : ""}
            </address>
          ) : (
            <p className="mt-2 text-muted">{m.legal.missing}</p>
          )}
          <p className="mt-2">
            {m.legal.contactLine}: <a href={`mailto:${SUPPORT_EMAIL}`} className="text-accent underline">{SUPPORT_EMAIL}</a>
          </p>
        </section>
      ) : null}
      <div className="prose mt-4">
        <Body components={mdxComponents(locale, "legal")} />
      </div>
    </article>
  );
}
