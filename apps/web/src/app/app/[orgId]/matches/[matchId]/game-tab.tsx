"use client";

import { useTranslations } from "next-intl";
import { type ReactNode, useState } from "react";
import { SectionHead } from "@/components/anlauf/blocks";
import { SceneSpot } from "@/components/anlauf/spot-parts";
import { SceneCamera, clockOf, useThingText } from "@/components/anlauf/three-things-view";
import { buttonClass } from "@/components/ui/button";
import { goalRuns, type MatchGraphics } from "@/lib/graphics";
import { threeThings, type Thing } from "@/lib/three-things";
import { usePhone } from "@/lib/use-phone";
import { halfScore, mainKeeper, mainSource, scoreSequence, topScorers } from "@/lib/telegram";
import type { Stats } from "./analysis-views";

/**
 * Tab Spiel below the three things (SPEC 7.2, UX test B08): the actions, Punkt 1 opened on the
 * tactics camera, the telegram, and beside them goals by position and three figures with their
 * source. Everything else of the match sits behind «Mehr zum Spiel».
 */

/** The actions under the three things: the team collection, the highlights, a picture. */
export function GameActions({ collect, onHighlights, onPicture }: { collect: ReactNode; onHighlights?: () => void; onPicture?: () => void }) {
  const t = useTranslations("anlauf");
  return (
    <div className="flex flex-wrap items-center gap-x-5 gap-y-3" data-testid="game-actions">
      {collect}
      {onHighlights && (
        <button type="button" onClick={onHighlights} className="min-h-11 cursor-pointer border-0 bg-transparent p-0 text-[15px] font-bold text-ink underline decoration-2 underline-offset-4">
          {t("shareHighlights")}
        </button>
      )}
      {onPicture && (
        <button type="button" onClick={onPicture} className="min-h-11 cursor-pointer border-0 bg-transparent p-0 text-[15px] font-bold text-ink underline decoration-2 underline-offset-4" data-testid="chat-picture">
          {t("chatPicture")}
        </button>
      )}
    </div>
  );
}

/** Punkt 1, opened: its scenes one by one on the tactics camera. */
export function PointOpen({ orgId, matchId, graphics, oppName }: { orgId: string; matchId: string; graphics: MatchGraphics; oppName: string }) {
  const t = useTranslations("anlauf");
  const text = useThingText();
  const thing: Thing | undefined = threeThings(goalRuns(graphics))[0];
  const scenes = (thing?.goals ?? []).filter((g) => g.eventId);
  const [at, setAt] = useState(0);
  const phone = usePhone();
  if (!thing || scenes.length === 0) return null;
  const goal = scenes[Math.min(at, scenes.length - 1)]!;
  const label = t("goalOf", { team: thing.team === "opp" ? oppName : t("us"), clock: clockOf(goal.minute) });
  const of = t("pointOpenNote", { n: at + 1, total: scenes.length });
  return (
    <section data-testid="point-open">
      <SectionHead title={t("pointOpen")} note={of} />
      <SceneCamera key={goal.eventId} orgId={orgId} matchId={matchId} eventId={goal.eventId!} label={label} view={phone ? "halfB" : "camL"} width={phone ? 390 : 900} caption={`${label} · ${text(thing)}`} />
      <SceneSpot orgId={orgId} matchId={matchId} graphics={graphics} eventId={goal.eventId!} label={label} />
      <div className="mt-2 flex flex-wrap gap-2.5">
        <button type="button" className={buttonClass("secondary", "sm")} disabled={at === 0} onClick={() => setAt((x) => Math.max(0, x - 1))}>
          {t("prevScene")}
        </button>
        <button type="button" className={buttonClass("secondary", "sm")} disabled={at >= scenes.length - 1} onClick={() => setAt((x) => Math.min(scenes.length - 1, x + 1))} data-testid="point-next">
          {t("nextScene")}
        </button>
      </div>
    </section>
  );
}

export interface TelegramMatch {
  own: string;
  opp: string;
  score: [number, number] | null;
  /** the half-time score of the report, when it has one */
  half?: [number, number] | null;
  venue: string | null;
  periodS: number;
  periods: number;
}

/** The telegram: one paragraph of facts as a report would print it, with «Kopieren». */
export function Telegram({ match, stats, names }: { match: TelegramMatch; stats: Stats | null; names: Record<string, string> }) {
  const t = useTranslations("anlauf");
  const [copied, setCopied] = useState(false);
  const text = telegramText(t, match, stats, names);
  if (!text) return null;
  return (
    <section data-testid="telegram">
      <SectionHead
        title={t("telegram")}
        action={
          <button
            type="button"
            className="min-h-11 cursor-pointer border-0 bg-transparent p-0 text-[15px] font-bold text-ink underline decoration-[1.5px] underline-offset-4"
            onClick={async () => {
              await navigator.clipboard?.writeText(text).catch(() => undefined);
              setCopied(true);
            }}
          >
            {copied ? t("copied") : t("copy")}
          </button>
        }
      />
      <p className="m-0 max-w-[66ch] text-[17px] leading-[1.55]">{text}</p>
    </section>
  );
}

type T = ReturnType<typeof useTranslations<"anlauf">>;

export function telegramText(t: T, m: TelegramMatch, stats: Stats | null, names: Record<string, string>): string | null {
  if (!m.score) return null;
  const timed = stats?.timeline.timed !== false;
  const points = stats?.timeline.score ?? [];
  const half = m.half ?? halfScore(points, m.periodS, timed);
  const parts = [
    t("tgHead", { own: m.own, opp: m.opp, score: `${m.score[0]}:${m.score[1]}` }) + (half ? ` (${half[0]}:${half[1]})` : "") + ".",
  ];
  if (m.venue) parts.push(`${m.venue}.`);
  const seq = scoreSequence(points, m.periodS, m.periods, timed);
  if (seq.length > 1) parts.push(t("tgSequence", { list: seq.map(([a, b]) => `${a}:${b}`).join(", ") }));
  if (stats) {
    const pens = [
      stats.own.suspensions ? t("tgPenalty", { n: stats.own.suspensions, team: m.own }) : null,
      stats.opponent.suspensions ? t("tgPenalty", { n: stats.opponent.suspensions, team: m.opp }) : null,
    ].filter(Boolean);
    if (pens.length) parts.push(t("tgPenalties", { list: pens.join(", ") }));
    const scorers = topScorers(Object.values(stats.players), names, 3, (k) => ` ${t("tgSeven", { n: k })}`);
    if (scorers.length) parts.push(t("tgScorers", { list: scorers.join(", ") }));
    const keeper = mainKeeper(Object.values(stats.goalkeepers ?? {}), names);
    if (keeper) parts.push(t("tgKeeper", { name: keeper.name, saves: keeper.saves }));
  }
  return parts.join(" ");
}

/** Three figures with their source; a figure the sources never recorded is left out. */
export function ThreeFigures({ stats, names }: { stats: Stats; names: Record<string, string> }) {
  const t = useTranslations("anlauf");
  const src = mainSource(stats.quality.sources);
  const from = t(src === "report" ? "fromReport" : src === "marked" ? "markedByYou" : "fromVideo");
  const keeper = mainKeeper(Object.values(stats.goalkeepers ?? {}), names);
  const figs: { value: string; label: string; testid: string }[] = [];
  if (stats.own.known?.saving !== false && stats.own.saves > 0) {
    figs.push({ value: String(stats.own.saves), label: `${keeper ? t("figSavesOf", { name: keeper.name }) : t("figSaves")}, ${from}`, testid: "fig-saves" });
  }
  if (stats.own.known?.turnovers !== false && stats.quality.events > 0) {
    figs.push({ value: String(stats.own.turnovers), label: `${t("figTurnovers")}, ${from}`, testid: "fig-turnovers" });
  }
  if (stats.own.shooting_pct != null && stats.own.shots > 0) {
    figs.push({
      value: `${Math.round(stats.own.shooting_pct * 100)}`,
      label: `${t("figShooting", { goals: stats.own.goals, shots: stats.own.shots })}, ${from}`,
      testid: "fig-shooting",
    });
  }
  if (figs.length === 0) return null;
  return (
    <dl className="m-0 grid grid-cols-3 border-t-2 border-ink" data-testid="three-figures">
      {figs.map((f, i) => (
        <div key={f.testid} className={i > 0 ? "border-l border-rule pl-3 pt-3" : "pt-3 pr-3"} data-testid={f.testid}>
          <dt className="sr-only">{f.label}</dt>
          <dd className="m-0 font-num text-[40px] leading-none">
            {f.value}
            {f.testid === "fig-shooting" && <span className="text-[20px]">%</span>}
          </dd>
          <p className="m-0 mt-1.5 text-[15px] text-ink-2" aria-hidden>
            {f.label}
          </p>
        </div>
      ))}
    </dl>
  );
}

/** «Als Bild für den Chat»: the score and the three things as a square picture to save. */
export function chatPicture(opts: { title: string; sub: string; score: string; things: { value: number; text: string }[]; heading: string; file: string }) {
  const c = document.createElement("canvas");
  c.width = 1080;
  c.height = 1080;
  const g = c.getContext("2d");
  if (!g) return;
  const css = getComputedStyle(document.documentElement);
  const v = (name: string, fallback: string) => css.getPropertyValue(name).trim() || fallback;
  const club = v("--club", "black");
  const onClub = v("--club-ink", "white");
  const ground = v("--ground", "white");
  const ink = v("--ink", "black");
  g.fillStyle = ground;
  g.fillRect(0, 0, 1080, 1080);
  g.fillStyle = club;
  g.beginPath();
  g.moveTo(0, 0);
  g.lineTo(1080, 0);
  g.lineTo(1080, 420);
  g.lineTo(0, 480);
  g.closePath();
  g.fill();
  g.fillStyle = onClub;
  g.font = "bold 40px sans-serif";
  g.fillText(opts.sub, 64, 100);
  g.font = "italic 900 64px sans-serif";
  g.fillText(opts.title, 64, 180, 952);
  g.font = "italic 900 200px sans-serif";
  g.fillText(opts.score, 64, 390, 952);
  g.fillStyle = ink;
  g.font = "italic 900 48px sans-serif";
  g.fillText(opts.heading, 64, 580);
  opts.things.forEach((x, i) => {
    const y = 680 + i * 120;
    g.font = "italic 900 88px sans-serif";
    g.fillText(String(x.value), 64, y + 20);
    g.font = "bold 40px sans-serif";
    g.fillText(x.text, 220, y, 796);
  });
  c.toBlob((blob) => {
    if (!blob) return;
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = opts.file;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 2000);
  }, "image/png");
}
