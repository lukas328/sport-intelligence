import type { Metadata } from "next";
import Link from "next/link";
import { HallPlan } from "@/components/hall-plan";
import { Honest } from "@/components/honest";
import { KitScope } from "@/components/kit";
import { PageHead, SectionHead } from "@/components/wurf-head";
import { APP_LOCALE, messages, type Locale } from "@/lib/i18n";
import { pageMeta } from "@/lib/seo";
import { registerUrl } from "@/lib/site";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = messages(locale).how;
  return pageMeta(locale, "so-funktioniert-es", t.title, t.lead);
}

export default async function How({ params }: Props) {
  const { locale } = await params;
  const m = messages(locale);
  const t = m.how;
  return (
    <KitScope>
      <PageHead kick={t.title} title={t.head} lead={t.lead} />
      <div className="wrap">
        <ol className="mt-12">
          {t.steps.map((s, i) => (
            <li key={s.title} className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-5 border-t-2 border-ink py-8 md:grid-cols-[7rem_minmax(0,1fr)_minmax(0,24rem)] md:gap-x-10">
              <span aria-hidden className="font-num text-[4.5rem] leading-[.85] text-club-text md:text-[6.5rem]">
                {i + 1}
              </span>
              <div>
                <h2 className="text-[2rem] md:text-[2.5rem]">{s.title}</h2>
                <p className="measure mt-3">{s.text}</p>
                {i === 0 && (
                  <Link href={`/${locale}/aufnahme/`} className="link mt-2">
                    {m.cta.filming}
                  </Link>
                )}
              </div>
              {i === 0 && (
                <div className="col-span-2 mt-6 md:col-span-1 md:mt-0">
                  <HallPlan label={m.filming.planLabel} camera={m.filming.planCamera} field={m.filming.planField} />
                </div>
              )}
            </li>
          ))}
        </ol>

        <section aria-labelledby="shots" className="mt-16">
          <SectionHead id="shots" title={t.shotsTitle} note={t.shotsNote} />
          <ul className="mt-8 grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-4">
            {t.shots.map((s) => (
              <li key={s.src}>
                <figure className="m-0">
                  <img src={s.src} alt={s.alt} width={390} height={730} loading="lazy" className="block h-auto w-full border-2 border-ink" />
                  <figcaption className="mt-3 text-[1.0625rem]">{s.caption}</figcaption>
                </figure>
              </li>
            ))}
          </ul>
        </section>

        <section aria-labelledby="kann" className="mt-20">
          <SectionHead id="kann" title={m.honest.title} />
          <div className="mt-8">
            <Honest t={m.honest} />
          </div>
        </section>

        <div className="mt-16 flex flex-col gap-3 border-t-2 border-ink pt-10 sm:flex-row sm:flex-wrap">
          <a href={registerUrl(APP_LOCALE[locale])} className="btn btn-ink">
            {m.cta.start}
          </a>
          <Link href={`/${locale}/demo/`} className="btn btn-line">
            {m.cta.demo}
          </Link>
        </div>
        <p className="mt-3 text-[1.0625rem] text-ink-2">{m.cta.trial}</p>
      </div>
    </KitScope>
  );
}
