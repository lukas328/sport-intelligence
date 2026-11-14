import type { Metadata } from "next";
import Link from "next/link";
import plans from "@handball/plans";
import { DemoCamera } from "@/components/demo-camera";
import { Honest } from "@/components/honest";
import { JsonLd } from "@/components/json-ld";
import { DemoLink, KitScope, ShirtPicker } from "@/components/kit";
import { TeamField } from "@/components/team-field";
import { Things } from "@/components/things";
import { SectionHead, WurfHead } from "@/components/wurf-head";
import { APP_LOCALE, fmt, messages, type Locale } from "@/lib/i18n";
import { pageMeta } from "@/lib/seo";
import { graph, organization, softwareApplication, webPage, website } from "@/lib/schema";
import { SITE_UPDATED } from "@/lib/site";
import { demoView } from "@/lib/things";
import { GUIDES } from "../../../content/ratgeber";

/** The three guides that exist in every language, shown on the start page. */
const FEATURED = ["handballspiel-filmen", "videoanalyse-amateurteam", "video-im-verein-einwilligung"];
/** «Für wen»: the guide for each case, in a guide that exists in that language. */
const FOR_WHO: Record<Locale, string[]> = {
  de: ["szenen-im-training-zeigen", "spiel-auswerten-20-minuten", "video-im-verein-einwilligung"],
  fr: ["szenen-im-training-zeigen", "spiel-auswerten-20-minuten", "video-im-verein-einwilligung"],
  en: ["videoanalyse-amateurteam", "handballspiel-filmen", "video-im-verein-einwilligung"],
};

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
  return (
    <KitScope>
      <JsonLd
        data={graph(
          organization(),
          website(locale),
          softwareApplication(locale, m.meta.description, m.pricing.plans),
          webPage(locale, "", m.meta.title, m.meta.description, SITE_UPDATED),
        )}
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
      >
        <TeamField id="team-top" label={t.teamLabel} button={t.teamButton} example={t.teamExample} appLocale={APP_LOCALE[locale]} onClub />
      </WurfHead>

      <div className="wrap">
        <div className="mt-8 grid grid-cols-1 gap-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,36rem)] lg:items-start">
          <div>
            <DemoLink href={`/${locale}/demo/`} className="btn btn-line">
              {m.cta.demo}
            </DemoLink>
            <p className="mt-3 text-[1.0625rem] text-ink-2">{m.cta.trial}</p>
          </div>
          <ShirtPicker question={m.kit.question} hint={m.kit.hint} names={m.kit.names} />
        </div>

        <section aria-labelledby="things" className="mt-20">
          <SectionHead id="things" title={m.things.title} note={m.things.side} />
          <Things things={v.things} legend={{ solid: m.things.legendSolid, dashed: m.things.legendDashed, thin: m.things.legendThin }} scenesHref={`/${locale}/demo/`} />
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

        <section aria-labelledby="forwho" className="mt-20">
          <SectionHead id="forwho" title={t.forWhoTitle} />
          <ul className="mt-2 grid grid-cols-1 md:grid-cols-3">
            {t.forWho.map((c, i) => (
              <li key={c.title} className="border-b border-rule py-6 md:border-b-0 md:px-6 md:first:pl-0 md:[&+li]:border-l md:[&+li]:border-l-rule">
                <h3 className="font-slant text-[1.5rem]">{c.title}</h3>
                <p className="mt-1">{c.text}</p>
                <Link href={`/${locale}/ratgeber/${FOR_WHO[locale][i]}/`} className="link mt-1">
                  {c.link}
                </Link>
              </li>
            ))}
          </ul>
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
                <Link href={`/${locale}/${["preise", "daten", "hilfe/einwilligungen"][i]}/`} className="link mt-1">
                  {[m.cta.pricing, m.cta.data, m.cta.consent][i]}
                </Link>
              </li>
            ))}
          </ul>
        </section>

        <section aria-labelledby="guides" className="mt-20">
          <SectionHead id="guides" title={m.guides.homeTitle} />
          <ul className="mt-2 grid grid-cols-1 md:grid-cols-3">
            {FEATURED.map((slug) => GUIDES.find((g) => g.slug === slug)!).map((g) => (
              <li key={g.slug} className="border-b border-rule py-6 md:border-b-0 md:px-6 md:first:pl-0 md:[&+li]:border-l md:[&+li]:border-l-rule">
                <Link href={`/${locale}/ratgeber/${g.slug}/`} className="font-slant text-[1.5rem] leading-tight hover:underline">
                  {g.title[locale] ?? g.title.de}
                </Link>
              </li>
            ))}
          </ul>
          <Link href={`/${locale}/ratgeber/`} className="link mt-2">
            {m.guides.all}
          </Link>
        </section>

        <section aria-labelledby="who" className="mt-20">
          <SectionHead id="who" title={m.us.homeTitle} />
          <p className="measure mt-4">{m.us.homeText}</p>
          <Link href={`/${locale}/ueber-uns/`} className="link mt-2">
            {m.us.homeLink}
          </Link>
        </section>

        <section aria-labelledby="final" className="mt-20 border-t-2 border-ink pt-10">
          <h2 id="final" className="text-[2.25rem] md:text-[3.25rem]">
            {t.finalTitle}
          </h2>
          <div className="mt-8 grid grid-cols-1 items-end gap-8 md:grid-cols-[minmax(0,34rem)_auto]">
            <TeamField id="team-end" label={t.teamLabel} button={t.teamButton} example={t.teamExample} appLocale={APP_LOCALE[locale]} />
            <DemoLink href={`/${locale}/demo/`} className="btn btn-line md:mb-9">
              {m.cta.demo}
            </DemoLink>
          </div>
          <p className="mt-3 text-[1.0625rem] text-ink-2">{m.cta.trial}</p>
        </section>
      </div>
    </KitScope>
  );
}
