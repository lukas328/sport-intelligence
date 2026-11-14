import type { Metadata } from "next";
import { RateCalc } from "@/components/calculators";
import { ToolPage } from "@/components/tool-page";
import { messages, type Locale } from "@/lib/i18n";
import { pageMeta } from "@/lib/seo";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = messages(locale).tools.rate;
  return pageMeta(locale, "rechner/wurfquote", t.metaTitle, t.description);
}

/** Shooting and save percentage; the formulas stand on the page, so it works without script. */
export default async function RatePage({ params }: Props) {
  const { locale } = await params;
  const t = messages(locale).tools.rate;
  const guide = locale === "en" ? "/de/ratgeber/wurfquote-torhueterquote/" : `/${locale}/ratgeber/wurfquote-torhueterquote/`;
  return (
    <ToolPage locale={locale} path="rechner/wurfquote" title={t.title} description={t.description} lead={t.lead} more={[guide, t.more]}>
      <div className="mt-10 grid max-w-[60rem] grid-cols-1 gap-12 md:grid-cols-2">
        <div>
          <RateCalc kind="shooting" title={t.shooting} text={t} />
          <p className="mt-4 font-bold">{t.formulaShooting}</p>
        </div>
        <div>
          <RateCalc kind="keeper" title={t.keeper} text={t} />
          <p className="mt-4 font-bold">{t.formulaKeeper}</p>
        </div>
      </div>
      <noscript>
        <p className="mt-6 text-ink-2">{t.noScript}</p>
      </noscript>
    </ToolPage>
  );
}
