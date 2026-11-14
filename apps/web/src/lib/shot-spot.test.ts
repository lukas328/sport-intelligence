import { describe, expect, it } from "vitest";
import { ZONE_AT } from "@/components/anlauf/geometry";
import { goalRuns, type MatchGraphics } from "./graphics";
import { checkMinutes, COURT_ZONES, goalsWithoutSpot, halfToCourt, nineAt, spotCounts, ZONE_AREA, ZONE_LABEL_AT, zoneAtHalf } from "./shot-spot";
import { threeThings } from "./three-things";

/** point in polygon (even-odd) */
function inside(p: readonly [number, number], poly: readonly (readonly [number, number])[]): boolean {
  let hit = false;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const [xi, yi] = poly[i]!;
    const [xj, yj] = poly[j]!;
    if (yi > p[1] !== yj > p[1] && p[0] < ((xj - xi) * (p[1] - yi)) / (yj - yi) + xi) hit = !hit;
  }
  return hit;
}

describe("Von wo? on the half court", () => {
  it("names each area by the place its label stands in", () => {
    for (const z of COURT_ZONES) {
      expect(zoneAtHalf(ZONE_LABEL_AT[z])).toBe(z);
      expect(inside(ZONE_LABEL_AT[z], ZONE_AREA[z])).toBe(true);
    }
  });

  it("puts the count anchors of the zone graphic into the same areas", () => {
    for (const z of COURT_ZONES) expect(zoneAtHalf(ZONE_AT[z]!)).toBe(z);
  });

  it("left is the attacker's left: the left of the picture is +y on the court (API: to_half, zones.json)", () => {
    // left wing, near the goal line, on the left of the picture
    expect(zoneAtHalf([1.5, 1.5])).toBe("la");
    expect(halfToCourt([1.5, 1.5])).toEqual([38.5, 18.5]);
    expect(zoneAtHalf([18.5, 1.5])).toBe("ra");
    expect(halfToCourt([18.5, 1.5])).toEqual([38.5, 1.5]);
  });

  it("splits circle and back court at the 9 m line", () => {
    expect(nineAt(10)).toBe(9);
    expect(zoneAtHalf([10, 8.9])).toBe("kr");
    expect(zoneAtHalf([10, 9.1])).toBe("rm");
    expect(zoneAtHalf([5, 8])).toBe("kr");
    expect(zoneAtHalf([5, 8.5])).toBe("rl");
    expect(zoneAtHalf([15.5, 12])).toBe("rr");
  });

  it("estimates minutes with the extra step (22 questions without it: 6 to 7 minutes)", () => {
    expect(checkMinutes(0, 22)).toBe(7);
    expect(checkMinutes(9, 13)).toBe(7);
    expect(checkMinutes(12, 10)).toBe(8);
    expect(checkMinutes(0, 0, 9)).toBe(1);
    expect(checkMinutes(0, 0, 0)).toBe(1);
  });
});

function goal(id: string, team: "own" | "opp", zone: string | null, extra: Partial<MatchGraphics["goals"][number]> = {}): MatchGraphics["goals"][number] {
  return { event_id: id, team, minute: 1, number: null, zone, run: [], shot: null, aim: null, confirmed: true, source: null, has_video: true, t_ms: 1000, zone_source: zone ? "coach" : null, spot_missing: zone == null, ...extra };
}

function graphics(goals: MatchGraphics["goals"]): MatchGraphics {
  return { has_video: true, analysis: "ready", field_confirmed: true, report_goals: [], goals, phases: [], checks: [], more_checks: [], source: "analysis", parts: [] } as unknown as MatchGraphics;
}

describe("places for the three things", () => {
  it("counts a goal with a place but no point, drawn at the zone's point", () => {
    const g = graphics([goal("a", "opp", "rl"), goal("b", "opp", "rl"), goal("c", "opp", "rl"), goal("d", "own", null)]);
    const runs = goalRuns(g);
    expect(runs).toHaveLength(3);
    // three goals at the zone's point are three dots, set apart, the same each time
    const spots = runs.map((r) => r.shot.join(","));
    expect(new Set(spots).size).toBe(3);
    expect(goalRuns(g).map((r) => r.shot)).toEqual(runs.map((r) => r.shot));
    for (const r of runs) expect(Math.hypot(r.shot[0] - ZONE_AT.rl![0], r.shot[1] - ZONE_AT.rl![1])).toBeCloseTo(1.1, 5);
    const things = threeThings(runs);
    expect(things.map((x) => [x.key, x.zone, x.value])).toEqual([["conceded_zone", "rl", 3]]);
  });

  it("three fast breaks are a thing of their own", () => {
    const g = graphics([goal("a", "opp", "gs"), goal("b", "opp", "gs"), goal("c", "opp", "gs")]);
    expect(threeThings(goalRuns(g)).map((x) => x.key)).toContain("conceded_fast_breaks");
  });

  it("says how many goals have a place and which to fill in, in the order of the video", () => {
    const g = graphics([goal("a", "own", "la"), goal("b", "opp", null, { t_ms: 9000 }), goal("c", "own", null, { t_ms: 2000 }), goal("d", "own", null, { spot_missing: false, zone_source: "unknown" })]);
    expect(goalsWithoutSpot(g).map((x) => x.event_id)).toEqual(["c", "b"]);
    expect(spotCounts(g)).toEqual({ placed: 1, missing: 2, total: 4 });
  });

  it("does not count an estimate after «Weiss nicht» as a place the coach gave (Echtlauf 6)", () => {
    const g = graphics([goal("a", "own", "la"), goal("b", "opp", "kr", { spot_missing: false, zone_source: "unknown" })]);
    expect(spotCounts(g)).toEqual({ placed: 1, missing: 0, total: 2 });
  });
});
