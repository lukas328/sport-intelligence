"use client";

import type { Schemas } from "@handball/api-client";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { SectionHead } from "@/components/anlauf/blocks";
import type { MatchGraphics } from "@/lib/graphics";
import { cn } from "@/lib/utils";
import type { Stats } from "./analysis-views";
import { MatchZones } from "./match-graphics";

type Entry = Schemas["RosterEntryOut"];

const FIELD_ROWS = 7;
const pct = (v: number | null) => (v == null || v > 1 ? "" : `${Math.round(v * 100)} %`);

/**
 * Zahlen (SPEC 7.4): the field players and the goalkeepers of the own team as two tables, at the
 * side the goals conceded by position, the goal target and the phases. The full report, shots,
 * goalkeepers in detail and the running figures stay one click away («Alle Zahlen»).
 */
const TARGET_ROWS = [
  ["TL", "TC", "TR"],
  ["ML", "MC", "MR"],
  ["BL", "BC", "BR"],
] as const;

export function NumbersView({ stats, graphics, roster, children }: { stats: Stats | null; graphics: MatchGraphics | null; roster: Entry[]; children: React.ReactNode }) {
  const t = useTranslations("numbersTab");
  const [all, setAll] = useState(false);
  const who = (id: string | null, number: number | null) => {
    const r = roster.find((x) => x.player_id === id) ?? (number != null ? roster.find((x) => x.jersey_number === number) : undefined);
    return { number: r?.jersey_number ?? number, name: r ? `${r.first_name} ${r.last_name}` : t("unknown") };
  };
  const keeperIds = new Set(Object.values(stats?.goalkeepers ?? {}).filter((k) => k.side === "own").map((k) => k.player_id));
  const field = Object.values(stats?.players ?? {})
    .filter((p) => p.side === "own" && !keeperIds.has(p.player_id) && (p.shots > 0 || p.goals > 0 || p.suspensions > 0))
    .sort((a, b) => b.goals - a.goals || b.shots - a.shots);
  const scorers = field.filter((p) => p.goals > 0);
  const shown = all ? field : scorers.slice(0, FIELD_ROWS);
  const keepers = Object.values(stats?.goalkeepers ?? {}).filter((k) => k.side === "own" && k.faced > 0);
  const zones = stats?.opponent.goal_zones ?? {};
  const marked = Object.values(zones).reduce((n, z) => n + z.goals, 0);
  const phases = graphics?.phases ?? [];
  // shots and rates only where misses were recorded: from goals alone every rate reads 100 %
  const shotsKnown = stats?.own.known?.shooting !== false;
  const th = "py-2 text-right text-[15px] font-semibold text-ink-2";
  const td = "py-2.5 text-right tabular-nums";
  return (
    <div className="space-y-12">
      <p className="max-w-[90ch] text-[15px] text-ink-2 md:text-[15px]">{t("intro")}</p>
      <div className="grid gap-x-12 gap-y-12 lg:grid-cols-[minmax(0,1fr)_340px]">
        <div className="min-w-0 space-y-12">
          {field.length > 0 && (
            <section data-testid="numbers-field">
              <SectionHead title={t("field")} note={t("byGoals")} />
              <table className="w-full border-collapse text-[15px]">
                <thead>
                  <tr className="border-b-2 border-ink">
                    <th scope="col" className={cn(th, "text-left")}>{t("numberName")}</th>
                    <th scope="col" className={th}>{t("goals")}</th>
                    <th scope="col" className={th}>{t("sevenM")}</th>
                    <th scope="col" className={th}>{t("twoMin")}</th>
                    {shotsKnown && <th scope="col" className={cn(th, "max-sm:hidden")}>{t("shots")}</th>}
                    {shotsKnown && <th scope="col" className={th}>{t("rate")}</th>}
                  </tr>
                </thead>
                <tbody>
                  {shown.map((p, i) => {
                    const w = who(p.player_id, p.number);
                    return (
                      <tr key={p.player_id ?? `n${p.number ?? i}`} className="border-b border-rule">
                        <th scope="row" className="py-2.5 text-left font-normal">
                          <b className="font-num mr-3 inline-block w-8 text-lg text-club-text">{w.number ?? ""}</b>
                          {w.name}
                        </th>
                        <td className={td}>{p.goals || ""}</td>
                        <td className={td}>{p.seven_m_shots > 0 ? `${p.seven_m_goals}/${p.seven_m_shots}` : ""}</td>
                        <td className={td}>{p.suspensions || ""}</td>
                        {shotsKnown && <td className={cn(td, "max-sm:hidden")}>{p.shots || ""}</td>}
                        {shotsKnown && <td className={cn(td, "text-ink-2")}>{p.shots > 0 ? pct(p.goals / p.shots) : ""}</td>}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              {!all && field.length > shown.length && (
                <p className="mt-2 text-[15px] text-ink-2">
                  {t("more", { n: field.length - shown.length })}{" "}
                  <button type="button" onClick={() => setAll(true)} className="cursor-pointer font-bold text-ink underline decoration-[1.5px] underline-offset-4">
                    {t("showAll")}
                  </button>
                </p>
              )}
            </section>
          )}
          {keepers.length > 0 && (
            <section data-testid="numbers-keepers">
              <SectionHead title={t("keeper")} />
              <table className="w-full border-collapse text-[15px]">
                <thead>
                  <tr className="border-b-2 border-ink">
                    <th scope="col" className={cn(th, "text-left")}>{t("numberName")}</th>
                    <th scope="col" className={th}>{t("against")}</th>
                    <th scope="col" className={th}>{t("saves")}</th>
                    <th scope="col" className={th}>{t("sevenMSaved")}</th>
                  </tr>
                </thead>
                <tbody>
                  {keepers.map((k, i) => {
                    const w = who(k.player_id, k.number);
                    return (
                      <tr key={k.player_id ?? i} className="border-b border-rule">
                        <th scope="row" className="py-2.5 text-left font-normal">
                          <b className="font-num mr-3 inline-block w-8 text-lg text-club-text">{w.number ?? ""}</b>
                          {w.name}
                        </th>
                        <td className={td}>{k.goals_against}</td>
                        <td className={td}>{k.saves}</td>
                        <td className={td}>{k.seven_m.faced > 0 ? t("ofN", { n: k.seven_m.saves, of: k.seven_m.faced }) : ""}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </section>
          )}
        </div>
        <aside className="min-w-0 space-y-12">
          {graphics && graphics.goals.some((g) => g.team === "opp") && <MatchZones graphics={graphics} only="opp" />}
          {marked > 0 && (
            <section>
              <SectionHead as="h3" title={t("target")} note={t("targetNote")} />
              {/* goals per corner from the shooter's view, a plain frame (UX test B23: no foreign colours) */}
              <table className="w-[220px] border-collapse border-x-[6px] border-t-[6px] border-ink" data-testid="target-grid">
                <caption className="sr-only">{t("target")}</caption>
                <tbody>
                  {TARGET_ROWS.map((row) => (
                    <tr key={row.join()}>
                      {row.map((z) => (
                        <td key={z} className="h-[50px] border border-rule text-center font-num text-xl">
                          {zones[z]?.goals ?? 0}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="mt-2 text-[15px] text-ink-2">{t("targetMarked", { n: marked, of: stats?.own.goals_against ?? marked })}</p>
            </section>
          )}
          {phases.length > 0 && (
            <section data-testid="numbers-phases">
              <SectionHead as="h3" title={t("phases")} />
              <ul className="m-0 list-none p-0">
                {phases.map((ph) => {
                  const minutes = Math.round(ph.windows.reduce((n, [a, b]) => n + (b - a), 0));
                  const total = Math.max(1, ph.goals_us + ph.goals_them);
                  return (
                    <li key={ph.kind} className="border-t border-rule py-3 first:border-t-0">
                      <p className="m-0 flex items-baseline justify-between gap-3">
                        <span className="text-[15px]">
                          {t(`phase_${ph.kind}`, { m: minutes })}
                          <small className="block text-[14px] text-ink-2">{ph.estimated ? t("fromVideo") : t(ph.kind === "fast_break" ? "fromEvents" : "fromSuspensions")}</small>
                        </span>
                        <b className="font-num text-xl">
                          {ph.goals_us}:{ph.goals_them}
                        </b>
                      </p>
                      <span aria-hidden className="mt-1.5 flex h-1.5 gap-0.5">
                        <i className="block" style={{ width: `${(100 * ph.goals_us) / total}%`, background: "var(--club-line)" }} />
                        <i className="block flex-1 bg-ink" />
                      </span>
                    </li>
                  );
                })}
              </ul>
            </section>
          )}
        </aside>
      </div>
      <details className="border-t-2 border-ink pt-4" data-testid="numbers-more">
        <summary className="min-h-11 cursor-pointer content-center">
          <span className="font-slant text-[22px]">{t("allNumbers")}</span> <span className="text-[15px] text-ink-2">{t("allNumbersNote")}</span>
        </summary>
        <div className="mt-8 space-y-12">{children}</div>
      </details>
    </div>
  );
}
