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
import { ownKeepers, withRosterIds, type RosterLike } from "@/lib/keepers";
import { halfScore, keeperSaves, mainSource, scoreSequence, topScorers } from "@/lib/telegram";
import type { Stats } from "./analysis-views";

/**
 * Tab Spiel below the three things (SPEC 7.2, UX test B08): the actions, Punkt 1 opened on the
 * tactics camera, the telegram, and beside them goals by position and three figures with their
 * source. Everything else of the match sits behind «Mehr zum Spiel».
 */

/** The actions under the three things: the team collection, the highlights, a picture. */
export function GameActions({ collect, onHighlights, onPicture }: { collect: ReactNode; onHighlights?: () => void; onPicture?: () => void }) {
  const t = useTranslations("anlauf");
  // nothing to do: no empty row that leaves a gap
  if (!collect && !onHighlights && !onPicture) return null;
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
export function Telegram({ match, stats, names, roster = [] }: { match: TelegramMatch; stats: Stats | null; names: Record<string, string>; roster?: RosterLike[] }) {
  const t = useTranslations("anlauf");
  const [copied, setCopied] = useState(false);
  const text = telegramText(t, match, stats, names, roster);
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

export function telegramText(t: T, m: TelegramMatch, stats: Stats | null, names: Record<string, string>, roster: RosterLike[] = []): string | null {
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
    const scorers = topScorers(withRosterIds(Object.values(stats.players), roster), names, 3, (k) => ` ${t("tgSeven", { n: k })}`);
    if (scorers.length) parts.push(t("tgScorers", { list: scorers.join(", ") }));
    // every own keeper with saves: the figure beside counts them all (R2)
    const keepers = keeperSaves(withRosterIds(ownKeepers(Object.values(stats.goalkeepers ?? {}), roster), roster), names);
    if (keepers.length === 1) parts.push(t("tgKeeper", { name: keepers[0]!.name, saves: keepers[0]!.saves }));
    else if (keepers.length > 1) parts.push(t("tgKeepers", { list: keepers.map((k) => t("tgKeeperItem", { name: k.name, saves: k.saves })).join(", ") }));
  }
  return parts.join(" ");
}

/** Three figures with their source; a figure the sources never recorded is left out. */
export function ThreeFigures({ stats, names, roster = [] }: { stats: Stats; names: Record<string, string>; roster?: RosterLike[] }) {
  const t = useTranslations("anlauf");
  const src = mainSource(stats.quality.sources);
  const from = t(src === "report" ? "fromReport" : src === "marked" ? "markedByYou" : "fromVideo");
  // the saves of the team; named after the keeper only when that keeper made all of them, so the
  // figure and the telegram never give two numbers for one thing (R2: «16 Paraden» and «20 Paraden»)
  const keepers = keeperSaves(withRosterIds(ownKeepers(Object.values(stats.goalkeepers ?? {}), roster), roster), names);
  const keeper = keepers.length === 1 && keepers[0]!.saves === stats.own.saves ? keepers[0]! : null;
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
