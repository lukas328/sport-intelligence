"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";
import { AttnTag, CameraKey, SectionHead } from "@/components/anlauf/blocks";
import { Zones } from "@/components/anlauf/bundle";
import { Rail } from "@/components/anlauf/charts";
import { clockOf, SceneCamera } from "@/components/anlauf/three-things-view";
import { goalRuns, reportGoals, type MatchGraphics } from "@/lib/graphics";
import { cn } from "@/lib/utils";

/** Gegentore and eigene Tore by position: counts at the zones, the shot spots as dots. */
export function MatchZones({ graphics, row = false, only }: { graphics: MatchGraphics; row?: boolean; only?: "opp" | "own" }) {
  const t = useTranslations("anlauf");
  const names = Object.fromEntries(["la", "ra", "rl", "rm", "rr", "kr", "m7", "gs"].map((z) => [z, t(`zoneShort.${z}` as "zoneShort.la")]));
  const sides = [
    { team: "opp" as const, title: t("conceded") },
    { team: "own" as const, title: t("scored") },
  ].filter((x) => !only || x.team === only);
  return (
    <aside className={cn("grid gap-10", row ? "md:grid-cols-2" : "content-start")}>
      {sides.map((s) => {
        const goals = goalRuns(graphics, s.team);
        if (goals.length === 0) return null;
        return (
          <section key={s.team}>
            <SectionHead as="h3" title={s.title} note={`${t("byPosition")}, ${goals.length}`} />
            <Zones goals={goals} team={s.team} zoneNames={names} label={`${s.title} ${t("byPosition")}: ${Object.entries(count(goals)).map(([z, n]) => `${names[z] ?? z} ${n}`).join(", ")}`} />
          </section>
        );
      })}
    </aside>
  );
}

function count(goals: { zone?: string | null }[]): Record<string, number> {
  const c: Record<string, number> = {};
  for (const g of goals) if (g.zone) c[g.zone] = (c[g.zone] ?? 0) + 1;
  return c;
}

/**
 * The Bühne of the tab Video (SPEC 7.3): the tactics camera of one goal with the Ball-Linie and
 * the legend, the goals of the match to pick from, the Rail of the report underneath.
 */
export function MatchCamera({ orgId, matchId, graphics, oppName }: { orgId: string; matchId: string; graphics: MatchGraphics; oppName: string }) {
  const t = useTranslations("anlauf");
  const goals = graphics.goals.filter((g) => g.has_video || g.source === "demo");
  const [eventId, setEventId] = useState<string | null>(goals[0]?.event_id ?? null);
  const goal = goals.find((g) => g.event_id === eventId) ?? null;
  const label = goal ? t("goalOf", { team: goal.team === "opp" ? oppName : t("us"), clock: clockOf(goal.minute) }) : "";
  return (
    <section className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_340px]" aria-labelledby="camera-title">
      <div className="min-w-0">
        <SectionHead title={<span id="camera-title">{t("cameraTitle")}</span>} note={goal ? clockOf(goal.minute) : undefined} action={goal ? <AttnTag>{label}</AttnTag> : undefined} />
        {eventId && <SceneCamera key={eventId} orgId={orgId} matchId={matchId} eventId={eventId} label={label} view="camL" width={900} caption={label} />}
        <CameraKey us={t("us")} them={oppName} referee={t("referee")} ball={t("ball")} />
        <p className="mt-1 text-[13px] text-ink-2">{t("numberRead")}</p>
        {graphics.report_goals.length > 0 && (
          <div className="mt-6">
            <Rail goals={reportGoals(graphics)} at={goal?.minute ?? null} label={t("rail")} />
            <p className="mt-1 flex justify-between text-[13px] text-ink-2">
              <span>0:00</span>
              <span>60:00</span>
            </p>
          </div>
        )}
      </div>
      <div>
        <SectionHead as="h3" title={t("sceneList")} note={String(goals.length)} />
        <ul className="m-0 max-h-[560px] list-none overflow-y-auto p-0">
          {goals.map((g) => {
            const on = g.event_id === eventId;
            return (
              <li key={g.event_id}>
                <button
                  type="button"
                  aria-pressed={on}
                  onClick={() => setEventId(g.event_id)}
                  className={cn("grid min-h-11 w-full cursor-pointer grid-cols-[58px_minmax(0,1fr)] gap-2.5 border-t border-rule px-3 py-2.5 text-left", on ? "bg-attn text-attn-ink" : "bg-transparent text-ink hover:bg-ink/5")}
                >
                  <b className="font-num text-[17px]">{clockOf(g.minute)}</b>
                  <span className="text-[15px] leading-snug">
                    {t("goalOf", { team: g.team === "opp" ? oppName : t("us"), clock: "" }).trim()}
                    {g.zone && <small className={cn("block text-[13px]", on ? "text-attn-ink" : "text-ink-2")}>{t(`zoneShort.${g.zone}` as "zoneShort.la")}</small>}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      </div>
    </section>
  );
}
