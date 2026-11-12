import type { Metadata } from "next";
import { notFound } from "next/navigation";
import type { CSSProperties } from "react";
import { ActiveMark, AttnTag, CameraKey, LineKey, linkClass, SectionHead } from "@/components/anlauf/blocks";
import { Bundle, EmptyField, Zones } from "@/components/anlauf/bundle";
import { DiffBars, Rail, Series } from "@/components/anlauf/charts";
import { PageHead, Strip, WurfHead } from "@/components/anlauf/heads";
import { TacticsCamera } from "@/components/anlauf/tactics-camera";
import { Button } from "@/components/ui/button";
import { DEMO_GOALS, DEMO_PHASE, DEMO_REPORT, DEMO_RESULT, DEMO_SCENE_KR, DEMO_SCENE_RA, DEMO_SEASON } from "@/lib/anlauf-demo";
import { CHECK_KITS, CHECK_OPPONENT, kit, kitVars } from "@/lib/color";

export const metadata: Metadata = { title: "Anlauf", robots: { index: false } };


const CAMERA_TEXT = {
  pause: "Pause",
  play: "Abspielen",
  notFound: "nicht erkannt",
  noBall: "Ball in dieser Szene nicht erkannt",
};

/**
 * The building blocks of the Anlauf look in the six check colours (SPEC.md section 13, step 1).
 * Development only: shown in production with HB_DEV_PAGES=1. ?club=blau shows one colour,
 * ?opp=unknown an opponent without a known colour.
 */
export default async function AnlaufPage({ searchParams }: { searchParams: Promise<{ club?: string; opp?: string }> }) {
  if (process.env.NODE_ENV === "production" && process.env.HB_DEV_PAGES !== "1") notFound();
  const { club, opp } = await searchParams;
  const names = (Object.keys(CHECK_KITS) as (keyof typeof CHECK_KITS)[]).filter((n) => !club || n === club);
  const against = opp === "unknown" ? null : CHECK_OPPONENT;
  const inPhase = DEMO_REPORT.filter((g) => g.minute >= DEMO_PHASE[0] && g.minute <= DEMO_PHASE[1]);
  const phaseText = `${DEMO_PHASE[0]}. bis ${DEMO_PHASE[1]}. Minute: ${inPhase.filter((g) => g.team === "own").length}:${inPhase.filter((g) => g.team === "opp").length}`;
  return (
    <main className="mx-auto max-w-[1280px] pb-24">
      <div className="px-4 py-6 md:px-8">
        <h1 className="text-[34px]">Anlauf: Bausteine</h1>
        <p className="mt-2 text-[15px] text-ink-2">
          Sechs Vereinsfarben gegen TSV Thalwil (schwarz und weiss){against ? "" : ", Gegner hier ohne bekannte Farbe"}. Alle Daten sind Demo-Daten.
        </p>
        <p className="mt-2 flex flex-wrap gap-3 text-[15px]">
          {Object.keys(CHECK_KITS).map((n) => (
            <a key={n} className={linkClass} href={`?club=${n}${opp ? `&opp=${opp}` : ""}`}>
              {n}
            </a>
          ))}
          <a className={linkClass} href={club ? `?club=${club}&opp=unknown` : "?opp=unknown"}>
            Gegner unbekannt
          </a>
        </p>
      </div>
      {names.map((n) => {
        const k = kit(CHECK_KITS[n], against);
        return (
          <section key={n} data-club={n} style={kitVars(k) as CSSProperties} className="border-t-2 border-ink pt-8 pb-14" aria-label={`Verein ${n}`}>
            <WurfHead
              kick="Samstag gegen TSV Thalwil, Analyse fertig seit Sonntag, 9:40"
              title="Gewonnen. Und drei Dinge zum Mitnehmen."
              own={DEMO_RESULT.own}
              opp={DEMO_RESULT.opp}
              ownName="HC Zürichsee"
              oppName="TSV Thalwil"
              goals={DEMO_REPORT}
              flightLabels={{ half: "Halbzeit {v}", end: "Schluss {v}", halfLevel: "Halbzeit, Gleichstand", endLevel: "Schluss, Gleichstand" }}
            />
            <div className="mt-6 grid gap-8 px-4 md:grid-cols-2 md:px-8">
              <Strip name="HC Zürichsee gegen TSV Thalwil" sub="Samstag, Meisterschaft" own={DEMO_RESULT.own} opp={DEMO_RESULT.opp} />
              <PageHead kick="Herren 1" title="Szenen" figure={142} figureLabel="Szenen aus 3 Spielen" />
            </div>

            <div className="mt-8 grid gap-10 px-4 md:grid-cols-3 md:px-8">
              <div>
                <SectionHead title="Gegentore rechts aussen" note="9 von 18" />
                <Bundle goals={DEMO_GOALS.them.filter((g) => g.zone === "ra")} rest={DEMO_GOALS.them.filter((g) => g.zone !== "ra")} width={360} play label="Anläufe der Gegentore über rechts aussen" />
                <LineKey
                  className="mt-2"
                  items={[
                    { label: "bestätigt", color: "var(--opp-line)" },
                    { label: "geschätzt", estimated: true, color: "var(--opp-line)" },
                  ]}
                />
              </div>
              <div>
                <SectionHead title="Unsere Tore vom Kreis" note="7 von 26" />
                <Bundle goals={DEMO_GOALS.us.filter((g) => g.zone === "kr")} rest={DEMO_GOALS.us.filter((g) => g.zone !== "kr")} width={360} label="Anläufe unserer Tore vom Kreis" />
              </div>
              <div>
                <SectionHead title="Tore nach Position" note="wir" />
                <Zones goals={DEMO_GOALS.us} team="own" label="Unsere Tore nach Position" />
              </div>
            </div>

            <div className="mt-10 grid gap-10 px-4 md:grid-cols-[minmax(0,2fr)_minmax(0,1fr)] md:px-8">
              <div>
                <SectionHead title="Taktikkamera" note="39:49 bis 39:55" action={<AttnTag>Gegentor 39:55</AttnTag>} />
                <TacticsCamera
                  scene={DEMO_SCENE_RA}
                  still={n !== "blau"}
                  text={{ ...CAMERA_TEXT, label: "Taktikkamera: Gegentor über rechts aussen", caption: "Thalwil 5 trifft von rechts aussen", captionSmall: "Positionen aus dem Video" }}
                />
                <CameraKey us="Wir" them="Thalwil" referee="Schiedsrichter" ball="Ball, wo erkannt" />
              </div>
              <div>
                <SectionHead title="Ohne Ball" />
                <TacticsCamera scene={DEMO_SCENE_KR} view="halfB" width={340} dot={16} still text={{ ...CAMERA_TEXT, label: "Taktikkamera: Tor vom Kreis" }} />
              </div>
            </div>

            <div className="mt-10 grid gap-10 px-4 md:grid-cols-3 md:px-8">
              <div className="md:col-span-2">
                <SectionHead title="Spielverlauf" note="Tore aus dem Matchblatt" />
                <Rail goals={DEMO_REPORT} phase={DEMO_PHASE} at={39.9} label="Tore im Spielverlauf" />
                <p className="mt-1 flex justify-between text-[13px] text-ink-2">
                  <span>0:00</span>
                  <span>
                    <AttnTag>{phaseText}</AttnTag>
                  </span>
                  <span>60:00</span>
                </p>
              </div>
              <div>
                <SectionHead title="Leeres Feld" note="noch keine Analyse" />
                <div className="max-w-[200px]">
                  <EmptyField label="Leeres Feld" />
                </div>
              </div>
            </div>

            <div className="mt-10 grid gap-10 px-4 md:grid-cols-[minmax(0,2fr)_minmax(0,1fr)] md:px-8">
              <div>
                <SectionHead title="Saison" note="Tordifferenz pro Spiel" />
                <DiffBars matches={DEMO_SEASON.diff} label="Tordifferenz pro Spiel" />
              </div>
              <div>
                <SectionHead title="Themen" />
                <ul className="m-0 list-none p-0">
                  {DEMO_SEASON.themes.map((t) => (
                    <li key={t.title} className="flex items-end justify-between gap-4 border-t border-rule py-3">
                      <span className="font-slant text-xl leading-tight">{t.title}</span>
                      <Series values={t.series} team={t.team} label={`${t.title}: ${t.series.join(", ")}`} />
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            <div className="mt-10 flex flex-wrap items-center gap-3 px-4 md:px-8">
              <Button>Szene ansehen</Button>
              <Button variant="secondary">Teilen</Button>
              <a className={linkClass} href="#top">
                Alle Gegentore
              </a>
              <span className="relative ml-6 px-3 py-2 font-slant text-lg">
                Spiele
                <ActiveMark className="right-2.5 -bottom-0.5 left-2.5" />
              </span>
              <span className="text-[15px] font-bold text-win">Sieg</span>
              <span className="text-[15px] font-bold text-loss">Niederlage</span>
            </div>
          </section>
        );
      })}
    </main>
  );
}
