import { describe, expect, it } from "vitest";
import { DRILLS, drillsFor, focusForInsight } from "./drills";

describe("drills", () => {
  it("are complete in every language and unique", () => {
    expect(new Set(DRILLS.map((d) => d.id)).size).toBe(DRILLS.length);
    for (const d of DRILLS)
      for (const lang of ["de-CH", "en", "fr"] as const) {
        expect(d.name[lang], `${d.id} ${lang}`).toBeTruthy();
        expect(d.setup[lang]).toBeTruthy();
        expect(d.coaching[lang]).toBeTruthy();
        expect(d.name[lang] + d.setup[lang] + d.coaching[lang]).not.toMatch(/[—–]/); // no long dashes
      }
    for (const d of DRILLS) expect(d.setup["de-CH"] + d.coaching["de-CH"]).not.toContain("ß");
  });

  it("maps insights to drills", () => {
    expect(focusForInsight("insights.zone_weak", "wing_left")).toEqual(["wings"]);
    expect(focusForInsight("insights.zone_weak", "back_centre")).toEqual(["back_court"]);
    expect(focusForInsight("insights.zone_strong", "circle_left")).toEqual(["pivot"]);
    expect(focusForInsight("insights.zone_weak", null)).toEqual(["finishing"]);
    expect(focusForInsight("insights.own_run")).toEqual([]);
    expect(drillsFor(focusForInsight("insights.seven_m_low")).map((d) => d.id)).toEqual(["seven_m_routine"]);
    expect(drillsFor(["goalkeeping"]).length).toBe(2);
  });
});
