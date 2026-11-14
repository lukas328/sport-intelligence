import type { Metadata } from "next";
import { PrintButton } from "@/components/print-button";
import { Sheet, ToolPage } from "@/components/tool-page";
import { fileVars } from "@/lib/files";
import { fmt, messages, type Locale } from "@/lib/i18n";
import { pageMeta } from "@/lib/seo";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = messages(locale).tools.matchday;
  return pageMeta(locale, "vorlagen/spieltag", t.metaTitle, t.description);
}

/** The matchday checklist on one A4 sheet. */
export default async function MatchdayTemplate({ params }: Props) {
  const { locale } = await params;
  const m = messages(locale);
  const t = m.tools.matchday;
  const files = fileVars(m);
  return (
    <ToolPage
      locale={locale}
      path="vorlagen/spieltag"
      title={t.title}
      description={t.description}
      lead={t.lead}
      parent={[m.tools.templates.title, `/${locale}/vorlagen/`]}
      more={[`/${locale}/ratgeber/handballspiel-filmen/`, t.more]}
    >
      <Sheet>
        <h2 className="text-[1.75rem] md:text-[2rem]">{t.title}</h2>
        <div className="mt-4 grid grid-cols-1 gap-x-10 md:grid-cols-2 print:grid-cols-2">
          {t.groups.map((g) => (
            <section key={g.title} className="mt-4 break-inside-avoid print:mt-[6mm]">
              <h3 className="font-slant border-b-2 border-ink pb-1 text-[1.375rem]">{g.title}</h3>
              <ul className="mt-1">
                {g.items.map((x) => (
                  <li key={x} className="flex gap-3 border-b border-rule py-2 leading-[1.45] print:py-[2.7mm] print:text-[13pt]">
                    <span aria-hidden className="mt-0.5 size-5 shrink-0 border-2 border-ink print:size-[6.5mm] print:mt-0" />
                    <span>{fmt(x, files)}</span>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      </Sheet>
      <PrintButton label={m.tools.print} />
      <p className="no-print mt-2 text-base text-ink-2">{m.tools.printNote}</p>
    </ToolPage>
  );
}
