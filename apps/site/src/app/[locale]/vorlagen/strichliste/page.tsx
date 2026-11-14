import type { Metadata } from "next";
import { PrintButton } from "@/components/print-button";
import { Sheet, ToolPage, WriteLine } from "@/components/tool-page";
import { messages, type Locale } from "@/lib/i18n";
import { pageMeta } from "@/lib/seo";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = messages(locale).tools.tally;
  return pageMeta(locale, "vorlagen/strichliste", t.metaTitle, t.description);
}

/** The tally sheet of «Ein Spiel in 20 Minuten auswerten»: goals by position, per half. */
export default async function TallyTemplate({ params }: Props) {
  const { locale } = await params;
  const m = messages(locale);
  const t = m.tools.tally;
  const table = (caption: string) => (
    <div className="mt-6 overflow-x-auto">
      <table className="w-full min-w-[30rem] border-collapse text-[1.0625rem]">
        <caption className="pb-2 text-left font-bold">{caption}</caption>
        <thead>
          <tr>
            {[t.position, t.first, t.second, t.total].map((h, i) => (
              <th key={h} scope="col" className={`border-b-2 border-ink py-2 text-left ${i ? "w-[22%] pl-3" : ""}`}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {t.rows.map((r) => (
            <tr key={r}>
              <th scope="row" className="border-b border-ink-2 py-2.5 text-left font-normal">
                {r}
              </th>
              <td className="border-b border-l border-ink-2" />
              <td className="border-b border-l border-ink-2" />
              <td className="border-b border-l border-ink-2" />
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
  return (
    <ToolPage
      locale={locale}
      path="vorlagen/strichliste"
      title={t.title}
      description={t.description}
      lead={t.lead}
      parent={[m.tools.templates.title, `/${locale}/vorlagen/`]}
      more={[locale === "en" ? "/de/ratgeber/spiel-auswerten-20-minuten/" : `/${locale}/ratgeber/spiel-auswerten-20-minuten/`, t.more]}
    >
      <Sheet>
        <div className="grid grid-cols-1 gap-x-10 md:grid-cols-[2fr_1fr]">
          <WriteLine label={t.match} />
          <WriteLine label={t.date} />
        </div>
        {table(t.against)}
        {table(t.own)}
        <p className="mt-6 font-bold">{t.notes}</p>
        <div className="mt-2 h-28 border-2 border-ink-2" />
      </Sheet>
      <PrintButton label={m.tools.print} />
      <p className="no-print mt-2 text-base text-ink-2">{m.tools.printNote}</p>
    </ToolPage>
  );
}
