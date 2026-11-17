/**
 * Drill library (BRIEF 4.10 "Trainingsübungen", M7, K21). Own handball exercises (no third-party
 * content, see docs/research/R1-uebungsbibliothek.md), each with a focus, set-up, procedure, coaching
 * points, variants and a court sketch drawn with the tactics board. They are linked to the insight
 * rules: an insight about weak wing shots suggests the wing drills. Texts in de-CH, en, fr.
 */
import { DRILL_LIBRARY } from "./drill-library";
import type { Drill, Focus, Lang, Level } from "./drill-types";

export * from "./drill-types";

export const DRILLS: Drill[] = DRILL_LIBRARY;

/** Focus areas suggested by an insight (key from handball_metrics.insights, zone from its params). */
export function focusForInsight(key: string, zone?: string | null): Focus[] {
  const rule = key.replace("insights.", "");
  if (rule.startsWith("zone_")) {
    if (zone?.startsWith("wing")) return ["wings"];
    if (zone?.startsWith("back") || zone?.startsWith("half")) return ["back_court"];
    if (zone?.startsWith("circle")) return ["pivot"];
    return ["finishing"];
  }
  const map: Record<string, Focus[]> = {
    shooting_below: ["finishing"],
    drought: ["finishing"],
    seven_m_low: ["seven_m"],
    saves_below: ["goalkeeping"],
    keeper_bad: ["goalkeeping"],
    conceded_zone: ["goalkeeping"],
    turnovers_high: ["passing"],
    fast_breaks_against: ["transition_defence"],
    powerplay_weak: ["powerplay"],
    player_inefficient: ["finishing"],
  };
  return map[rule] ?? [];
}

/** Drills for the focus areas, those whose first focus matches first (the most specific). */
export function drillsFor(focus: Focus[]): Drill[] {
  const hits = DRILLS.filter((d) => d.focus.some((f) => focus.includes(f)));
  return [...hits.filter((d) => focus.includes(d.focus[0]!)), ...hits.filter((d) => !focus.includes(d.focus[0]!))];
}

export interface DrillFilter {
  focus?: Focus | null;
  level?: Level | null;
  /** at most this many minutes */
  minutes?: number | null;
  query?: string;
  lang?: Lang;
}

/** The library filtered by focus, level, duration and a search word (name in the coach's language). */
export function filterDrills(f: DrillFilter, list: Drill[] = DRILLS): Drill[] {
  const q = (f.query ?? "").trim().toLowerCase();
  const lang = f.lang ?? "de-CH";
  return list.filter(
    (d) =>
      (!f.focus || d.focus.includes(f.focus)) &&
      (!f.level || d.level === f.level) &&
      (!f.minutes || d.minutes <= f.minutes) &&
      (!q || d.name[lang].toLowerCase().includes(q) || d.name["de-CH"].toLowerCase().includes(q)),
  );
}
