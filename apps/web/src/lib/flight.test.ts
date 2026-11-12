import { describe, expect, it } from "vitest";
import { floorAt, flightLayout, type ReportGoal } from "@/components/anlauf/flight-layout";

const LABELS = { half: "Halbzeit {v}", end: "Schluss {v}", halfLevel: "Halbzeit, Gleichstand", endLevel: "Schluss, Gleichstand" };

/** goals from a sequence of +1 / -1 */
function seq(steps: number[]): ReportGoal[] {
  return steps.map((d, i) => ({ minute: ((i + 1) * 59) / (steps.length + 1), team: d > 0 ? "own" : "opp" }));
}

/** the line's segments as boxes, widened by the stroke */
function segments(pts: readonly (readonly [number, number])[]) {
  return pts.slice(1).map((p, i) => {
    const q = pts[i]!;
    return [Math.min(p[0], q[0]) - 1.5, Math.min(p[1], q[1]) - 1.5, Math.max(p[0], q[0]) + 1.5, Math.max(p[1], q[1]) + 1.5] as const;
  });
}

const overlaps = (a: readonly number[], b: readonly number[]) => a[0]! < b[2]! && b[0]! < a[2]! && a[1]! < b[3]! && b[1]! < a[3]!;

const CASES: Record<string, number[]> = {
  "around zero": [1, -1, 1, -1, -1, 1, 1, -1, 1, -1, 1, -1, -1, 1, 1, -1, 1, 1, -1, -1, 1, 1],
  "level at half time": [1, 1, -1, -1, 1, -1, 1, -1, 1, 1, -1, 1, 1, -1, 1, 1],
  "always ahead": [1, 1, 1, -1, 1, 1, -1, 1, 1, 1, -1, 1, 1, 1],
  "always behind": [-1, -1, 1, -1, -1, -1, 1, -1, -1, -1, 1, -1],
  "late comeback": [-1, -1, -1, -1, -1, 1, 1, 1, 1, 1, 1, 1, 1],
};

describe("flight labels", () => {
  for (const [name, steps] of Object.entries(CASES)) {
    it(`${name}: no label touches the line, the edge or another label`, () => {
      const W = 1000;
      const H = 120;
      const slant = 48;
      const L = flightLayout(seq(steps), W, H, 60, LABELS, slant);
      for (const l of L.labels) {
        // gap of 4 around the text
        const box = [l.box[0] - 4, l.box[1] - 4, l.box[2] + 4, l.box[3] + 4];
        for (const s of segments(L.pts)) expect(overlaps(box, s), `${l.text} on the line`).toBe(false);
        expect(l.box[1]).toBeGreaterThanOrEqual(0);
        // clear of the slanted lower edge
        expect(l.box[3]).toBeLessThanOrEqual(floorAt(l.box[2], W, H, slant));
      }
      expect(overlaps(L.labels[0]!.box, L.labels[1]!.box)).toBe(false);
      // the end label keeps clear of the end dot
      expect(L.labels[1]!.box[2]).toBeLessThan(L.end[0] - 6);
      // every point of the line above the slanted edge
      for (const p of L.pts) expect(p[1]).toBeLessThanOrEqual(floorAt(p[0], W, H, slant) + 0.01);
    });
  }

  it("says «Gleichstand» instead of 0", () => {
    const L = flightLayout(seq(CASES["level at half time"]!), 1000, 120, 60, LABELS, 48);
    expect(L.labels[0]!.text).toBe("Halbzeit, Gleichstand");
    expect(flightLayout(seq([1, 1, -1]), 1000, 120, 60, LABELS).labels[0]!.text).not.toContain("0");
  });
});
