import type { Metadata } from "next";
import { PrintButton } from "@/components/print-button";
import { Sheet, ToolPage, WriteLine } from "@/components/tool-page";
import { messages, type Locale } from "@/lib/i18n";
import { pageMeta } from "@/lib/seo";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = messages(locale).tools.consent;
  return pageMeta(locale, "vorlagen/einwilligung", t.metaTitle, t.description);
}

/** The consent form of the guide «Filmen im Verein», as a sheet to print and sign. */
export default async function ConsentTemplate({ params }: Props) {
  const { locale } = await params;
  const m = messages(locale);
  const t = m.tools.consent;
  return (
    <ToolPage
      locale={locale}
      path="vorlagen/einwilligung"
      title={t.title}
      description={t.description}
      lead={t.lead}
      parent={[m.tools.templates.title, `/${locale}/vorlagen/`]}
      more={[`/${locale}/ratgeber/video-im-verein-einwilligung/`, t.more]}
    >
      <Sheet>
        <h2 className="text-[1.75rem] md:text-[2rem]">{t.sheetTitle}</h2>
        <WriteLine label={t.team} />
        <p className="measure mt-4 leading-[1.6]">{t.intro}</p>
        <p className="mt-6 font-bold">{t.agree}</p>
        <ul className="mt-2">
          {t.items.map((x) => (
            <li key={x} className="flex gap-3 py-2 leading-[1.5] print:py-[3mm]">
              <span aria-hidden className="mt-1 size-5 shrink-0 border-2 border-ink print:size-[7mm] print:mt-0" />
              <span>{x}</span>
            </li>
          ))}
        </ul>
        <p className="measure mt-4 leading-[1.6]">{t.change}</p>
        <p className="measure mt-3 leading-[1.6]">{t.withdraw}</p>
        <div className="grid grid-cols-1 gap-x-10 md:grid-cols-2 print:grid-cols-2">
          <WriteLine label={t.name} />
          <WriteLine label={t.date} />
        </div>
        <WriteLine label={t.sign} />
        <p className="mt-8 text-base print:mt-[10mm] print:text-[12.5pt]">{t.contact}</p>
      </Sheet>
      <PrintButton label={m.tools.print} />
      <p className="no-print mt-2 text-base text-ink-2">{m.tools.printNote}</p>
    </ToolPage>
  );
}
