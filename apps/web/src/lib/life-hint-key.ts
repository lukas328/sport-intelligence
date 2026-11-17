import type { Mode, Section } from "./nav-model";

/**
 * The text of the first-visit note of an area of Teamleben (K16), by who reads it. The parents'
 * overview names the dates only while Teamfunktionen are on: without them it shows the scenes.
 */
export function lifeHintKey(area: Section, mode: Mode, datesOn: boolean): string {
  const who = mode === "staff" ? "staff" : mode === "family" ? "family" : "player";
  if (area === "overview" && who === "family" && !datesOn) return "hint_overview_family_off";
  return `hint_${area}_${who}`;
}
