import type { Metadata } from "next";
import Link from "next/link";
import plans from "@handball/plans";
import { DemoCamera } from "@/components/demo-camera";
import { Honest } from "@/components/honest";
import { JsonLd } from "@/components/json-ld";
import { DemoLink, KitScope, ShirtPicker } from "@/components/kit";
import { Things } from "@/components/things";
import { SectionHead, WurfHead } from "@/components/wurf-head";
import { APP_LOCALE, fmt, messages, type Locale } from "@/lib/i18n";
import { pageMeta } from "@/lib/seo";
import { SITE_URL, SUPPORT_EMAIL, registerUrl } from "@/lib/site";
import { demoView } from "@/lib/things";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  return pageMeta(locale, "", undefined, messages(locale).meta.description);
}

export default async function Home({ params }: Props) {
  const { locale } = await params;
  const m = messages(locale);
  const t = m.home;
  const v = demoView(m);
  const team = plans.plans.find((p) => p.plan === "team")!;
  const start = registerUrl(APP_LOCALE[locale]);
  return (
    <KitScope>
      <JsonLd
        data={{
          "@context": "https://schema.org",
          "@graph": [
            { "@type": "Organization", name: "Handball Intelligence", url: SITE_URL, email: SUPPORT_EMAIL },
            {
              "@type": "SoftwareApplication",
              name: "Handball Intelligence",
              applicationCategory: "SportsApplication",
              operatingSystem: "Web",
              description: m.meta.description,
            },
          ],
        }}
      />
      <WurfHead
        kick={m.match.fictional}
        title={t.title}
        lead={t.lead}
        own={v.final.own}
        opp={v.final.opp}
        ownName={v.own}
        oppName={v.opp}
        scoreLabel={fmt(m.match.resultLabel, { own: v.own, opp: v.opp, a: v.final.own, b: v.final.opp })}
        goals={v.report}
        flightLabels={{ half: m.match.flightHalf, end: m.match.flightEnd }}
      />

      <div className="wrap">
        <div className="mt-8 grid grid-cols-1 gap-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,36rem)] lg:items-start">
          <div>
            <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap">
              <a href={start} className="btn btn-ink">
                {m.cta.start}
              </a>
              <DemoLink href={`/${locale}/demo/`} className="btn btn-line">
                {m.cta.demo}
              </DemoLink>
            </div>
            <p className="mt-3 text-[1.0625rem] text-ink-2">{m.cta.trial}</p>
          </div>
          <ShirtPicker question={m.kit.question} hint={m.kit.hint} names={m.kit.names} />
        </div>

        <section aria-labelledby="things" className="mt-20">
          <SectionHead id="things" title={m.things.title} note={m.things.side} />
          <Things things={v.things} legend={{ solid: m.things.legendSolid, dashed: m.things.legendDashed, thin: m.things.legendThin }} />
        </section>

        <section aria-labelledby="more" className="mt-20">
          <SectionHead id="more" title={t.moreTitle} />
          <div className="mt-8 grid grid-cols-1 gap-10 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
            <DemoCamera
              scene={v.scene}
              text={{ label: m.camera.label, pause: m.camera.pause, play: m.camera.play, notFound: m.camera.notFound, noBall: m.camera.noBall, caption: v.scene.label }}
              legend={{ own: v.own, opp: v.opp, ref: m.camera.legendRef, number: m.camera.legendNumber, ball: m.camera.legendBall }}
            />
            <ul className="border-t-2 border-ink">
              {t.more.map((x) => (
                <li key={x.title} className="border-b border-rule py-5">
                  <h3 className="font-slant text-[1.5rem]">{x.title}</h3>
                  <p className="mt-1">{x.text}</p>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section aria-labelledby="steps" className="mt-20">
          <SectionHead id="steps" title={t.stepsTitle} />
          <ol className="mt-2 grid grid-cols-1 md:grid-cols-3">
            {t.steps.map((s, i) => (
              <li key={s.title} className="flex gap-5 border-b border-rule py-6 md:block md:border-b-0 md:px-6 md:first:pl-0 md:[&+li]:border-l md:[&+li]:border-l-rule">
                <span aria-hidden className="font-num block text-[4.5rem] leading-[.85] text-club-text md:text-[6rem]">
                  {i + 1}
                </span>
                <div>
                  <h3 className="font-slant text-[1.625rem] md:mt-3">{s.title}</h3>
                  <p className="mt-1">{s.text}</p>
                </div>
              </li>
            ))}
          </ol>
          <div className="mt-4 flex flex-wrap gap-x-8">
            <Link href={`/${locale}/aufnahme/`} className="link">
              {m.cta.filming}
            </Link>
            <Link href={`/${locale}/so-funktioniert-es/`} className="link">
              {m.cta.how}
            </Link>
          </div>
        </section>

        <section aria-labelledby="honest" className="mt-20">
          <SectionHead id="honest" title={m.honest.title} />
          <div className="mt-8">
            <Honest t={m.honest} short />
          </div>
          <Link href={`/${locale}/so-funktioniert-es/#kann`} className="link mt-2">
            {m.cta.honest}
          </Link>
        </section>

        <section aria-labelledby="board" className="mt-20">
          <SectionHead id="board" title={t.boardTitle} />
          <ul className="mt-2 grid grid-cols-1 md:grid-cols-3">
            {t.board.map((b, i) => (
              <li key={b.title} className="border-b border-rule py-6 md:border-b-0 md:px-6 md:first:pl-0 md:[&+li]:border-l md:[&+li]:border-l-rule">
                <h3 className="font-slant text-[1.5rem]">{b.title}</h3>
                <p className="mt-1">{fmt(b.text, { price: team.price_chf_month })}</p>
                <Link href={`/${locale}/${["preise", "daten", "daten"][i]}/`} className="link mt-1">
                  {[m.cta.pricing, m.cta.data, m.cta.data][i]}
                </Link>
              </li>
            ))}
          </ul>
        </section>

        <section aria-labelledby="final" className="mt-20 border-t-2 border-ink pt-10">
          <h2 id="final" className="text-[2.25rem] md:text-[3.25rem]">
            {t.finalTitle}
          </h2>
          <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:flex-wrap">
            <a href={start} className="btn btn-ink">
              {m.cta.start}
            </a>
            <DemoLink href={`/${locale}/demo/`} className="btn btn-line">
              {m.cta.demo}
            </DemoLink>
          </div>
          <p className="mt-3 text-[1.0625rem] text-ink-2">{m.cta.trial}</p>
        </section>
      </div>
    </KitScope>
  );
}
