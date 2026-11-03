import type { Drill } from "@handball/tactics";

type Lang = "de-CH" | "fr" | "en";

/** A library drill as stored in a session: a snapshot, so later library changes keep the plan. */
export interface DrillItem {
  drill_id: string;
  name: string;
  minutes: number;
  focus?: string[];
  setup?: string | null;
  coaching?: string | null;
  note?: string | null;
}

export function toDrillItem(d: Drill, lang: string): DrillItem {
  const l = (["de-CH", "fr", "en"].includes(lang) ? lang : "de-CH") as Lang;
  return {
    drill_id: d.id,
    name: d.name[l] ?? d.name["de-CH"],
    minutes: d.minutes,
    focus: [...d.focus],
    setup: d.setup[l] ?? d.setup["de-CH"],
    coaching: d.coaching[l] ?? d.coaching["de-CH"],
  };
}

export function totalMinutes(items: { minutes: number }[]): number {
  return items.reduce((sum, d) => sum + d.minutes, 0);
}

/** Moves an item one step up (-1) or down (+1); out-of-range moves return the list unchanged. */
export function move<T>(list: T[], index: number, step: -1 | 1): T[] {
  const j = index + step;
  if (j < 0 || j >= list.length) return list;
  const out = [...list];
  [out[index], out[j]] = [out[j]!, out[index]!];
  return out;
}
