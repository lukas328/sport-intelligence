import type { Metadata } from "next";
import type { CSSProperties } from "react";
import Link from "next/link";
import plans from "@handball/plans";
import { AskCard } from "@/components/ask-card";
import { HeroFilm } from "@/components/hero-film";
import { ProductShot } from "@/components/product-shot";
import { appShot, SHOT_SIZES } from "@/lib/product-shots";
import { JsonLd } from "@/components/json-ld";
import { DemoLink, KitScope, StartLink } from "@/components/kit";
import { Reveal } from "@/components/reveal";
import { Evening, When } from "@/components/story";
import { PhoneChat } from "@/components/phone-chat";
import { TeamField } from "@/components/team-field";
import { Things } from "@/components/things";
import { APP_LOCALE, fmt, messages, type Locale } from "@/lib/i18n";
import { pageMeta } from "@/lib/seo";
import { graph, organization, softwareApplication, webPage, website } from "@/lib/schema";
import { SITE_UPDATED } from "@/lib/site";
import { saturday, sundayAnswer, threeMatchesLater } from "@/lib/story";
import { SeasonBars } from "@/components/week/season-bars";
import { demoView } from "@/lib/things";
import { DRILL_LANG, DRILLS } from "@/lib/drills";
import { seasonRightWing } from "@/lib/week";
import { LoopTile } from "@/components/week/loop-tile";
import { HallPhoto } from "@/components/hall-photo";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  return pageMeta(locale, "", undefined, messages(locale).meta.description);
}

/**
 * The start page as one week of an invented team (BEFUNDE-2 W5, W22; BEFUNDE-3 U6, U18): not a
 * video platform but what to change in training, as one thread: a pattern found, a question to
 * the assistant, a training tip and the scenes for the team, checked three matches later. The
 * promise with the three things turning in a card; Saturday 7 pm, lost with only a feeling and a video (BEFUNDE-4 U39: a sticker says the video is enough and leads to «So funktioniert es»);
 * Saturday 10 pm, the three things and the real app on a computer; Sunday, the question to the
 * assistant, then what it means for training (BEFUNDE-4 U30: pattern, why, drill, effect, the loop
 * of the demo week); Tuesday, the training tip and four scenes in the
 * team chat; three matches later the right wing is closed, as a green block across the page.
 * Then the video in the club, the price and the team field. About 600 words (U18); the tactics
 * camera lives on the demo page, the step pictures on «So funktioniert es». The match is the demo
 * match, so its numbers are the demo's, and the page says once, in the hero, that it is invented
 * (U25). The colours are the website's own (cream, green, ink); the demo club plays in that green.
 */
export default async function Home({ params }: Props) {
  const { locale } = await params;
  const m = messages(locale);
  const t = m.home;
  const v = demoView(m);
  const sat = saturday();
  const later = threeMatchesLater();
  const season = seasonRightWing();
  const d = m.demo;
  const answer = sundayAnswer();
  const team = plans.plans.find((p) => p.plan === "team")!;
  const app = APP_LOCALE[locale];
  // on the start page each thing leads to its scenes in the demo; the halves stand in the hero (U18)
  const things = v.things.map((x) => ({
    ...x,
    sub: "",
    scenesLabel: fmt(m.things.scenesLink, { n: x.goals.length }),
  }));
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
      <Reveal />

      {/* 1 · the promise, the way in, and the three things of the demo match turning in a card (S3) */}
      <section
        aria-labelledby="hero"
        className="on-club relative overflow-hidden bg-club text-club-ink shadow-[inset_0_0_0_2px_var(--club-edge)] [clip-path:polygon(0_0,100%_0,100%_97%,0_100%)] md:[clip-path:polygon(0_0,100%_0,100%_calc(100%-4rem),0_100%)]"
      >
        {/* a hall in the background, grey and soft in the club colour, rising from below (U48) */}
        <img
          src="/media/halle-kopf-1000.webp"
          srcSet="/media/halle-kopf-1000.webp 1000w, /media/halle-kopf-1600.webp 1600w"
          sizes="100vw"
          alt=""
          aria-hidden
          width={1600}
          height={690}
          decoding="async"
          fetchPriority="low"
          className="pointer-events-none absolute inset-x-0 bottom-0 h-[70%] w-full object-cover object-bottom opacity-40 mix-blend-soft-light md:opacity-60 [mask-image:linear-gradient(to_bottom,transparent,#000_70%)] print:hidden"
        />
        {/* on the phone: headline, film, then the lead and the way in (U22); from lg the film
            stands on the right across both rows */}
        <div className="wrap relative grid grid-cols-1 gap-x-14 pt-8 pb-16 md:pt-14 lg:grid-cols-[minmax(0,1.05fr)_minmax(0,1fr)] lg:grid-rows-[auto_1fr] lg:pb-28">
          <div className="min-w-0 lg:col-start-1 lg:row-start-1">
            <p className="text-base font-semibold md:text-[1.0625rem]">{t.kick}</p>
            <h1
              id="hero"
              className="mt-3 text-[2.75rem] leading-[.95] md:text-[4.5rem] lg:text-[3.875rem] xl:text-[4.5rem]"
            >
              {t.title}
            </h1>
          </div>
          <div className="mt-8 min-w-0 lg:col-start-2 lg:row-span-2 lg:row-start-1 lg:mt-0 lg:self-center lg:pl-4">
            <div className="mx-auto max-w-[32.5rem] lg:mr-0">
              <HeroFilm
                things={v.things}
                court={sat}
                text={{
                  ...t.film,
                  label: fmt(t.film.label, { n: sat.n, of: sat.of }),
                  count: fmt(t.film.count, { n: sat.n, of: sat.of }),
                  score: `${v.own} ${sat.score} ${v.opp}`,
                  note: t.example,
                }}
              />
            </div>
          </div>
          <div className="mt-8 min-w-0 lg:col-start-1 lg:row-start-2 lg:mt-0">
            <p className="max-w-[34rem] text-[1.1875rem] leading-normal font-medium md:mt-6 md:text-[1.375rem]">
              {t.lead}
            </p>
            {/* one main action, the team search; one second, the demo match (U16) */}
            <div className="mt-8">
              <TeamField
                id="team"
                label={t.teamLabel}
                button={t.teamButton}
                hint={t.teamHint}
                after={t.teamAfter}
                appLocale={app}
                onClub
              />
            </div>
            <DemoLink href={`/${locale}/demo/`} className="link mt-4 text-[1.0625rem] font-medium text-club-ink">
              {m.cta.demo}
            </DemoLink>
          </div>
        </div>
      </section>

      {/* 2 · Saturday, 7 pm: the problem (W6, W23, W25), the evening after the defeat */}
      <section
        aria-labelledby="problem"
        className="-mt-10 bg-ink pt-10 text-ground md:-mt-16 md:pt-16 print:mt-0 print:bg-transparent print:pt-0 print:text-ink"
      >
        <div className="wrap grid grid-cols-1 items-center gap-10 py-14 md:py-20 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)] lg:gap-16">
          <div data-reveal className="min-w-0">
            <When dark>{t.problemWhen}</When>
            <h2 id="problem" className="mt-4 text-[2.5rem] md:text-[4rem]">
              {t.problemTitle}
            </h2>
            <p className="mt-6 max-w-[36rem] text-[1.1875rem] text-[#dcdfe2] md:text-[1.3125rem] print:text-ink">
              {t.problemText}
            </p>
            <p className="mt-3 max-w-[36rem] text-[1.1875rem] text-[#dcdfe2] md:text-[1.3125rem] print:text-ink">
              {t.problemRest}
            </p>
            <p className="mt-6 text-[1.25rem] font-bold md:text-[1.4375rem]">{t.problemBuild}</p>
          </div>
          <div data-reveal style={{ "--d": 1 } as CSSProperties} className="min-w-0">
            <Evening t={t.problemCard} score={sat.score} how={{ text: m.cta.how, href: `/${locale}/so-funktioniert-es/` }} />
          </div>
        </div>
        {/* the hall after the match: the ball in front of the empty goal, out of the dark (U48) */}
        <HallPhoto
          name="tor-ball"
          sizes="100vw"
          className="h-52 [mask-image:linear-gradient(to_bottom,transparent,#000_45%)] sm:h-64 md:h-[22rem]"
          imgClassName="object-[50%_86%] brightness-[0.78] saturate-[0.8]"
        />
      </section>

      <div className="wrap">
        {/* 3 · Saturday, 10 pm: what you get, the three things (W7) */}
        <section aria-labelledby="get" className="mt-20 md:mt-28">
          <div data-reveal className="max-w-[44rem]">
            <When>{t.getWhen}</When>
            <h2 id="get" className="mt-4 text-[2.25rem] md:text-[3.5rem]">
              {t.getTitle}
            </h2>
            <p className="mt-4 text-[1.1875rem] md:text-[1.3125rem]">
              {fmt(t.getText, { n: sat.n, of: sat.of })}
            </p>
          </div>
          <div data-reveal style={{ "--d": 1 } as CSSProperties} className="mt-6">
            <Things things={things} scenesHref={`/${locale}/demo/`} clean />
          </div>
          {/* the real app on a computer: the match with its video and scenes (S13) */}
          <div data-reveal className="mt-12 md:mt-16">
            <ProductShot
              name={appShot("app-desktop", locale)}
              phone={appShot("video-phone", locale)}
              alt={t.appAlt}
              lettering={t.film.video}
              labels={{}}
              sizes={SHOT_SIZES.column()}
              framed={false}
              caption={t.getMore}
            />
          </div>
        </section>

        {/* 4 · Sunday: ask your matches (U6), the assistant's answer with its source */}
        <section aria-labelledby="ask" className="mt-20 md:mt-28">
          <div className="grid grid-cols-1 items-center gap-10 md:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)] md:gap-14">
            <div data-reveal className="min-w-0">
              <When>{t.askWhen}</When>
              <h2 id="ask" className="mt-4 text-[2.25rem] md:text-[3rem]">
                {t.askTitle}
              </h2>
              <p className="mt-4 text-[1.1875rem]">{t.askText}</p>
            </div>
            <div data-reveal style={{ "--d": 1 } as CSSProperties} className="min-w-0">
              <AskCard
                t={t.ask}
                a={answer}
                team={`${v.own} ${t.chat.group}`}
                opp={v.opp}
                scenesHref={`/${locale}/demo/#things`}
              />
            </div>
          </div>
        </section>

        {/* 4b · what it means for training (U30): the loop pattern, why, drill, effect, as on the demo page */}
        <section aria-labelledby="loop" data-reveal className="mt-20 md:mt-28">
          <LoopTile
            kick={t.loopKick}
            title={t.loopTitle}
            steps={t.loop.map((s) => ({
              title: s.title,
              text: fmt(s.text, { n: sat.n, of: sat.of, drill: DRILLS.defence_6_0_shift.name[DRILL_LANG[locale]] }),
            }))}
            link={t.loopLink}
            demoHref={`/${locale}/demo/`}
            numeral={sat.n}
            unit={String(sat.of)}
            scene={v.scene}
            drill={DRILLS.defence_6_0_shift}
            drillLabel={fmt(m.demo.sketchLabel, { name: DRILLS.defence_6_0_shift.name[DRILL_LANG[locale]] })}
            bars={seasonRightWing().map((s) => s.n)}
          />
        </section>

        {/* 6 · Tuesday: four scenes in the team chat (W26, W28) */}
        <section aria-labelledby="share" className="mt-20 md:mt-28">
          <div className="grid grid-cols-1 items-center gap-10 md:grid-cols-2 md:gap-16">
            <div data-reveal className="min-w-0">
              <When>{t.shareWhen}</When>
              <h2 id="share" className="mt-4 text-[2.25rem] md:text-[3rem]">
                {t.shareTitle}
              </h2>
              <p className="mt-4 text-[1.1875rem]">{fmt(t.shareText, { fast: answer.fast })}</p>
              <ul className="mt-6 border-t-2 border-ink">
                {t.sharePoints.map((x) => (
                  <li key={x} className="flex gap-3 border-b border-rule py-3 font-semibold">
                    <Tick />
                    {x}
                  </li>
                ))}
              </ul>
            </div>
            <div data-reveal style={{ "--d": 1 } as CSSProperties} className="min-w-0">
              <PhoneChat t={t.chat} locale={locale} />
            </div>
          </div>
        </section>
      </div>

      {/* 7 · three matches later: the right wing is closed (W27), the high point of the week as a
          green block across the page, the numbers counting up (S12, S14) */}
      <section
        aria-labelledby="after"
        className="on-club mt-20 bg-club text-club-ink [clip-path:polygon(0_2rem,100%_0,100%_calc(100%-2rem),0_100%)] md:mt-28 md:[clip-path:polygon(0_4rem,100%_0,100%_calc(100%-4rem),0_100%)]"
      >
        <div className="wrap pt-20 pb-20 md:pt-32 md:pb-32">
          <div data-reveal className="max-w-[48rem]">
            <When onClub>{t.afterWhen}</When>
            <h2 id="after" className="mt-4 text-[2.75rem] md:text-[5rem]">
              {t.afterTitle}
            </h2>
            <p className="mt-5 text-[1.1875rem] md:text-[1.375rem]">
              {fmt(t.afterText, {
                before: sat.n,
                beforeOf: sat.of,
                after: later.n,
                afterOf: later.of,
              })}
            </p>
          </div>
          {/* the same season bars as the demo match (U46): one bar per match, tap one for its goals */}
          <div data-reveal style={{ "--d": 1 } as CSSProperties} className="mt-12 md:mt-16">
            <SeasonBars
              matches={season}
              text={{
                label: d.nextLabel,
                of: season.map((x) => fmt(d.nextOf, { n: x.n, of: x.of })),
                bars: season.map((x) => fmt(d.nextBar, { opp: x.opp, n: x.n, of: x.of })),
                courts: season.map((x) => fmt(d.nextCourt, { opp: x.opp, n: x.n, of: x.of })),
                demo: d.nextDemo,
                example: d.nextTag,
              }}
            />
            <p className="mt-6 inline-block border-2 border-dashed border-club-ink px-3 py-1 text-[1.0625rem] font-semibold">{d.nextExample}</p>
          </div>
        </div>
      </section>

      <div className="wrap">
        {/* 8 · the video stays in the club */}
        <section aria-labelledby="trust" className="mt-16 md:mt-24">
          <h2 id="trust" data-reveal className="text-[2.25rem] md:text-[3rem]">
            {t.trustTitle}
          </h2>
          <ul className="mt-8 grid grid-cols-1 gap-8 md:grid-cols-3">
            {t.trust.map((x, i) => (
              <li
                key={x.title}
                data-reveal
                style={{ "--d": i } as CSSProperties}
                className="border-t-2 border-ink pt-5"
              >
                <h3 className="text-[1.375rem] leading-tight">{x.title}</h3>
                <p className="mt-2">{x.text}</p>
              </li>
            ))}
          </ul>
          <div className="mt-8 flex flex-wrap gap-x-8">
            <Link href={`/${locale}/daten/`} className="link">
              {m.cta.data}
            </Link>
            <Link href={`/${locale}/ueber-uns/`} className="link">
              {t.trustLink}
            </Link>
          </div>
        </section>

        {/* 9 · price (W4, W11) */}
        <section aria-labelledby="price" className="mt-20 md:mt-28">
          <div
            data-reveal
            className="grid grid-cols-1 items-center gap-6 border-2 border-ink bg-paper p-6 md:grid-cols-[auto_minmax(0,1fr)_auto] md:gap-10 md:p-10"
          >
            {/* the days with their words under them, centred on the title like the buttons (U27) */}
            <p className="flex items-baseline gap-3 md:flex-col md:items-start md:gap-2">
              <b className="font-num text-[5rem] leading-[.8] text-club-text md:text-[7rem]">
                {team.trial_days}
              </b>
              <span className="text-[1.0625rem] font-semibold text-ink-2">{t.priceUnit}</span>
            </p>
            <div>
              <h2 id="price" className="text-[2rem] md:text-[2.5rem]">
                {fmt(t.priceTitle, { price: team.price_chf_month })}
              </h2>
              <p className="mt-2">
                {fmt(t.priceText, { days: team.trial_days, price: team.price_chf_month })}
              </p>
            </div>
            <div className="flex flex-col gap-2">
              <StartLink appLocale={app} className="btn btn-ink">
                {m.cta.start}
              </StartLink>
              <Link href={`/${locale}/preise/`} className="link justify-center">
                {m.cta.pricing}
              </Link>
            </div>
          </div>
        </section>

        {/* 10 · start */}
        <section
          aria-labelledby="final"
          className="mt-20 grid grid-cols-1 items-center gap-8 border-t-2 border-ink pt-10 md:mt-28 lg:grid-cols-[minmax(0,1.25fr)_minmax(0,1fr)] lg:gap-12"
        >
          <div className="min-w-0">
            <h2 id="final" className="text-[2.5rem] md:text-[3.75rem]">
              {t.finalTitle}
            </h2>
            {/* as in the head: the team search, the demo as a text link under it */}
            <div className="mt-8">
              <TeamField
                id="team-end"
                label={t.teamLabel}
                button={t.teamButton}
                hint={t.teamHint}
                appLocale={app}
              />
              <DemoLink href={`/${locale}/demo/`} className="link mt-4">
                {m.cta.demo}
              </DemoLink>
            </div>
          </div>
          {/* the next match, in the visitor's shirt colour (U48) */}
          <HallPhoto
            name="sprungwurf"
            tint
            sizes="(min-width: 1024px) 34rem, 100vw"
            className="aspect-[13/11] border-2 border-ink max-lg:-order-1 max-lg:aspect-[16/10]"
            imgClassName="object-top"
          />
        </section>
      </div>
    </KitScope>
  );
}

function Tick() {
  return (
    <svg viewBox="0 0 20 20" aria-hidden className="mt-1 size-5 shrink-0 text-club-text">
      <path
        d="M3 10.5 8 15 17 5"
        fill="none"
        stroke="currentColor"
        strokeWidth={3}
        strokeLinecap="square"
      />
    </svg>
  );
}
