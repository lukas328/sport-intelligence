import { describe, expect, it } from "vitest";
import { DRILLS, FOCI, drillsFor, filterDrills, focusForInsight } from "./drills";
import { GOAL_AREA_M, MIN_GAP, distToGoal, minTokenGap } from "./geometry";

const TEXTS = ["name", "setup", "procedure", "coaching", "variants"] as const;

describe("drills", () => {
  it("are a useful library: about forty, every focus with a choice", () => {
    expect(DRILLS.length).toBeGreaterThanOrEqual(40);
    for (const f of FOCI) expect(DRILLS.filter((d) => d.focus.includes(f)).length, f).toBeGreaterThanOrEqual(3);
    expect(DRILLS.filter((d) => d.level === "basic").length).toBeGreaterThanOrEqual(15);
    expect(DRILLS.filter((d) => d.level === "advanced").length).toBeGreaterThanOrEqual(10);
  });

  it("are complete in every language and unique", () => {
    expect(new Set(DRILLS.map((d) => d.id)).size).toBe(DRILLS.length);
    for (const d of DRILLS) {
      expect(d.minutes, d.id).toBeGreaterThanOrEqual(5);
      expect(d.minutes, d.id).toBeLessThanOrEqual(30);
      expect(d.players, d.id).toMatch(/^\d{1,2}(-\d{1,2})?$/);
      expect(d.focus.length, d.id).toBeGreaterThan(0);
      for (const lang of ["de-CH", "en", "fr"] as const)
        for (const k of TEXTS) {
          expect(d[k][lang], `${d.id} ${k} ${lang}`).toBeTruthy();
          expect(d[k][lang], `${d.id} ${k} ${lang}`).not.toMatch(/[—–]/); // no long dashes
          expect(d[k][lang].length, `${d.id} ${k} ${lang}`).toBeLessThan(600);
        }
      for (const k of TEXTS) expect(d[k]["de-CH"], `${d.id} ${k}`).not.toContain("ß");
      // the snapshot in a session takes set-up and procedure together (2000 characters at most)
      expect(d.setup.fr.length + d.procedure.fr.length).toBeLessThan(1900);
    }
  });

  it("sketches are handball-correct and readable", () => {
    for (const d of DRILLS) {
      const s = d.sketch;
      expect(s.tokens.length, d.id).toBeGreaterThan(0);
      expect(s.tokens.length, d.id).toBeLessThanOrEqual(16);
      expect(new Set(s.tokens.map((t) => t.id)).size, `${d.id} ids`).toBe(s.tokens.length);
      expect(minTokenGap(s.tokens), `${d.id} overlap`).toBeGreaterThanOrEqual(MIN_GAP);
      for (const t of s.tokens) {
        expect(t.x, `${d.id} ${t.id}`).toBeGreaterThanOrEqual(s.court === "half" ? 20.8 : 0.5);
        expect(t.x, `${d.id} ${t.id}`).toBeLessThanOrEqual(39.5);
        expect(t.y, `${d.id} ${t.id}`).toBeGreaterThanOrEqual(0.7);
        expect(t.y, `${d.id} ${t.id}`).toBeLessThanOrEqual(19.3);
        expect(t.label.length, `${d.id} ${t.id}`).toBeLessThanOrEqual(3);
        if (t.label !== "TW") {
          expect(distToGoal(t.x, t.y), `${d.id} ${t.id} in the goal area`).toBeGreaterThan(GOAL_AREA_M + 0.2);
          expect(distToGoal(t.x, t.y, "left"), `${d.id} ${t.id} in the goal area`).toBeGreaterThan(GOAL_AREA_M + 0.2);
        }
      }
      for (const a of s.arrows) {
        expect(a.points.length, d.id).toBeGreaterThanOrEqual(2);
        expect(a.points.length, d.id).toBeLessThanOrEqual(12);
      }
    }
  });

  it("maps insights to drills", () => {
    expect(focusForInsight("insights.zone_weak", "wing_left")).toEqual(["wings"]);
    expect(focusForInsight("insights.zone_weak", "back_centre")).toEqual(["back_court"]);
    expect(focusForInsight("insights.zone_strong", "circle_left")).toEqual(["pivot"]);
    expect(focusForInsight("insights.zone_weak", null)).toEqual(["finishing"]);
    expect(focusForInsight("insights.own_run")).toEqual([]);
    expect(drillsFor(focusForInsight("insights.seven_m_low")).map((d) => d.id)).toEqual(["seven_m_routine", "seven_m_duel", "keeper_seven_m"]);
    // the drills made for the focus come before those that only touch it
    const keeper = drillsFor(["goalkeeping"]);
    expect(keeper.length).toBeGreaterThanOrEqual(4);
    expect(keeper[0]!.focus[0]).toBe("goalkeeping");
    expect(keeper.at(-1)!.focus[0]).not.toBe("goalkeeping");
  });

  it("filters by focus, level, minutes and name", () => {
    const wings = filterDrills({ focus: "wings" });
    expect(wings.every((d) => d.focus.includes("wings"))).toBe(true);
    expect(filterDrills({ level: "advanced" }).every((d) => d.level === "advanced")).toBe(true);
    expect(filterDrills({ minutes: 10 }).every((d) => d.minutes <= 10)).toBe(true);
    expect(filterDrills({ query: "zehner" }).map((d) => d.id)).toEqual(["passing_ten_passes"]);
    expect(filterDrills({ query: "dix", lang: "fr" }).map((d) => d.id)).toEqual(["passing_ten_passes"]);
    expect(filterDrills({})).toHaveLength(DRILLS.length);
  });
});
