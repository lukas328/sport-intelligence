import { DRILLS } from "@handball/tactics";
import { describe, expect, it } from "vitest";
import { move, toDrillItem, totalMinutes } from "./drill-snapshot";

describe("drill snapshot", () => {
  it("copies the drill in the user's language", () => {
    const d = DRILLS[0]!;
    const fr = toDrillItem(d, "fr");
    expect(fr.drill_id).toBe(d.id);
    expect(fr.name).toBe(d.name.fr ?? d.name["de-CH"]);
    expect(toDrillItem(d, "xx").name).toBe(d.name["de-CH"]);
    expect(fr.focus).toEqual(d.focus);
  });

  it("sums minutes and reorders", () => {
    expect(totalMinutes([{ minutes: 15 }, { minutes: 20 }])).toBe(35);
    expect(move(["a", "b", "c"], 0, 1)).toEqual(["b", "a", "c"]);
    expect(move(["a", "b", "c"], 2, 1)).toEqual(["a", "b", "c"]);
    expect(move(["a", "b", "c"], 0, -1)).toEqual(["a", "b", "c"]);
  });
});
