import type { Metadata } from "next";
import { StorageCalc } from "@/components/calculators";
import { ToolPage } from "@/components/tool-page";
import { fmt, messages, type Locale } from "@/lib/i18n";
import { pageMeta } from "@/lib/seo";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = messages(locale).tools.storage;
  return pageMeta(locale, "rechner/speicher", t.metaTitle, t.description);
}

/** Storage for a recording; the table of guide values carries the answer without script. */
export default async function StoragePage({ params }: Props) {
  const { locale } = await params;
  const t = messages(locale).tools.storage;
  const gb = (mb: number) => String(Math.round((90 * mb) / 100) / 10).replace(".", locale === "en" ? "." : ",");
  return (
    <ToolPage locale={locale} path="rechner/speicher" title={t.title} description={t.description} lead={t.lead} more={[`/${locale}/ratgeber/handballspiel-filmen/`, t.more]}>
      <div className="mt-10 max-w-[44rem]">
        <StorageCalc text={t} options={t.options} />
        <p className="mt-4">{t.resultNote}</p>
        <p className="mt-2 font-bold">{t.formula}</p>
        <h2 className="section-head mt-12 text-[1.75rem]">{t.tableTitle}</h2>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-[1.0625rem] tabular-nums">
            <thead>
              <tr>
                {[t.colSetting, t.colMb, t.colMatch].map((h) => (
                  <th key={h} scope="col" className="border-b-2 border-ink py-2 pr-4 text-left">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {t.options.map((o) => (
                <tr key={o.id}>
                  <th scope="row" className="border-b border-rule py-2 pr-4 text-left font-normal">
                    {o.label}
                  </th>
                  <td className="border-b border-rule py-2 pr-4">{o.mb}</td>
                  <td className="border-b border-rule py-2">{fmt(t.result, { gb: gb(o.mb) })}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-3 text-ink-2">{t.tableNote}</p>
      </div>
    </ToolPage>
  );
}
