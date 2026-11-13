import { KitScope } from "@/components/kit";
import { PageHead } from "@/components/wurf-head";
import { legalBody, mdxComponents } from "@/lib/content";
import { messages, type Locale } from "@/lib/i18n";
import { COMPANY, SUPPORT_EMAIL } from "@/lib/site";

const TITLE = { agb: "terms", datenschutz: "privacy", impressum: "imprint" } as const;

/** Legal pages are drafts until reviewed (OPEN_QUESTIONS Q-ADD-3) and say so. */
export async function LegalPage({ locale, page }: { locale: Locale; page: keyof typeof TITLE }) {
  const m = messages(locale);
  const Body = await legalBody(locale, page);
  return (
    <KitScope>
    <PageHead kick={m.footer.legal} title={m.footer[TITLE[page]]}>
      <p role="note" className="mt-6 inline-block bg-attn px-3 py-1.5 text-[1.0625rem] font-semibold text-ink">{m.legal.draft}</p>
    </PageHead>
    <article className="wrap">
      {page === "impressum" ? (
        <section className="mt-10">
          <h2 className="text-[1.75rem]">{m.legal.company}</h2>
          {COMPANY.name ? (
            <address className="mt-2 whitespace-pre-line not-italic">
              {COMPANY.name}
              {"\n"}
              {COMPANY.address}
              {COMPANY.uid ? `\n${m.legal.uid}: ${COMPANY.uid}` : ""}
            </address>
          ) : (
            <p className="mt-2 text-ink-2">{m.legal.missing}</p>
          )}
          <p className="mt-2">
            {m.legal.contactLine}: <a href={`mailto:${SUPPORT_EMAIL}`} className="font-bold underline decoration-2 underline-offset-4">{SUPPORT_EMAIL}</a>
          </p>
        </section>
      ) : null}
      <div className="prose mt-10">
        <Body components={mdxComponents(locale, "legal")} />
      </div>
    </article>
    </KitScope>
  );
}
