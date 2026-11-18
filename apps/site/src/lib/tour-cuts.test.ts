import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { sundayAnswer } from "./story";
import { COLLECTION, SEARCH, SEASON_BARS, tourTimeline } from "./tour-cuts";

const readme = readFileSync(join(__dirname, "..", "..", "scripts", "product-shots", "README.md"), "utf8");

describe("the live cut-outs of the app tour say what the captures show (U34)", () => {
  it("the search: 26 of 77 over three matches, 34 per cent, 11 of 29 in the demo match", () => {
    expect(Math.round((SEARCH.n / SEARCH.of) * 100)).toBe(SEARCH.percent);
    const last = sundayAnswer();
    expect([SEARCH.last.n, SEARCH.last.of]).toEqual([last.n, last.of]);
    expect(readme).toContain(`${SEARCH.n} of ${SEARCH.of}, ${SEARCH.percent} Prozent`);
  });

  it("the season: one bar per match, adding up to the search, the last one the demo match", () => {
    expect(SEASON_BARS.reduce((a, b) => a + b.n, 0)).toBe(SEARCH.n);
    expect(SEASON_BARS.at(-1)!.n).toBe(SEARCH.last.n);
    expect(readme).toContain(`bars ${SEASON_BARS.map((b) => b.n).join(", ")}`);
  });

  it("the match: 56 goals, 27 of ours, the scene 5:01 in its phase", () => {
    const t = tourTimeline();
    expect(t.goals).toHaveLength(56);
    expect(t.goals.filter((g) => g.own)).toHaveLength(27);
    expect(t.scene.clock).toBe("5:01");
    expect(t.scene.minute).toBeGreaterThanOrEqual(t.phase[0]);
    expect(t.scene.minute).toBeLessThanOrEqual(t.phase[1]);
    expect(COLLECTION.scenes).toBe(4);
  });
});
