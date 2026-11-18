import type { Metadata } from "next";
import Link from "next/link";
import { Rail } from "@/components/anlauf/charts";
import { CameraLegend, DemoCamera } from "@/components/demo-camera";
import { DemoGuide } from "@/components/demo-guide";
import { KitScope, ShirtPicker, StartLink } from "@/components/kit";
import { Things } from "@/components/things";
import { SectionHead, WurfHead } from "@/components/wurf-head";
import { demoFigures } from "@/lib/demo";
import { APP_LOCALE, fmt, messages, type Locale } from "@/lib/i18n";
import { pageMeta } from "@/lib/seo";
import { demoView, MATCH } from "@/lib/things";

type Props = { params: Promise<{ locale: Locale }> };

/** Where the four pictures of «Was du hier siehst» lead. */
const GUIDE_IDS = ["things", "scene", "flow", "zahlen"];

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  return pageMeta(
    locale,
    "demo",
    messages(locale).seo.demo.title,
    messages(locale).seo.demo.description,
  );
}

/**
 * The demo match: invented and marked so at the top (never hidden), drawn with the app's
 * building blocks. Four small pictures say what is on the page and jump there (K11, L6). No account, no video; one scene
 * on the tactics camera, with the ball (invented) and handball-typical positions.
 */
export default async function Demo({ params }: Props) {
  const { locale } = await params;
  const m = messages(locale);
  const t = m.demo;
  const v = demoView(m);
  const figures = demoFigures(MATCH);
  // goals conceded by position, most first; the zone of the first thing is drawn strong
  const opp = v.goals.filter((g) => g.team === "opp");
  const conceded = opp.length;
  const first = v.things.find((x) => x.team === "opp")?.goals[0]?.zone;
  const zones = (Object.keys(t.zoneNames) as (keyof typeof t.zoneNames)[])
    .map((key) => ({
      key,
      label: t.zoneNames[key],
      n: opp.filter((g) => g.zone === key).length,
      strong: key === first,
    }))
    .filter((z) => z.n > 0)
    .sort((a, b) => b.n - a.n);
  // the score at half-time, from the match report
  const halfScore = MATCH.stats.timeline.score.filter((x) => x.clock_s <= 1800).at(-1);
  const half = `${halfScore?.own ?? 0}:${halfScore?.opp ?? 0}`;
  return (
    <KitScope>
      <p
        role="note"
        className="border-b-2 border-ink bg-attn px-4 py-4 text-[1.0625rem] text-ink md:px-8"
      >
        <span className="wrap block !px-0">
          <b>{t.banner}</b> {t.bannerText}
        </span>
      </p>
      <WurfHead
        kick={m.match.when}
        title={m.match.lost}
        own={v.final.own}
        opp={v.final.opp}
        ownName={v.own}
        oppName={v.opp}
        scoreLabel={fmt(m.match.resultLabel, {
          own: v.own,
          opp: v.opp,
          a: v.final.own,
          b: v.final.opp,
        })}
        goals={v.report}
        flightLabels={{ half: m.match.flightHalf, end: m.match.flightEnd }}
      />
      <div className="wrap">
        {/* what is on this page, as four small pictures that jump there (L6) */}
        <DemoGuide
          title={t.guideTitle}
          lead={t.guideLead}
          tiles={t.guide.map((g, i) => ({ ...g, id: GUIDE_IDS[i]! }))}
          thing={v.things[0]!}
          scene={v.scene}
          report={v.report}
          zones={zones}
          score={`${v.final.own}:${v.final.opp}`}
        />
        <p className="mt-6 text-base text-ink-2">{t.sources}</p>

        <section aria-labelledby="things" className="mt-14">
          <SectionHead id="things" title={m.things.side} />
          <p className="measure mt-3 text-[1.0625rem] text-ink-2">{t.thingsNote}</p>
          <Things
            things={v.things}
            legend={{ solid: m.things.legendSolid, thin: m.things.legendThin }}
            selectable
            pickHint={t.pick}
            scenesOf={t.scenesOf}
            timesOf={t.timesOf}
            noVideo={t.noVideo}
          />
          <div className="mt-10 max-w-[44rem]">
            <ShirtPicker question={m.kit.question} hint={m.kit.hint} names={m.kit.names} />
          </div>
        </section>

        <section aria-labelledby="scene" className="mt-16">
          <SectionHead id="scene" title={m.camera.title} note={v.sceneGoal.clock} />
          {/* U24: the half where the scene plays, goal at the top as everywhere on the site, labelled;
              on a wide screen the text and the legend beside it */}
          <div className="mt-6 grid grid-cols-1 gap-x-12 gap-y-6 lg:grid-cols-[minmax(0,46rem)_minmax(0,1fr)]">
            <div className="lg:col-start-2 lg:row-start-1">
              <p className="measure">{t.cameraText}</p>
              <div className="mt-6">
                <CameraLegend
                  list
                  legend={{
                    own: v.own,
                    opp: v.opp,
                    ref: m.camera.legendRef,
                    number: m.camera.legendNumber,
                    ball: m.camera.legendBall,
                  }}
                />
              </div>
            </div>
            <div className="lg:col-start-1 lg:row-start-1">
              <DemoCamera
                scene={v.scene}
                view="halfB"
                desktopWidth={736}
                shotLabel={false}
                text={{
                  label: `${m.camera.label} ${m.camera.half}.`,
                  pause: m.camera.pause,
                  play: m.camera.play,
                  notFound: m.camera.notFound,
                  noBall: m.camera.noBall,
                  caption: v.scene.label,
                  captionSmall: m.camera.half,
                  ballLine: m.camera.ballLine,
                }}
              />
            </div>
          </div>
        </section>

        {/* the match in figures (L7): one head, the run of the match across, figures and positions
            side by side below it, both as rows on the same rhythm */}
        <section aria-labelledby="stats" className="mt-20">
          <SectionHead id="stats" title={t.statsTitle} />
          <div id="flow" className="mt-8 scroll-mt-4">
            <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-2">
              <h3 className="text-[1.375rem] md:text-[1.5rem]">{t.flowTitle}</h3>
              <p className="flex flex-wrap gap-x-5 gap-y-1 text-base font-semibold" aria-hidden>
                <span className="inline-flex items-center gap-2">
                  <i className="inline-block h-4 w-2 bg-[var(--club-line)]" />
                  {v.own} {v.final.own}
                </span>
                <span className="inline-flex items-center gap-2">
                  <i className="inline-block h-4 w-2 bg-[var(--opp-line)]" />
                  {v.opp} {v.final.opp}
                </span>
              </p>
            </div>
            <div className="mt-4 border-y border-rule py-3">
              <Rail goals={v.report} label={fmt(t.flowLabel, { own: v.own, opp: v.opp })} />
            </div>
            <p className="mt-2 grid grid-cols-3 text-base text-ink-2" aria-hidden>
              <span>{t.flowStart}</span>
              <span className="text-center">{fmt(t.flowHalf, { score: half })}</span>
              <span className="text-right">
                {fmt(t.flowEnd, { score: `${v.final.own}:${v.final.opp}` })}
              </span>
            </p>
          </div>

          <div
            id="zahlen"
            className="mt-14 grid scroll-mt-4 grid-cols-1 gap-x-16 gap-y-14 lg:grid-cols-2"
          >
            <div>
              <h3 id="figures" className="text-[1.375rem] md:text-[1.5rem]">
                {t.figuresTitle}
              </h3>
              <table className="sheet mt-3">
                <thead>
                  <tr>
                    <th scope="col">
                      <span className="sr-only">{t.figuresTitle}</span>
                    </th>
                    <th scope="col">{v.own}</th>
                    <th scope="col">{v.opp}</th>
                    <th scope="col" className="hidden text-left sm:table-cell">
                      {t.figuresSource}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {figures.map((f) => (
                    <tr key={f.key}>
                      <th scope="row" className="font-semibold">
                        {t.figures[f.key]}
                        <span className="block text-base font-normal text-ink-2 sm:hidden">
                          {t.source[f.source]}
                        </span>
                      </th>
                      <td className="font-num text-[1.5rem]">
                        {f.key === "shootingPct" && f.own != null
                          ? fmt(t.pct, { v: f.own })
                          : f.own}
                      </td>
                      <td className="font-num text-[1.5rem]">
                        {f.key === "shootingPct" && f.opp != null
                          ? fmt(t.pct, { v: f.opp })
                          : f.opp}
                      </td>
                      <td className="hidden !pl-4 text-left text-base text-ink-2 sm:table-cell">
                        {t.source[f.source]}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div>
              <div className="flex flex-wrap items-baseline justify-between gap-x-6">
                <h3 id="zones" className="text-[1.375rem] md:text-[1.5rem]">
                  {t.zonesTitle}
                </h3>
                <p className="text-base font-semibold text-ink-2">
                  {fmt(t.zonesTotal, { n: conceded })}
                </p>
              </div>
              {/* one row per position, the same rhythm as the figures; the biggest is thing 1 */}
              <ul
                className="mt-3 border-t-2 border-ink"
                aria-label={fmt(t.zonesLabel, { opp: v.opp })}
              >
                {zones.map((z) => (
                  <li
                    key={z.key}
                    className="grid min-h-[3.25rem] grid-cols-[minmax(0,9.5rem)_minmax(0,1fr)_2.5rem] items-center gap-x-4 border-b border-rule"
                  >
                    <span className={z.strong ? "font-semibold" : undefined}>{z.label}</span>
                    <span aria-hidden className="block h-4">
                      <i
                        className={z.strong ? "block h-full bg-ink" : "block h-full bg-ink/25"}
                        style={{ width: `${(z.n / zones[0]!.n) * 100}%` }}
                      />
                    </span>
                    <span className="font-num text-right text-[1.5rem]">{z.n}</span>
                  </li>
                ))}
              </ul>
              <p className="mt-3 text-base text-ink-2">{t.zonesNote}</p>
            </div>
          </div>
        </section>

        <section aria-labelledby="end" className="mt-20 border-t-2 border-ink pt-10">
          <h2 id="end" className="text-[2.25rem] md:text-[3.25rem]">
            {t.endTitle}
          </h2>
          <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:flex-wrap">
            <StartLink appLocale={APP_LOCALE[locale]} className="btn btn-ink">
              {m.cta.start}
            </StartLink>
            <Link href={`/${locale}/so-funktioniert-es/`} className="btn btn-line">
              {m.cta.how}
            </Link>
          </div>
          <p className="mt-3 text-[1.0625rem] text-ink-2">{m.cta.trial}</p>
        </section>
      </div>
    </KitScope>
  );
}
