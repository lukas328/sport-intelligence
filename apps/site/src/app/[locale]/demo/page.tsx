import type { Metadata } from "next";
import Link from "next/link";
import { Zones } from "@/components/anlauf/bundle";
import { Rail } from "@/components/anlauf/charts";
import { DemoCamera } from "@/components/demo-camera";
import { KitScope, ShirtPicker } from "@/components/kit";
import { Things } from "@/components/things";
import { SectionHead, WurfHead } from "@/components/wurf-head";
import { demoFigures } from "@/lib/demo";
import { APP_LOCALE, fmt, messages, type Locale } from "@/lib/i18n";
import { pageMeta } from "@/lib/seo";
import { startUrl } from "@/lib/site";
import { demoView, MATCH } from "@/lib/things";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = messages(locale).demo;
  return pageMeta(locale, "demo", t.title, `${t.banner} ${t.bannerText}`);
}

/**
 * The demo match: invented and marked so at the top (never hidden), drawn with the app's
 * building blocks. No account, no video; one scene on the tactics camera, without a ball.
 */
export default async function Demo({ params }: Props) {
  const { locale } = await params;
  const m = messages(locale);
  const t = m.demo;
  const v = demoView(m);
  const figures = demoFigures(MATCH);
  const opp = v.goals.filter((g) => g.team === "opp" && g.zone !== "m7" && g.zone !== "gs");
  return (
    <KitScope>
      <p role="note" className="border-b-2 border-ink bg-attn px-4 py-4 text-[1.0625rem] text-ink md:px-8">
        <span className="wrap block !px-0">
          <b>{t.banner}</b> {t.bannerText}
        </span>
      </p>
      <WurfHead
        kick={m.match.when}
        title={m.match.won}
        own={v.final.own}
        opp={v.final.opp}
        ownName={v.own}
        oppName={v.opp}
        scoreLabel={fmt(m.match.resultLabel, { own: v.own, opp: v.opp, a: v.final.own, b: v.final.opp })}
        goals={v.report}
        flightLabels={{ half: m.match.flightHalf, end: m.match.flightEnd }}
      />
      <div className="wrap">
        <p className="mt-6 text-[1.0625rem] text-ink-2">{t.sources}</p>
        <div className="mt-8 max-w-[44rem]">
          <ShirtPicker question={m.kit.question} hint={m.kit.hint} names={m.kit.names} />
        </div>

        <section aria-labelledby="things" className="mt-16">
          <SectionHead id="things" title={m.things.side} />
          <Things
            things={v.things}
            legend={{ solid: m.things.legendSolid, dashed: m.things.legendDashed, thin: m.things.legendThin }}
            selectable
            pickHint={t.pick}
            scenesOf={t.scenesOf}
            timesOf={t.timesOf}
            estimated={t.estimated}
            noVideo={t.noVideo}
          />
        </section>

        <section aria-labelledby="scene" className="mt-16">
          <SectionHead id="scene" title={m.camera.title} note={v.sceneGoal.clock} />
          <div className="mt-6">
            <DemoCamera
              scene={v.scene}
              text={{ label: m.camera.label, pause: m.camera.pause, play: m.camera.play, notFound: m.camera.notFound, noBall: m.camera.noBall, caption: v.scene.label }}
              legend={{ own: v.own, opp: v.opp, ref: m.camera.legendRef, number: m.camera.legendNumber, ball: m.camera.legendBall }}
            />
          </div>
        </section>

        <section aria-labelledby="flow" className="mt-16">
          <SectionHead id="flow" title={t.flowTitle} />
          <div className="mt-6">
            <Rail goals={v.report} label={fmt(t.flowLabel, { own: v.own, opp: v.opp })} />
            <p className="mt-2 flex justify-between text-base text-ink-2" aria-hidden>
              <span>0</span>
              <span>30</span>
              <span>60</span>
            </p>
          </div>
        </section>

        <div className="mt-16 grid grid-cols-1 gap-16 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]">
          <section aria-labelledby="figures">
            <SectionHead id="figures" title={t.figuresTitle} />
            <div>
              <table className="sheet mt-2">
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
                        <span className="block text-base font-normal text-ink-2 sm:hidden">{t.source[f.source]}</span>
                      </th>
                      <td className="font-num text-[1.5rem]">{f.key === "shootingPct" && f.own != null ? fmt(t.pct, { v: f.own }) : f.own}</td>
                      <td className="font-num text-[1.5rem]">{f.key === "shootingPct" && f.opp != null ? fmt(t.pct, { v: f.opp }) : f.opp}</td>
                      <td className="hidden !pl-4 text-left text-base text-ink-2 sm:table-cell">{t.source[f.source]}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
          <section aria-labelledby="zones">
            <SectionHead id="zones" title={t.zonesTitle} />
            <div className="mx-auto mt-6 max-w-[26rem]">
              <Zones goals={opp} team="opp" width={400} label={fmt(t.zonesLabel, { opp: v.opp })} zoneNames={m.things.zoneShort} />
            </div>
            <p className="mt-3 text-base text-ink-2">{t.zonesNote}</p>
          </section>
        </div>

        <section aria-labelledby="end" className="mt-20 border-t-2 border-ink pt-10">
          <h2 id="end" className="text-[2.25rem] md:text-[3.25rem]">
            {t.endTitle}
          </h2>
          <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:flex-wrap">
            <a href={startUrl(APP_LOCALE[locale])} className="btn btn-ink">
              {m.cta.start}
            </a>
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
