import type { Metadata } from "next";
import Link from "next/link";
import { HallCamera } from "@/components/figures";
import { JsonLd } from "@/components/json-ld";
import { KitScope, StartLink } from "@/components/kit";
import { MailLine } from "@/components/mail-line";
import { PageHead, SectionHead, Updated } from "@/components/wurf-head";
import { APP_LOCALE, messages, type Locale } from "@/lib/i18n";
import { ORG_ID, graph, organization, webPage } from "@/lib/schema";
import { pageMeta } from "@/lib/seo";
import { launchState } from "@/lib/files";
import { LAUNCHED } from "@/lib/site";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = messages(locale).us;
  return pageMeta(locale, "ueber-uns", t.metaTitle, t.description);
}

/**
 * «Über uns»: what we want and how we work, in «wir». No people, dates, customer numbers or clubs as
 * references until Lukas supplies them (docs/site/SEO.md, «Braucht Lukas»).
 */
export default async function AboutUs({ params }: Props) {
  const { locale } = await params;
  const m = messages(locale);
  const t = m.us;
  return (
    <KitScope>
      <JsonLd data={graph(organization(), { ...webPage(locale, "ueber-uns", t.metaTitle, t.description, undefined, "AboutPage"), about: { "@id": ORG_ID } })} />
      <PageHead kick={t.title} title={t.head} lead={t.lead}>
        <Updated locale={locale} />
        {!LAUNCHED && <p className="mt-4 max-w-[40rem] border-l-4 border-attn bg-paper px-4 py-2 text-[1.0625rem]">{launchState(m)}</p>}
      </PageHead>
      <div className="wrap">
        <div className="mt-12 grid grid-cols-1 gap-12 lg:grid-cols-[minmax(0,1fr)_minmax(0,26rem)]">
          <div className="min-w-0">
            {t.sections.map((s, i) => (
              <section key={s.title} aria-labelledby={`u-${i}`} className="mb-12">
                <h2 id={`u-${i}`} className="section-head text-[1.75rem] md:text-[2.125rem]">
                  {s.title}
                </h2>
                {s.text.map((p) => (
                  <p key={p.slice(0, 24)} className="measure mt-4 leading-[1.6]">
                    {p}
                  </p>
                ))}
                {i === 2 && (
                  <Link href={`/${locale}/so-funktioniert-es/#kann`} className="link mt-3">
                    {m.cta.honest}
                  </Link>
                )}
                {i === 3 && (
                  <Link href={`/${locale}/daten/`} className="link mt-3">
                    {m.cta.data}
                  </Link>
                )}
              </section>
            ))}
          </div>
          <div className="min-w-0">
            <div className="lg:sticky lg:top-6">
              <HallCamera label={m.filming.planLabel} camera={m.filming.planCamera} field={m.filming.planField} corner={m.filming.planCorner} caption={t.pictureCaption} />
              <figure className="m-0 mt-8 max-w-[18rem]">
                <img src="/screens/start.jpg" alt={t.shotAlt} width={390} height={730} loading="lazy" className="block h-auto w-full border-2 border-ink" />
                <figcaption className="mt-3 text-[1.0625rem] text-ink-2">{t.shotCaption}</figcaption>
              </figure>
            </div>
          </div>
        </div>

        <section aria-labelledby="grundsatz" className="mt-6">
          <SectionHead id="grundsatz" title={m.about.principlesTitle} />
          <ul className="mt-2 grid grid-cols-1 md:grid-cols-3">
            {m.about.principles.map((p) => (
              <li key={p.title} className="border-b border-rule py-6 md:border-b-0 md:px-6 md:first:pl-0 md:[&+li]:border-l md:[&+li]:border-l-rule">
                <h3 className="font-slant text-[1.5rem]">{p.title}</h3>
                <p className="mt-1">{p.text}</p>
              </li>
            ))}
          </ul>
        </section>

        <section aria-labelledby="schreib" className="mt-16 border-t-2 border-ink pt-8">
          <h2 id="schreib" className="text-[2rem] md:text-[2.5rem]">
            {t.contactTitle}
          </h2>
          <p className="measure mt-3">
            <MailLine template={t.contact} />
          </p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:flex-wrap">
            <StartLink appLocale={APP_LOCALE[locale]} className="btn btn-ink">
              {m.cta.start}
            </StartLink>
            <Link href={`/${locale}/demo/`} className="btn btn-line">
              {m.cta.demo}
            </Link>
          </div>
        </section>
      </div>
    </KitScope>
  );
}
